# cli.py
import argparse
import asyncio
import json
import logging
import os
from typing import Optional

from config import Config
from utils.logging import setup_logging
import llm_usage
from paper.latest import (
    iter_latest_papers,
    CATEGORIES,
    backfill_language_and_translation,
    diagnose_language,
    list_non_english_papers,
    backfill_doi_and_url,
)
from paper.embeddings import backfill_missing_embeddings
from db import upsert_paper


async def fetch_latest_command(
    category: Optional[str], days: int, limit: int, sort_by: str = "date",
    refresh: bool = False, continue_without_llm: bool = False,
) -> int:
    """Fetch papers for one or all known categories, storing each paper the moment it's ready.

    Each paper is retrieved, enriched (open-access check, abstract, translation, LLM summary,
    embedding, image), validated, and upserted before the next one starts - so a crash, Ctrl+C or
    quota stop never loses papers that were already finished. Papers already stored are skipped
    (unless `refresh`), so re-running resumes instead of redoing work and burning LLM quota.
    When every Gemini model's daily budget is spent the run stops with a clear message (rather
    than storing papers with raw-abstract descriptions) unless `continue_without_llm`.
    """
    logger = logging.getLogger("paperbites.cli")
    categories = [category] if category else CATEGORIES
    saved = 0

    try:
        for cat in categories:
            stats = {}
            cat_saved = 0
            try:
                async for paper in iter_latest_papers(
                    cat, days_back=days, limit=limit, sort_by=sort_by,
                    skip_existing=not refresh, stop_when_llm_exhausted=not continue_without_llm,
                    stats=stats,
                ):
                    try:
                        upsert_paper(paper)
                    except Exception as e:
                        logger.error(f"Couldn't store '{paper.get('title', '')[:60]}': {e}")
                        continue
                    saved += 1
                    cat_saved += 1
                    logger.info(f"[{cat}] saved {cat_saved}: {paper['title'][:80]}")
            except llm_usage.LLMQuotaExhausted as e:
                logger.warning(
                    f"Stopping: {e}. Saved {saved} paper(s) so far; they're kept. "
                    f"Re-run after the reset (midnight Pacific) to continue - already-saved papers are skipped."
                )
                break
            logger.info(
                f"'{cat}': {stats.get('candidates', 0)} candidates, saved {cat_saved}, "
                f"skipped {stats.get('skipped_existing', 0)} already stored, dropped {stats.get('dropped', 0)}"
            )
    finally:
        usage = llm_usage.tracker.format_report()
        if usage:
            logger.info("Gemini usage:\n" + usage)

    return saved


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(description="Fetch research papers into the PaperBites feed")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    fetch_parser = subparsers.add_parser("fetch-latest", help="Fetch latest papers from free APIs into MongoDB")
    fetch_parser.add_argument("--category", help="Single category to fetch (default: all known categories)", default=None)
    fetch_parser.add_argument("--days", help="How many days back to look", type=int, default=7)
    fetch_parser.add_argument("--limit", help="Max papers per category per source", type=int, default=20)
    fetch_parser.add_argument(
        "--sort-by", help="'date' for the latest papers, 'citations' for the most-cited in the window",
        choices=["date", "citations"], default="date",
    )
    fetch_parser.add_argument(
        "--refresh", action="store_true",
        help="Re-process papers that are already stored (default: skip them, which saves LLM quota)",
    )
    fetch_parser.add_argument(
        "--continue-without-llm", action="store_true",
        help="When the daily Gemini quota is spent, keep going and store papers with their raw "
             "abstract as the description (default: stop, so they can be summarized after the reset)",
    )
    fetch_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    usage_parser = subparsers.add_parser(
        "llm-usage", help="Show today's Gemini usage per model against its RPM / TPM / RPD limits"
    )
    usage_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    backfill_parser = subparsers.add_parser(
        "backfill-embeddings",
        help="Compute embeddings for papers already in MongoDB that predate semantic search "
             "(or fell outside every fetch-latest run's days_back window since) - safe to re-run",
    )
    backfill_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    backfill_language_parser = subparsers.add_parser(
        "backfill-language",
        help="Re-check the language of papers already in MongoDB tagged 'en' but never "
             "translated, using the fixed title-first detection - safe to re-run",
    )
    backfill_language_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    diagnose_parser = subparsers.add_parser(
        "diagnose-language",
        help="Read-only: show exactly what langdetect saw/decided for papers still tagged 'en', "
             "to see why backfill-language didn't flag them as non-English",
    )
    diagnose_parser.add_argument("--limit", help="Max papers to inspect", type=int, default=50)
    diagnose_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    non_english_parser = subparsers.add_parser(
        "list-non-english",
        help="Read-only: show every paper currently tagged with a non-English language, with "
             "both its translated title and title_original - confirms non-English papers exist "
             "and were actually translated, without checking documents one by one",
    )
    non_english_parser.add_argument("--limit", help="Max papers to list", type=int, default=50)
    non_english_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    backfill_doi_parser = subparsers.add_parser(
        "backfill-doi-url",
        help="Clear malformed DOIs (e.g. a bare 'DOI: 10.61132/' with no suffix) and fill in a "
             "doi.org fallback URL for papers with a valid DOI but no url - without a url, "
             "'Read Original Paper' doesn't render at all - safe to re-run",
    )
    backfill_doi_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    args = parser.parse_args()

    logger = setup_logging()
    config = Config(args.config)
    os.makedirs(config.get("paths.temp_dir"), exist_ok=True)

    async def run():
        if args.command == "fetch-latest":
            total = await fetch_latest_command(
                args.category, args.days, args.limit, sort_by=args.sort_by,
                refresh=args.refresh, continue_without_llm=args.continue_without_llm,
            )
            logger.info(f"Saved {total} papers total")
        elif args.command == "llm-usage":
            from paper.summarize import _configured_model_names
            print(llm_usage.tracker.format_report(_configured_model_names()))
            print(f"Daily quotas reset in {llm_usage.seconds_until_pacific_reset(llm_usage._time_now()) / 3600:.1f}h (midnight Pacific)")
        elif args.command == "backfill-embeddings":
            result = await backfill_missing_embeddings()
            logger.info(f"Backfill complete: {result}")
        elif args.command == "backfill-language":
            result = await backfill_language_and_translation()
            logger.info(f"Backfill complete: {result}")
        elif args.command == "diagnose-language":
            results = diagnose_language(limit=args.limit)
            print(json.dumps(results, indent=2))
        elif args.command == "list-non-english":
            results = list_non_english_papers(limit=args.limit)
            print(json.dumps(results, indent=2))
            logger.info(f"Found {len(results)} non-English paper(s)")
        elif args.command == "backfill-doi-url":
            result = backfill_doi_and_url()
            logger.info(f"Backfill complete: {result}")
        else:
            parser.print_help()

    asyncio.run(run())

if __name__ == "__main__":
    main()
