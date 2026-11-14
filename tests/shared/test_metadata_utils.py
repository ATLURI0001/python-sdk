import pytest
from mcp_types import Implementation, Prompt, Resource, Tool, ToolAnnotations

from mcp.shared.metadata_utils import get_description, get_display_name, is_valid_mcp_name


def test_get_display_name_tool_precedence():
    # title > annotations.title > name
    tool_full = Tool(
        name="tool_name",
        title="Tool Title",
        annotations=ToolAnnotations(title="Annot Title"),
        inputSchema={"type": "object"},
    )
    assert get_display_name(tool_full) == "Tool Title"

    tool_annot = Tool(
        name="tool_name",
        annotations=ToolAnnotations(title="Annot Title"),
        inputSchema={"type": "object"},
    )
    assert get_display_name(tool_annot) == "Annot Title"

    tool_name_only = Tool(
        name="tool_name",
        inputSchema={"type": "object"},
    )
    assert get_display_name(tool_name_only) == "tool_name"


def test_get_display_name_blank_title_fallback():
    # Blank/whitespace title should fall back to annotations or name
    tool = Tool(
        name="fallback_name",
        title="   ",
        annotations=ToolAnnotations(title="Annot Title"),
        inputSchema={"type": "object"},
    )
    assert get_display_name(tool) == "Annot Title"

    prompt = Prompt(name="prompt_name", title="   ")
    assert get_display_name(prompt) == "prompt_name"


def test_get_display_name_dict_and_none_support():
    assert get_display_name(None) == ""
    assert get_display_name({"title": "Custom Tool", "name": "custom"}) == "Custom Tool"
    assert get_display_name({"title": "  ", "name": "custom"}) == "custom"
    assert get_display_name({"annotations": {"title": "Annot"}, "name": "custom"}) == "Annot"
    assert get_display_name({"name": "only_name"}) == "only_name"


def test_get_display_name_other_objects():
    res = Resource(name="res_name", uri="file:///test", title="Resource Title")
    assert get_display_name(res) == "Resource Title"

    impl = Implementation(name="impl_name", version="1.0.0")
    assert get_display_name(impl) == "impl_name"


def test_get_description_precedence_and_fallbacks():
    assert get_description(None) == ""
    assert get_description({"description": "Primary desc"}) == "Primary desc"
    assert get_description({"description": "   ", "annotations": {"description": "Annot desc"}}) == "Annot desc"
    assert get_description({"annotations": {"description": "Only Annot"}}) == "Only Annot"

    tool = Tool(
        name="tool_desc",
        description="Tool Description",
        inputSchema={"type": "object"},
    )
    assert get_description(tool) == "Tool Description"

    tool_blank = Tool(
        name="tool_desc",
        description="   ",
        inputSchema={"type": "object"},
    )
    assert get_description(tool_blank) == ""

    class CustomAnnot:
        description = "Annot Description"

    class CustomObject:
        description = "   "
        annotations = CustomAnnot()

    assert get_description(CustomObject()) == "Annot Description"


def test_is_valid_mcp_name():
    assert is_valid_mcp_name("valid_name") is True
    assert is_valid_mcp_name("tool-123") is True
    assert is_valid_mcp_name("a" * 64) is True

    # Too long
    assert is_valid_mcp_name("a" * 65) is False

    # Empty or non-string
    assert is_valid_mcp_name("") is False
    assert is_valid_mcp_name("   ") is False
    assert is_valid_mcp_name(None) is False
    assert is_valid_mcp_name(123) is False

    # Whitespace or control characters inside
    assert is_valid_mcp_name("name with space") is False
    assert is_valid_mcp_name("name\nwith_newline") is False
    assert is_valid_mcp_name("name\x00with_null") is False

