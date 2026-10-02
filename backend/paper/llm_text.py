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
