"""Utility functions for working with metadata in MCP types.

These utilities are primarily intended for client-side usage to properly display
human-readable names in user interfaces in a spec-compliant way.
"""

import re
from typing import Any
from mcp_types import Implementation, Prompt, Resource, ResourceTemplate, Tool


def get_display_name(obj: Tool | Resource | Prompt | ResourceTemplate | Implementation | dict[str, Any] | None) -> str:
    """Get the display name for an MCP object with proper precedence.

    This is a client-side utility function designed to help MCP clients display
    human-readable names in their user interfaces. When servers provide a 'title'
    field, it should be preferred over the programmatic 'name' field for display.

    For tools: title > annotations.title > name
    For other objects: title > name

    Args:
        obj: An MCP object with name and optional title fields

    Returns:
        The display name to use for UI presentation
    """
    if obj is None:
        return ""

    if isinstance(obj, dict):
        title = obj.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
        annotations = obj.get("annotations")
        if isinstance(annotations, dict):
            annot_title = annotations.get("title")
            if isinstance(annot_title, str) and annot_title.strip():
                return annot_title.strip()
        name = obj.get("name")
        return str(name).strip() if name is not None else ""

    if isinstance(obj, Tool):
        # Tools have special precedence: title > annotations.title > name
        title = getattr(obj, "title", None)
        if title is not None and str(title).strip():
            return str(title).strip()
        annotations = getattr(obj, "annotations", None)
        if annotations is not None:
            if hasattr(annotations, "title") and annotations.title is not None and str(annotations.title).strip():
                return str(annotations.title).strip()
            if isinstance(annotations, dict):
                annot_title = annotations.get("title")
                if annot_title is not None and str(annot_title).strip():
                    return str(annot_title).strip()
        name = getattr(obj, "name", "")
        return str(name).strip() if name is not None else ""
    else:
        # All other objects: title > name
        title = getattr(obj, "title", None)
        if title is not None and str(title).strip():
            return str(title).strip()
        name = getattr(obj, "name", "")
        return str(name).strip() if name is not None else ""


def get_description(obj: Tool | Resource | Prompt | ResourceTemplate | Implementation | dict[str, Any] | None) -> str:
    """Get the human-readable description for an MCP object with fallback to annotations.

    For tools: description > annotations.description > ""
    For other objects: description > ""

    Args:
        obj: An MCP object (Tool, Resource, Prompt, dict, etc.)

    Returns:
        The description string to use for documentation or UI presentation
    """
    if obj is None:
        return ""

    if isinstance(obj, dict):
        desc = obj.get("description")
        if isinstance(desc, str) and desc.strip():
            return desc.strip()
        annotations = obj.get("annotations")
        if isinstance(annotations, dict):
            annot_desc = annotations.get("description")
            if isinstance(annot_desc, str) and annot_desc.strip():
                return annot_desc.strip()
        return ""

    desc = getattr(obj, "description", None)
    if desc is not None and str(desc).strip():
        return str(desc).strip()

    annotations = getattr(obj, "annotations", None)
    if annotations is not None:
        if hasattr(annotations, "description") and annotations.description is not None and str(annotations.description).strip():
            return str(annotations.description).strip()
        if isinstance(annotations, dict):
            annot_desc = annotations.get("description")
            if annot_desc is not None and str(annot_desc).strip():
                return str(annot_desc).strip()

    return ""


def is_valid_mcp_name(name: Any) -> bool:
    """Validate whether an identifier meets MCP name constraints.

    Names must be non-empty strings between 1 and 64 characters containing
    no control characters or whitespace.
    """
    if not isinstance(name, str):
        return False
    name = name.strip()
    if not name or len(name) > 64:
        return False
    for ch in name:
        if ch.isspace() or ord(ch) < 32 or ord(ch) == 127:
            return False
    return True


def sanitize_mcp_name(name: Any, fallback: str = "item") -> str:
    """Sanitize arbitrary input into a valid MCP name conforming to protocol constraints.

    Replaces invalid characters and whitespace with underscores and truncates to 64 chars.
    """
    if not isinstance(name, str) or not name.strip():
        return fallback[:64] if fallback else "item"
    cleaned = []
    for ch in name.strip():
        if ch.isspace() or ord(ch) < 32 or ord(ch) == 127 or ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
            cleaned.append("_")
        else:
            cleaned.append(ch)
    result = "".join(cleaned).strip("_")
    if not result:
        return fallback[:64] if fallback else "item"
    return result[:64]


