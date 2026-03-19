"""PyCard stage 1: minimal single-card editor."""

from __future__ import annotations

import tkinter as tk
from typing import Any


g: dict[str, Any] = {
    "edit_mode": False,
    "current_tool": "select",
    "objects": [],
    "selected_object_id": None,
    "drag": {
        "active": False,
        "object_id": None,
        "start_mouse": [0, 0],
        "start_pos": [0, 0],
    },
    "next_id": 1,
    "root": None,
    "canvas": None,
    "toolbar_frame": None,
    "tool_buttons": {},
    "menu_edit_var": None,
    "selection_rect_id": None,
}


def _sync_tool_button_styles(state: dict[str, Any]) -> None:
    for tool_name, button in state["tool_buttons"].items():
        relief = tk.SUNKEN if tool_name == state["current_tool"] else tk.RAISED
        button.configure(relief=relief)


def _sync_toolbar_visibility(state: dict[str, Any]) -> None:
    toolbar_frame = state["toolbar_frame"]
    if toolbar_frame is None:
        return
    if state["edit_mode"]:
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
    else:
        toolbar_frame.pack_forget()


def _find_object_by_id(state: dict[str, Any], object_id: int | None) -> dict[str, Any] | None:
    if object_id is None:
        return None
    for obj in state["objects"]:
        if obj["id"] == object_id:
            return obj
    return None


def _event_xy_on_canvas(state: dict[str, Any], event: tk.Event) -> tuple[int, int]:
    canvas = state["canvas"]
    x = int(canvas.canvasx(event.x_root - canvas.winfo_rootx()))
    y = int(canvas.canvasy(event.y_root - canvas.winfo_rooty()))
    return x, y


def _forward_widget_event_to_canvas(event: tk.Event, state: dict[str, Any], fn: Any) -> str | None:
    fn(event, state)
    if state["edit_mode"]:
        return "break"
    return None


def _sync_selection_visual(state: dict[str, Any]) -> None:
    selected_id = state["selected_object_id"]
    canvas = state["canvas"]

    for obj in state["objects"]:
        is_selected = obj["id"] == selected_id
        thickness = 2 if is_selected else 0
        obj["widget"].configure(highlightthickness=thickness, highlightbackground="#1f78ff")

    rect_id = state["selection_rect_id"]
    if rect_id is not None:
        canvas.delete(rect_id)
        state["selection_rect_id"] = None

    selected_obj = _find_object_by_id(state, selected_id)
    if selected_obj is None:
        return

    x = selected_obj["x"]
    y = selected_obj["y"]
    w = selected_obj["width"]
    h = selected_obj["height"]
    state["selection_rect_id"] = canvas.create_rectangle(
        x - 2,
        y - 2,
        x + w + 2,
        y + h + 2,
        outline="#1f78ff",
        width=2,
    )


def init_app() -> None:
    root = tk.Tk()
    root.title("PyCard Stage 1")
    root.resizable(True, True)

    state = g
    state["root"] = root
    state["objects"] = []
    state["selected_object_id"] = None
    state["drag"] = {
        "active": False,
        "object_id": None,
        "start_mouse": [0, 0],
        "start_pos": [0, 0],
    }
    state["next_id"] = 1

    build_menubar(root, state)
    build_toolbar(root, state)
    build_canvas(root, state)
    root.bind_all("<Delete>", lambda event: on_delete_key(event, state))

    _sync_tool_button_styles(state)
    _sync_toolbar_visibility(state)
    root.mainloop()


def build_menubar(root: tk.Tk, state: dict[str, Any]) -> None:
    menubar = tk.Menu(root)
    window_menu = tk.Menu(menubar, tearoff=0)
    edit_var = tk.BooleanVar(value=state["edit_mode"])
    state["menu_edit_var"] = edit_var
    window_menu.add_checkbutton(
        label="Edit Mode",
        variable=edit_var,
        command=lambda: toggle_edit_mode(state),
    )
    menubar.add_cascade(label="Window", menu=window_menu)
    root.configure(menu=menubar)


def build_toolbar(root: tk.Tk, state: dict[str, Any]) -> None:
    toolbar_frame = tk.Frame(root, bd=1, relief=tk.GROOVE)
    state["toolbar_frame"] = toolbar_frame

    select_btn = tk.Button(toolbar_frame, text="Select", command=lambda: set_tool(state, "select"))
    label_btn = tk.Button(toolbar_frame, text="T", width=4, command=lambda: set_tool(state, "label"))
    button_btn = tk.Button(toolbar_frame, text="Button", command=lambda: set_tool(state, "button"))

    select_btn.pack(side=tk.LEFT, padx=4, pady=4)
    label_btn.pack(side=tk.LEFT, padx=4, pady=4)
    button_btn.pack(side=tk.LEFT, padx=4, pady=4)

    state["tool_buttons"] = {
        "select": select_btn,
        "label": label_btn,
        "button": button_btn,
    }


