"""Add-paper-by-photo: reading the image (Gemini, OCR fallback), parsing, and matching."""
import asyncio
import json

import mongomock
import pytest

import db
import paper.embeddings as E
import paper.photo_scan as P
import paper.summarize as S
import paper.citation as C


def run(coro):
    return asyncio.run(coro)


# ---- parsing -----------------------------------------------------------------------------------
def test_parse_full_json_reply():
    raw = json.dumps({"title": "Deep  Learning\nfor Cats", "authors": ["A. One", "B. Two"], "venue": "Nature",
                      "year": "2024", "doi": "doi:10.1038/s41586-024-12345-6.", "abstract": "We study cats.",
                      "text": None})
    d = P.parse_image_details(raw)
    assert d["title"] == "Deep Learning for Cats" and d["authors"] == ["A. One", "B. Two"]
    assert d["doi"] == "10.1038/s41586-024-12345-6" and d["abstract"] == "We study cats." and d["text"] == ""


def test_parse_tolerates_fences_prose_and_string_authors():
    raw = 'Sure!\n```json\n{"title": "T", "authors": "A. One, B. Two and C. Three"}\n```'
    d = P.parse_image_details(raw)
    assert d["title"] == "T" and d["authors"] == ["A. One", "B. Two", "C. Three"]


def test_parse_non_json_keeps_text_and_finds_doi_in_it():
    d = P.parse_image_details("Some Title. Journal 2020. https://doi.org/10.1000/xyz123")
    assert d["title"] == "" and d["doi"] == "10.1000/xyz123" and "Journal 2020" in d["text"]


def test_parse_empty():
    assert P.parse_image_details(None)["doi"] is None and P.parse_image_details("  ")["authors"] == []


def test_queries():
    d = P.parse_image_details(json.dumps({"title": "T", "authors": list("ABCDE"), "venue": "V", "year": "2020"}))
    assert P.citation_query(d) == "T A, B, C V 2020"
    only_text = P.parse_image_details("just words")
    assert P.citation_query(only_text) == "just words"
    assert P.embedding_query(d) == "T"


# ---- reading: Gemini first, OCR as fallback ---------------------------------------------------------
def test_read_image_uses_gemini_when_it_reads_something(monkeypatch):
    async def gemini(b, m):
        return json.dumps({"title": "Read By Gemini"})
    monkeypatch.setattr(S, "extract_image_details", gemini)
    monkeypatch.setattr(P, "ocr_image_text", lambda b: pytest.fail("OCR should not run"))
    d = run(P.read_image(b"x", "image/jpeg"))
    assert d["title"] == "Read By Gemini" and d["source"] == "gemini"


def test_read_image_falls_back_to_ocr_when_gemini_fails(monkeypatch):
    async def gemini(b, m):
        return None
    monkeypatch.setattr(S, "extract_image_details", gemini)
    monkeypatch.setattr(P, "ocr_image_text", lambda b: "Quantum  Widgets\nby Someone  10.5555/abc.1")
    d = run(P.read_image(b"x", "image/jpeg"))
    assert d["source"] == "ocr" and d["doi"] == "10.5555/abc.1" and "Quantum Widgets" in d["text"]


def test_read_image_reports_nothing_readable(monkeypatch):
    async def gemini(b, m):
        return None
    monkeypatch.setattr(S, "extract_image_details", gemini)
    monkeypatch.setattr(P, "ocr_image_text", lambda b: "")
    assert run(P.read_image(b"x", "image/jpeg"))["source"] is None
    out = run(P.scan_image(b"x", "image/jpeg"))
    assert out["extracted"] is None and out["candidates"] == []


def test_ocr_helper_never_raises_on_garbage():
    assert P.ocr_image_text(b"not an image") == ""


# ---- matching --------------------------------------------------------------------------------
def cand(doi, title, **kw):
    return {"doi": doi, "title": title, "authors": [], **kw}


def test_merge_dedupes_by_doi_and_title_and_keeps_priority():
    merged = P._merge([[cand("10.1/A", "One")], [cand("10.1/a", "One again", in_library=True), cand(None, "Two")],
                       [cand(None, " two "), cand("10.1/b", "Three")]], 10)
    assert [c["title"] for c in merged] == ["One", "Two", "Three"]
    assert P._merge([[cand("10.1/a", "x")] * 5], 2) == [cand("10.1/a", "x")]


@pytest.fixture
def library(monkeypatch):
    database = mongomock.MongoClient().paperbites
    monkeypatch.setattr(db, "get_db", lambda: database)
    database.papers.insert_many([
        {"title": "Match", "authors": [{"id": None, "name": "Jane Doe"}], "doi": "10.9/m", "embedding": [1, 0],
         "published_date": "2026-09-01", "journal": "J"},
        {"title": "Weak", "authors": [], "doi": "10.9/w", "embedding": [0, 1], "published_date": "2026-09-02"},
        {"title": "No vector", "authors": [], "doi": "10.9/n", "published_date": "2026-09-03"},
    ])
    return database


