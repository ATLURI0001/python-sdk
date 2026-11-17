import pytest
from mcp_types import Implementation, Prompt, Resource, Tool, ToolAnnotations

from mcp.shared.metadata_utils import (
    format_mcp_summary,
    get_description,
    get_display_name,
    get_mime_type,
    is_valid_mcp_name,
    is_valid_progress_token,
    is_valid_protocol_version,
    is_valid_request_id,
    is_valid_uri,
    normalize_uri,
    is_valid_cursor,
    sanitize_cursor,
    normalize_request_id,
    sanitize_mcp_name,
    sanitize_progress_token,
    validate_input_schema,
    inspect_schema_diagnostics,
)


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


def test_sanitize_mcp_name():
    assert sanitize_mcp_name("valid-tool_name") == "valid-tool_name"
    assert sanitize_mcp_name("tool with spaces and / slash") == "tool_with_spaces_and___slash"
    assert sanitize_mcp_name("   ") == "item"
    assert sanitize_mcp_name(None, fallback="default_tool") == "default_tool"
    assert len(sanitize_mcp_name("x" * 100)) == 64


def test_get_mime_type_and_format_summary():
    # Direct dictionary mimeType
    assert get_mime_type({"mimeType": "TEXT/PLAIN"}) == "text/plain"
    assert get_mime_type({"mime_type": "Application/JSON"}) == "application/json"
    assert get_mime_type({"annotations": {"mimeType": "image/png"}}) == "image/png"
    assert get_mime_type(None) == ""

    # Summary formatting
    summary = format_mcp_summary({
        "name": "read_data",
        "title": "Read Data Resource",
        "description": "Reads sensor data",
        "mimeType": "application/json",
    })
    assert summary["name"] == "read_data"
    assert summary["display_name"] == "Read Data Resource"
    assert summary["description"] == "Reads sensor data"
    assert summary["mime_type"] == "application/json"
    assert format_mcp_summary(None)["display_name"] == ""


def test_request_id_validation_and_normalization():
    # Valid integer IDs
    assert is_valid_request_id(0) is True
    assert is_valid_request_id(42) is True
    assert is_valid_request_id(-1) is True
    assert normalize_request_id(42) == 42

    # Booleans are not valid request IDs
    assert is_valid_request_id(True) is False
    assert is_valid_request_id(False) is False
    assert normalize_request_id(True) is None

    # Valid string IDs
    assert is_valid_request_id("req_123") is True
    assert is_valid_request_id("a" * 128) is True
    assert normalize_request_id("  req_abc  ") == "req_abc"

    # Invalid string IDs
    assert is_valid_request_id("") is False
    assert is_valid_request_id("   ") is False
    assert is_valid_request_id("a" * 129) is False
    assert normalize_request_id("   ") is None

    # Invalid object types
    assert is_valid_request_id(None) is False
    assert is_valid_request_id(3.14) is False
    assert is_valid_request_id({"id": 1}) is False
    assert normalize_request_id(None) is None


def test_progress_token_validation_and_sanitization():
    # Integer tokens
    assert is_valid_progress_token(101) is True
    assert is_valid_progress_token(True) is False
    assert sanitize_progress_token(101) == 101

    # String tokens
    assert is_valid_progress_token("progress-token-1") is True
    assert is_valid_progress_token("token\x00invalid") is False
    assert sanitize_progress_token(" token_clean\x1f ") == "token_clean"

    # Fallback on boolean or None
    assert sanitize_progress_token(True, fallback_prefix="prog") == "prog_0"
    assert sanitize_progress_token(None, fallback_prefix="prog") == "prog_auto"


def test_protocol_version_validation():
    # Valid date-based versions
    assert is_valid_protocol_version("2024-11-05") is True
    assert is_valid_protocol_version("2025-03-26") is True
    assert is_valid_protocol_version("2026-07-28") is True

    # Valid semver versions
    assert is_valid_protocol_version("1.0.0") is True
    assert is_valid_protocol_version("0.1.0-alpha.1") is True

    # Invalid version formats
    assert is_valid_protocol_version("") is False
    assert is_valid_protocol_version("   ") is False
    assert is_valid_protocol_version("2024-11") is False
    assert is_valid_protocol_version("v1.0") is False
    assert is_valid_protocol_version(None) is False
    assert is_valid_protocol_version(20250326) is False


def test_resource_uri_validation_and_normalization():
    # Valid URIs
    assert is_valid_uri("file:///home/user/doc.txt") is True
    assert is_valid_uri("postgres://localhost:5432/db") is True
    assert is_valid_uri("custom+protocol://resource-id") is True
    assert is_valid_uri("HTTP://example.com/api") is True

    # Normalization
    assert normalize_uri("  HTTP://Example.COM/api  ") == "http://Example.COM/api"
    assert normalize_uri("FILE:///path/file.py") == "file:///path/file.py"

    # Invalid URIs
    assert is_valid_uri("") is False
    assert is_valid_uri("   ") is False
    assert is_valid_uri("no-scheme-path/file.txt") is False
    assert is_valid_uri("123scheme://invalid") is False
    assert is_valid_uri("file://path\x00with-null") is False
    assert is_valid_uri(None) is False
    assert normalize_uri("invalid-uri") is None


def test_pagination_cursor_validation_and_sanitization():
    # Valid cursors
    assert is_valid_cursor("cursor_abc123") is True
    assert is_valid_cursor("eyJuZXh0UGFnZSI6Mn0=") is True

    # Invalid cursors
    assert is_valid_cursor("") is False
    assert is_valid_cursor("   ") is False
    assert is_valid_cursor(None) is False
    assert is_valid_cursor(12345) is False
    assert is_valid_cursor("cursor\x07bell") is False
    assert is_valid_cursor("c" * 513) is False

    # Sanitization
    assert sanitize_cursor("  cursor_token_123  ") == "cursor_token_123"
    assert sanitize_cursor("token\x00clean") == "tokenclean"
    assert sanitize_cursor("") is None
    assert sanitize_cursor(None) is None
    assert sanitize_cursor(123) is None


def test_validate_input_schema_and_diagnostics():
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "nested": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer"}
                }
            }
        },
        "required": ["name"]
    }
    is_valid, err = validate_input_schema(valid_schema)
    assert is_valid is True
    assert err is None

    diag = inspect_schema_diagnostics(valid_schema)
    assert diag["valid"] is True
    assert diag["property_count"] == 2
    assert diag["required_count"] == 1
    assert diag["max_depth"] == 2

    # Malformed schema (non-dict)
    is_valid, err = validate_input_schema("invalid")
    assert is_valid is False
    assert "must be a JSON object" in err
    bad_diag = inspect_schema_diagnostics("invalid")
    assert bad_diag["valid"] is False

    # Top-level type not object
    is_valid, err = validate_input_schema({"type": "string"})
    assert is_valid is False
    assert "must be 'object'" in err

    # Properties not dict
    is_valid, err = validate_input_schema({"type": "object", "properties": [1, 2]})
    assert is_valid is False

    # Required not list of strings
    is_valid, err = validate_input_schema({"type": "object", "required": [123]})
    assert is_valid is False



