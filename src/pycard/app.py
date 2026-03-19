"""PyCard stage 1: minimal single-card editor."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
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
    "filename": None,
    "tool_default_bg": None,
    "persistence_writer": None,
    "persistence_reader": None,
    "project_dir_name": ".pycard",
}


def _sync_tool_button_styles(state: dict[str, Any]) -> None:
    active_bg = "#b8dcff"
    default_bg = state["tool_default_bg"]
    for tool_name, button in state["tool_buttons"].items():
        relief = tk.SUNKEN if tool_name == state["current_tool"] else tk.RAISED
        bg = active_bg if tool_name == state["current_tool"] else default_bg
        button.configure(relief=relief, bg=bg)


def configure_persistence(
    state: dict[str, Any],
    writer: Any | None = None,
    reader: Any | None = None,
    project_dir_name: str = ".pycard",
) -> None:
    state["persistence_writer"] = writer
    state["persistence_reader"] = reader
    state["project_dir_name"] = project_dir_name


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


def _get_widget_text(obj: dict[str, Any]) -> str:
    widget = obj["widget"]
    if obj["type"] == "entry":
        return str(widget.get())
    if obj["type"] == "text":
        return str(widget.get("1.0", "end-1c"))
    return str(obj["text"])


def _set_widget_text(obj: dict[str, Any], value: str) -> None:
    widget = obj["widget"]
    if obj["type"] == "label":
        widget.configure(text=value)
    elif obj["type"] == "button":
        widget.configure(text=value)
    elif obj["type"] == "entry":
        widget.delete(0, tk.END)
        widget.insert(0, value)
    elif obj["type"] == "text":
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)


def _serialize_payload(state: dict[str, Any]) -> dict[str, Any]:
    root = state["root"]
    root.update_idletasks()
    payload_objects = []
    for obj in state["objects"]:
        payload_objects.append(
            {
                "id": int(obj["id"]),
                "type": str(obj["type"]),
                "x": int(obj["x"]),
                "y": int(obj["y"]),
                "width": int(obj["width"]),
                "height": int(obj["height"]),
                "text": _get_widget_text(obj),
            }
        )
    return {
        "window": {
            "width": int(root.winfo_width()),
            "height": int(root.winfo_height()),
        },
        "objects": payload_objects,
    }


def _apply_loaded_payload(state: dict[str, Any], payload: dict[str, Any]) -> None:
    clear_all_objects(state)
    loaded = payload.get("objects", [])
    state["objects"] = []
    max_id = 0
    for raw in loaded:
        obj_id = int(raw["id"])
        obj = {
            "id": obj_id,
            "type": str(raw["type"]),
            "x": int(raw["x"]),
            "y": int(raw["y"]),
            "width": int(raw["width"]),
            "height": int(raw["height"]),
            "text": str(raw.get("text", "")),
            "widget": None,
            "window_id": None,
        }
        state["objects"].append(obj)
        if obj_id > max_id:
            max_id = obj_id

    state["next_id"] = max_id + 1

    window = payload.get("window", {})
    width = window.get("width")
    height = window.get("height")
    if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
        state["root"].geometry(f"{width}x{height}")

    rebuild_all_widgets(state)


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
    if not state["filename"]:
        state["filename"] = "cards.json"

    build_menubar(root, state)
    build_toolbar(root, state)
    build_canvas(root, state)
    root.bind_all("<Delete>", lambda event: on_delete_key(event, state))
    load_from_file(state)

    _sync_tool_button_styles(state)
    _sync_toolbar_visibility(state)
    root.mainloop()


def build_menubar(root: tk.Tk, state: dict[str, Any]) -> None:
    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Save", underline=0, command=lambda: save_to_file(state))
    file_menu.add_command(label="Load", underline=0, command=lambda: load_from_file(state))
    file_menu.add_separator()
    file_menu.add_command(label="Export", underline=0, command=lambda: save_as_file(state))
    file_menu.add_command(label="Import", underline=0, command=lambda: load_from_dialog(state))
    file_menu.add_separator()
    file_menu.add_command(label="Quit", underline=0, command=lambda: state["root"].quit())
    menubar.add_cascade(label="File", underline=0, menu=file_menu)

    window_menu = tk.Menu(menubar, tearoff=0)
    edit_var = tk.BooleanVar(value=state["edit_mode"])
    state["menu_edit_var"] = edit_var
    window_menu.add_checkbutton(
        label="Edit Mode",
        underline=0,
        variable=edit_var,
        command=lambda: toggle_edit_mode(state),
    )
    menubar.add_cascade(label="Window", underline=0, menu=window_menu)
    root.configure(menu=menubar)


def build_toolbar(root: tk.Tk, state: dict[str, Any]) -> None:
    toolbar_frame = tk.Frame(root, bd=1, relief=tk.GROOVE)
    state["toolbar_frame"] = toolbar_frame

    select_btn = tk.Button(toolbar_frame, text="Select", command=lambda: set_tool(state, "select"))
    label_btn = tk.Button(toolbar_frame, text="T", width=4, command=lambda: set_tool(state, "label"))
    button_btn = tk.Button(toolbar_frame, text="Button", command=lambda: set_tool(state, "button"))
    entry_btn = tk.Button(toolbar_frame, text="Entry", command=lambda: set_tool(state, "entry"))
    text_btn = tk.Button(toolbar_frame, text="Text", command=lambda: set_tool(state, "text"))

    select_btn.pack(side=tk.LEFT, padx=4, pady=4)
    label_btn.pack(side=tk.LEFT, padx=4, pady=4)
    button_btn.pack(side=tk.LEFT, padx=4, pady=4)
    entry_btn.pack(side=tk.LEFT, padx=4, pady=4)
    text_btn.pack(side=tk.LEFT, padx=4, pady=4)

    state["tool_buttons"] = {
        "select": select_btn,
        "label": label_btn,
        "button": button_btn,
        "entry": entry_btn,
        "text": text_btn,
    }
    state["tool_default_bg"] = select_btn.cget("bg")


def build_canvas(root: tk.Tk, state: dict[str, Any]) -> None:
    canvas = tk.Canvas(root, bg="white", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.bind("<Button-1>", lambda event: on_mouse_down(event, state))
    canvas.bind("<B1-Motion>", lambda event: on_mouse_move(event, state))
    canvas.bind("<ButtonRelease-1>", lambda event: on_mouse_up(event, state))
    canvas.bind("<Double-Button-1>", lambda event: handle_double_click(event, state))
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
    elif type == "entry":
        text = ""
        width, height = 120, 24
        widget = tk.Entry(canvas)
    elif type == "text":
        text = ""
        width, height = 200, 100
        widget = tk.Text(canvas)
    else:
        raise ValueError(f"Unknown object type: {type}")

    object_id = state["next_id"]
    state["next_id"] += 1

    obj = {
        "id": object_id,
        "type": type,
        "x": int(x - (width // 2)),
        "y": int(y - (height // 2)),
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
    widget.bind(
        "<Double-Button-1>",
        lambda event: _forward_widget_event_to_canvas(event, state, handle_double_click),
        add="+",
    )
    state["objects"].append(obj)
    render_object(canvas, obj)
    _set_widget_text(obj, text)
    select_object(state, object_id)
    return obj


def create_entry_object(state: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    return create_object(state, "entry", x, y)


def create_text_object(state: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    return create_object(state, "text", x, y)


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


def clear_all_objects(state: dict[str, Any]) -> None:
    canvas = state["canvas"]
    for obj in list(state["objects"]):
        if obj["window_id"] is not None:
            canvas.delete(obj["window_id"])
        obj["widget"].destroy()
    state["objects"] = []
    state["selected_object_id"] = None
    state["drag"]["active"] = False
    state["drag"]["object_id"] = None
    _sync_selection_visual(state)


def rebuild_all_widgets(state: dict[str, Any]) -> None:
    canvas = state["canvas"]
    for obj in state["objects"]:
        type_name = obj["type"]
        if type_name == "label":
            widget = tk.Label(canvas, text=obj["text"], bd=1, relief=tk.FLAT, bg="#f8f8f8")
        elif type_name == "button":
            widget = tk.Button(canvas, text=obj["text"])
        elif type_name == "entry":
            widget = tk.Entry(canvas)
        elif type_name == "text":
            widget = tk.Text(canvas)
        else:
            continue

        obj["widget"] = widget
        obj["window_id"] = None
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
        widget.bind(
            "<Double-Button-1>",
            lambda event: _forward_widget_event_to_canvas(event, state, handle_double_click),
            add="+",
        )
        render_object(canvas, obj)
        _set_widget_text(obj, obj["text"])
    _sync_selection_visual(state)


def save_to_file(state: dict[str, Any]) -> None:
    file_id = state["filename"] or "cards.json"
    state["filename"] = file_id

    payload = _serialize_payload(state)

    writer = state["persistence_writer"]
    if writer is not None:
        writer(file_id, payload, "p2")
        return

    project_dir = Path.cwd() / state["project_dir_name"]
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / file_id
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def save_as_file(state: dict[str, Any]) -> None:
    filename = filedialog.asksaveasfilename(
        title="Save Card As",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not filename:
        return

    payload = _serialize_payload(state)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_from_file(state: dict[str, Any]) -> None:
    file_id = state["filename"] or "cards.json"
    state["filename"] = file_id

    reader = state["persistence_reader"]
    if reader is not None:
        try:
            payload = reader(file_id, "p")
        except FileNotFoundError:
            return
    else:
        path = Path.cwd() / state["project_dir_name"] / file_id
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

    _apply_loaded_payload(state, payload)


def load_from_dialog(state: dict[str, Any]) -> None:
    filename = filedialog.askopenfilename(
        title="Load Card From",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not filename:
        return

    with open(filename, "r", encoding="utf-8") as f:
        payload = json.load(f)

    _apply_loaded_payload(state, payload)


def open_property_editor(state: dict[str, Any], object_id: int) -> None:
    obj = _find_object_by_id(state, object_id)
    if obj is None:
        return

    top = tk.Toplevel(state["root"])
    top.title("Edit Properties")
    top.transient(state["root"])

    tk.Label(top, text="Text").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    if obj["type"] == "text":
        text_widget: Any = tk.Text(top, width=40, height=8)
        text_widget.insert("1.0", _get_widget_text(obj))
    else:
        text_widget = tk.Entry(top, width=40)
        text_widget.insert(0, _get_widget_text(obj))
    text_widget.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    tk.Label(top, text="Width").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    width_entry = tk.Entry(top, width=12)
    width_entry.insert(0, str(obj["width"]))
    width_entry.grid(row=1, column=1, sticky="w", padx=8, pady=6)

    tk.Label(top, text="Height").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    height_entry = tk.Entry(top, width=12)
    height_entry.insert(0, str(obj["height"]))
    height_entry.grid(row=2, column=1, sticky="w", padx=8, pady=6)

    top.grid_columnconfigure(1, weight=1)

    def on_apply() -> None:
        if obj["type"] == "text":
            new_text = text_widget.get("1.0", "end-1c")
        else:
            new_text = text_widget.get()
        try:
            new_width = int(width_entry.get())
            new_height = int(height_entry.get())
        except ValueError:
            return
        apply_property_changes(
            state,
            object_id,
            {
                "text": new_text,
                "width": new_width,
                "height": new_height,
            },
        )
        top.destroy()

    tk.Button(top, text="Apply", command=on_apply).grid(row=3, column=0, padx=8, pady=10, sticky="w")
    tk.Button(top, text="Cancel", command=top.destroy).grid(row=3, column=1, padx=8, pady=10, sticky="e")


def apply_property_changes(state: dict[str, Any], object_id: int, new_values: dict[str, Any]) -> None:
    obj = _find_object_by_id(state, object_id)
    if obj is None:
        return

    text_value = str(new_values.get("text", obj["text"]))
    width_value = int(new_values.get("width", obj["width"]))
    height_value = int(new_values.get("height", obj["height"]))

    obj["text"] = text_value
    obj["width"] = max(20, width_value)
    obj["height"] = max(20, height_value)
    _set_widget_text(obj, obj["text"])
    render_object(state["canvas"], obj)
    _sync_selection_visual(state)


def handle_double_click(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    x, y = _event_xy_on_canvas(state, event)
    object_id = find_object_at_position(state, x, y)
    if object_id is None:
        return
    select_object(state, object_id)
    open_property_editor(state, object_id)


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
        set_tool(state, "select")
    elif tool == "button":
        create_object(state, "button", x, y)
        set_tool(state, "select")
    elif tool == "entry":
        create_entry_object(state, x, y)
        set_tool(state, "select")
    elif tool == "text":
        create_text_object(state, x, y)
        set_tool(state, "select")
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