def test_library_matches_use_embedding_similarity_and_threshold(library, monkeypatch):
    async def fake_score(query, docs):
        assert {d["title"] for d in docs} == {"Match", "Weak"}  # papers without a vector aren't compared
        return sorted([(0.95 if d["title"] == "Match" else 0.30, d) for d in docs], key=lambda p: -p[0])
    monkeypatch.setattr(E, "score_documents", fake_score)
    found = run(P.library_matches(P.parse_image_details(json.dumps({"title": "Some title", "abstract": "words here"}))))
    assert [c["title"] for c in found] == ["Match"]
    assert found[0]["in_library"] is True and found[0]["authors"] == ["Jane Doe"] and "embedding" not in found[0]


def test_library_matches_fail_soft(library, monkeypatch):
    async def boom(query, docs):
        raise RuntimeError("embedding service down")
    monkeypatch.setattr(E, "score_documents", boom)
    assert run(P.library_matches(P.parse_image_details(json.dumps({"title": "Some title here"})))) == []


def test_find_candidates_combines_doi_library_and_search(library, monkeypatch):
    async def lookup(session, doi):
        return cand(doi, "By DOI")
    async def search(session, query, n):
        return [cand("10.2/x", "By search"), cand("10.9/m", "Match (crossref copy)")]
    async def fake_score(query, docs):
        return [(0.9, d) for d in docs if d["title"] == "Match"]
    monkeypatch.setattr(C, "_lookup_doi", lookup)
    monkeypatch.setattr(C, "_search_crossref_bibliographic", search)
    monkeypatch.setattr(E, "score_documents", fake_score)
    d = P.parse_image_details(json.dumps({"title": "A longer paper title", "doi": "10.1234/doi"}))
    out = run(P.find_candidates(d))
    assert [c["title"] for c in out] == ["By DOI", "Match", "By search"]  # library copy wins the duplicate
    assert out[1]["in_library"] is True


def test_find_candidates_survives_lookup_failures(library, monkeypatch):
    async def boom(*a):
        raise RuntimeError("network")
    async def no_score(query, docs):
        return []
    monkeypatch.setattr(C, "_lookup_doi", boom)
    monkeypatch.setattr(C, "_search_crossref_bibliographic", boom)
    monkeypatch.setattr(E, "score_documents", no_score)
    assert run(P.find_candidates(P.parse_image_details(json.dumps({"title": "T", "doi": "10.1/d"})))) == []


# ---- endpoints ---------------------------------------------------------------------------------
@pytest.fixture
def client(monkeypatch, library):
    from starlette.testclient import TestClient
    import api_server
    monkeypatch.setattr(api_server.auth, "get_user_id_for_token", lambda t: "user1" if t == "good" else None)
    added = []
    monkeypatch.setattr(api_server.bookmarks_store, "add_bookmark", lambda u, p: added.append((u, p)))
    c = TestClient(api_server.app)
    c.added = added
    return c


AUTH = {"Authorization": "Bearer good"}


def test_scan_endpoint_requires_auth_and_an_image(client):
    assert client.post("/api/papers/citation/scan", files={"image": ("a.jpg", b"x", "image/jpeg")}).status_code == 401
    assert client.post("/api/papers/citation/scan", headers=AUTH, data={}).status_code == 400
    assert client.post("/api/papers/citation/scan", headers=AUTH, files={"image": ("a.jpg", b"", "image/jpeg")}).status_code == 400


def test_scan_endpoint_returns_candidates_and_extracted(client, monkeypatch):
    async def fake_scan(b, m):
        assert b == b"img" and m == "image/png"
        return {"extracted": "A Title", "details": {}, "candidates": [cand("10.1234/x", "A Title")]}
    monkeypatch.setattr(P, "scan_image", fake_scan)
    r = client.post("/api/papers/citation/scan", headers=AUTH, files={"image": ("a.png", b"img", "image/png")})
    assert r.status_code == 200 and r.json() == {"extracted": "A Title", "candidates": [cand("10.1234/x", "A Title")]}


def test_confirming_an_already_stored_paper_bookmarks_it_instead_of_duplicating(client, library, monkeypatch):
    import paper.citation as citation
    monkeypatch.setattr(citation, "add_paper_from_citation", lambda c: pytest.fail("pipeline must not re-run"))
    r = client.post("/api/papers/citation/confirm", headers=AUTH, json={"doi": "10.9/M", "title": "Match"})
    assert r.status_code == 200 and r.json()["title"] == "Match" and "embedding" not in r.json()
    assert client.added == [("user1", r.json()["id"])] and library.papers.count_documents({}) == 3
