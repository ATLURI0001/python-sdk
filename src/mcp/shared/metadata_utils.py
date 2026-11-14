"""Utility functions for working with metadata in MCP types.

These utilities are primarily intended for client-side usage to properly display
human-readable names in user interfaces in a spec-compliant way.
"""

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
