import pytest

import mcp_server


def test_mcp_import_does_not_parse_test_arguments_or_connect():
    assert mcp_server.mcp.name == "RAG Knowledge Assistant"


@pytest.mark.parametrize("value", [0, -1, 6])
def test_mcp_source_limits_are_validated(value):
    with pytest.raises(ValueError):
        mcp_server._bounded(value, "max_pages", 5)


def test_mcp_question_is_trimmed():
    assert mcp_server._question("  research this  ") == "research this"
