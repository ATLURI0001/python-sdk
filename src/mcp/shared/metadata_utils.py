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

    Example:
        ```python
        # In a client displaying available tools
        tools = await session.list_tools()
        for tool in tools.tools:
            display_name = get_display_name(tool)
            print(f"Available tool: {display_name}")
        ```

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
