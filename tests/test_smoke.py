from pycard.app import g, set_tool


def test_set_tool_changes_current_tool() -> None:
    g["current_tool"] = "select"
    set_tool(g, "label")
    assert g["current_tool"] == "label"
