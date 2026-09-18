# paper/chat.py
"""Per-paper chat agent: answers questions about a specific paper using Gemini via LangChain.

Deliberately stateless server-side - no LangGraph, no server-held conversation memory. The
client resends the full message history with each request, and the paper's own metadata/abstract
is injected as a system message for context. This is the simplest thing that works for
"answer questions about the paper, using the paper as context"; LangGraph/agentic tool use (e.g.
retrieval over the full PDF text) is a reasonable next step if the abstract alone ever stops
being enough context, but isn't needed for this.
"""
import logging
from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import Config

config_instance = Config()
logger = logging.getLogger("paperbites.chat")

_MODEL_NAME = "gemini-2.5-flash"

_SYSTEM_PROMPT = (
    "You are a research assistant helping a reader understand a specific paper. Answer "
    "questions using the paper's details below, plus your general knowledge of the field for "
    "context in under 200 words. If the abstract doesn't contain enough detail to answer precisely (e.g. exact "
    "numbers, specific methods), say so rather than guessing. Keep answers conversational and "
    "concise.\n\n"
    "Title: {title}\n"
    "Authors: {authors}\n"
    "Journal: {journal}\n"
    "Published: {published_date}\n\n"
    "Abstract:\n{abstract}"
)


def _get_llm():
    """Lazily build the Gemini chat model. Returns None if no API key is configured."""
    api_key = config_instance.get("api.gemini_key")
    if not api_key:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=_MODEL_NAME, google_api_key=api_key, temperature=0.4)


def _build_system_message(paper: Dict) -> SystemMessage:
    authors = ", ".join(a.get("name", "") for a in paper.get("authors", [])) or "Unknown"
    abstract = paper.get("abstract") or paper.get("description") or "No abstract available."
    return SystemMessage(
        content=_SYSTEM_PROMPT.format(
            title=paper.get("title", "Untitled"),
            authors=authors,
            journal=paper.get("journal") or "Unknown",
            published_date=paper.get("published_date") or "Unknown",
            abstract=abstract,
        )
    )


async def ask_about_paper(paper: Dict, history: List[Dict[str, str]], question: str) -> Optional[str]:
    """Answer a question about a paper, given prior turns as [{role: 'user'|'assistant', content}].

    Returns None if Gemini isn't configured or the call fails - the caller is expected to
    surface that as a "chat unavailable" response rather than a fabricated answer.
    """
    llm = _get_llm()
    if not llm:
        return None

    messages = [_build_system_message(paper)]
    for turn in history:
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if turn.get("role") == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    messages.append(HumanMessage(content=question))

    try:
        response = await llm.ainvoke(messages)
        return (response.content or "").strip() or None
    except Exception as e:
        logger.error(f"Gemini chat failed: {e}")
        return None