def build_canvas(root: tk.Tk, state: dict[str, Any]) -> None:
    canvas = tk.Canvas(root, bg="white", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.bind("<Button-1>", lambda event: on_mouse_down(event, state))
    canvas.bind("<B1-Motion>", lambda event: on_mouse_move(event, state))
    canvas.bind("<ButtonRelease-1>", lambda event: on_mouse_up(event, state))
    state["canvas"] = canvas


def set_tool(state: dict[str, Any], tool_name: str) -> None:
    state["current_tool"] = tool_name
    _sync_tool_button_styles(state)


def toggle_edit_mode(state: dict[str, Any]) -> None:
    edit_var = state["menu_edit_var"]
    if edit_var is not None:
        state["edit_mode"] = bool(edit_var.get())
    else:
        state["edit_mode"] = not state["edit_mode"]
    _sync_toolbar_visibility(state)


def create_object(state: dict[str, Any], type: str, x: int, y: int) -> dict[str, Any]:
    canvas = state["canvas"]
    if type == "label":
        text = "Label"
        width, height = 80, 24
        widget = tk.Label(canvas, text=text, bd=1, relief=tk.FLAT, bg="#f8f8f8")
    elif type == "button":
        text = "Button"
        width, height = 100, 32
        widget = tk.Button(canvas, text=text)
    else:
        raise ValueError(f"Unknown object type: {type}")

    object_id = state["next_id"]
    state["next_id"] += 1

    obj = {
        "id": object_id,
        "type": type,
        "x": int(x),
        "y": int(y),
        "width": width,
        "height": height,
        "text": text,
        "widget": widget,
        "window_id": None,
    }
    widget.bind(
        "<Button-1>",
        lambda event: _forward_widget_event_to_canvas(event, state, on_mouse_down),
        add="+",
    )
    widget.bind(
        "<B1-Motion>",
        lambda event: _forward_widget_event_to_canvas(event, state, on_mouse_move),
        add="+",
    )
    widget.bind(
        "<ButtonRelease-1>",
        lambda event: _forward_widget_event_to_canvas(event, state, on_mouse_up),
        add="+",
    )
    state["objects"].append(obj)
    render_object(canvas, obj)
    select_object(state, object_id)
    return obj


def render_object(canvas: tk.Canvas, obj: dict[str, Any]) -> None:
    if obj["window_id"] is None:
        obj["window_id"] = canvas.create_window(
            obj["x"],
            obj["y"],
            anchor="nw",
            window=obj["widget"],
            width=obj["width"],
            height=obj["height"],
        )
    else:
        canvas.coords(obj["window_id"], obj["x"], obj["y"])


def select_object(state: dict[str, Any], object_id: int | None) -> None:
    state["selected_object_id"] = object_id
    _sync_selection_visual(state)


def find_object_at_position(state: dict[str, Any], x: int, y: int) -> int | None:
    for obj in reversed(state["objects"]):
        left = obj["x"]
        top = obj["y"]
        right = left + obj["width"]
        bottom = top + obj["height"]
        if left <= x <= right and top <= y <= bottom:
            return obj["id"]
    return None


def start_drag(state: dict[str, Any], event: tk.Event) -> None:
    x, y = _event_xy_on_canvas(state, event)
    object_id = find_object_at_position(state, x, y)
    select_object(state, object_id)
    if object_id is None:
        state["drag"]["active"] = False
        state["drag"]["object_id"] = None
        return

    obj = _find_object_by_id(state, object_id)
    if obj is None:
        return

    state["drag"]["active"] = True
    state["drag"]["object_id"] = object_id
    state["drag"]["start_mouse"] = [x, y]
    state["drag"]["start_pos"] = [obj["x"], obj["y"]]


def drag_move(state: dict[str, Any], event: tk.Event) -> None:
    drag = state["drag"]
    if not drag["active"]:
        return

    object_id = drag["object_id"]
    obj = _find_object_by_id(state, object_id)
    if obj is None:
        return

    x, y = _event_xy_on_canvas(state, event)
    dx = x - drag["start_mouse"][0]
    dy = y - drag["start_mouse"][1]
    obj["x"] = drag["start_pos"][0] + dx
    obj["y"] = drag["start_pos"][1] + dy
    render_object(state["canvas"], obj)
    _sync_selection_visual(state)


def end_drag(state: dict[str, Any], event: tk.Event) -> None:
    _ = event
    state["drag"]["active"] = False
    state["drag"]["object_id"] = None


def delete_selected_object(state: dict[str, Any]) -> None:
    selected_id = state["selected_object_id"]
    if selected_id is None:
        return

    obj = _find_object_by_id(state, selected_id)
    if obj is None:
        state["selected_object_id"] = None
        return

    canvas = state["canvas"]
    if obj["window_id"] is not None:
        canvas.delete(obj["window_id"])
    obj["widget"].destroy()
    state["objects"] = [item for item in state["objects"] if item["id"] != selected_id]
    state["selected_object_id"] = None
    state["drag"]["active"] = False
    state["drag"]["object_id"] = None
    _sync_selection_visual(state)


def on_delete_key(event: tk.Event, state: dict[str, Any]) -> None:
    _ = event
    if not state["edit_mode"]:
        return
    delete_selected_object(state)


def on_canvas_click(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return

    x, y = _event_xy_on_canvas(state, event)
    tool = state["current_tool"]
    if tool == "label":
        create_object(state, "label", x, y)
    elif tool == "button":
        create_object(state, "button", x, y)
    elif tool == "select":
        object_id = find_object_at_position(state, x, y)
        select_object(state, object_id)


def on_mouse_down(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return

    if state["current_tool"] == "select":
        start_drag(state, event)
    else:
        on_canvas_click(event, state)


def on_mouse_move(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    if state["current_tool"] == "select":
        drag_move(state, event)


def on_mouse_up(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    if state["current_tool"] == "select":
        end_drag(state, event)


def main() -> int:
    init_app()
    return 0
