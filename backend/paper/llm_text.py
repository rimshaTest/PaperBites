"""Pull plain text out of a LangChain chat response.

`response.content` is a plain string for some model/library versions and a list of content blocks
for others (newer langchain-google-genai returns blocks like {"type": "text", "text": "..."},
possibly alongside non-text blocks such as reasoning). Callers that did `response.content.strip()`
crashed with "'list' object has no attribute 'strip'" on the list form.
"""
from typing import Any


def response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type", "text") == "text" and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)


def response_tokens(response: Any) -> "int | None":
    """Total tokens a call used, from the response's usage metadata when the library provides it
    (LangChain puts it on AIMessage.usage_metadata); None if unknown."""
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total
        parts = [usage.get("input_tokens"), usage.get("output_tokens")]
        if all(isinstance(p, int) for p in parts):
            return sum(parts)
    return None