def get_mime_type(obj: Any) -> str:
    """Extract and normalize the MIME type for an MCP object or resource representation."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        mime = obj.get("mimeType") or obj.get("mime_type")
        if isinstance(mime, str) and mime.strip():
            return mime.strip().lower()
        annotations = obj.get("annotations")
        if isinstance(annotations, dict):
            annot_mime = annotations.get("mimeType") or annotations.get("mime_type")
            if isinstance(annot_mime, str) and annot_mime.strip():
                return annot_mime.strip().lower()
        return ""

    mime = getattr(obj, "mimeType", None) or getattr(obj, "mime_type", None)
    if mime is not None and str(mime).strip():
        return str(mime).strip().lower()

    annotations = getattr(obj, "annotations", None)
    if annotations is not None:
        annot_mime = getattr(annotations, "mimeType", None) or getattr(annotations, "mime_type", None)
        if annot_mime is not None and str(annot_mime).strip():
            return str(annot_mime).strip().lower()
        if isinstance(annotations, dict):
            annot_mime = annotations.get("mimeType") or annotations.get("mime_type")
            if annot_mime is not None and str(annot_mime).strip():
                return str(annot_mime).strip().lower()

    return ""


def format_mcp_summary(obj: Any) -> dict[str, str]:
    """Generate a consistent metadata dictionary for display and telemetry."""
    raw_name = ""
    if isinstance(obj, dict):
        raw_name = str(obj.get("name") or "")
    elif obj is not None:
        raw_name = str(getattr(obj, "name", "") or "")

    return {
        "name": raw_name.strip(),
        "display_name": get_display_name(obj),
        "description": get_description(obj),
        "mime_type": get_mime_type(obj),
    }


def is_valid_request_id(id_val: Any) -> bool:
    """Validate whether an identifier meets JSON-RPC 2.0 / MCP request ID constraints.

    Must be an integer (excluding bools) or a non-empty string with length <= 128 characters.
    """
    if isinstance(id_val, bool):
        return False
    if isinstance(id_val, int):
        return True
    if isinstance(id_val, str):
        trimmed = id_val.strip()
        return bool(trimmed) and len(trimmed) <= 128
    return False


def normalize_request_id(id_val: Any) -> int | str | None:
    """Normalize a JSON-RPC / MCP request identifier.

    Returns the integer or trimmed string if valid, or None if the input is malformed.
    """
    if isinstance(id_val, bool):
        return None
    if isinstance(id_val, int):
        return id_val
    if isinstance(id_val, str):
        trimmed = id_val.strip()
        if trimmed and len(trimmed) <= 128:
            return trimmed
    return None


def is_valid_progress_token(token: Any) -> bool:
    """Validate whether a token meets MCP progress token constraints.

    Must be an integer (excluding bool) or non-empty string <= 128 chars without control characters.
    """
    if isinstance(token, bool):
        return False
    if isinstance(token, int):
        return True
    if isinstance(token, str):
        trimmed = token.strip()
        if not trimmed or len(trimmed) > 128:
            return False
        return not any(ord(c) < 32 or ord(c) == 127 for c in trimmed)
    return False


def sanitize_progress_token(token: Any, fallback_prefix: str = "token") -> int | str:
    """Sanitize arbitrary input into a valid MCP progress token."""
    if isinstance(token, bool):
        return f"{fallback_prefix}_0"
    if isinstance(token, int):
        return token
    if isinstance(token, str):
        cleaned = [c for c in token.strip() if ord(c) >= 32 and ord(c) != 127]
        result = "".join(cleaned).strip()
        if result:
            return result[:128]
    return f"{fallback_prefix}_auto"


def is_valid_protocol_version(version: Any) -> bool:
    """Validate whether a version string matches standard MCP date-based (YYYY-MM-DD) or semver format."""
    if not isinstance(version, str):
        return False
    v = version.strip()
    if not v or len(v) > 32:
        return False
    # Date-based: YYYY-MM-DD
    if re.fullmatch(r"^\d{4}-\d{2}-\d{2}$", v):
        return True
    # Semver: X.Y.Z
    if re.fullmatch(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$", v):
        return True
    return False

