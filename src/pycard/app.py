"""PyCard application."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any


g: dict[str, Any] = {
    "edit_mode": False,
    "current_tool": "select",
    "stack": {
        "cards": [],
        "current_card_id": None,
        "next_card_id": 1,
    },
    "selected_object_id": None,
    "drag": {
        "active": False,
        "object_id": None,
        "start_mouse": [0, 0],
        "start_pos": [0, 0],
    },
    "resize": {
        "active": False,
        "object_id": None,
        "handle": None,
        "start_mouse": [0, 0],
        "start_geom": {
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
        },
    },
    "selection_overlay": {
        "box_item_id": None,
        "handle_item_ids": [],
    },
    "next_object_id": 1,
    "filename": "cards.json",
    "root": None,
    "canvas": None,
    "toolbar_window": None,
    "tool_buttons": {},
    "tool_default_bg": None,
    "menu_edit_var": None,
    "persistence_writer": None,
    "persistence_reader": None,
    "project_dir_name": ".pycard",
}


def configure_persistence(
    state: dict[str, Any],
    writer: Any | None = None,
    reader: Any | None = None,
    project_dir_name: str = ".pycard",
) -> None:
    state["persistence_writer"] = writer
    state["persistence_reader"] = reader
    state["project_dir_name"] = project_dir_name


def get_current_card(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return the currently visible card, or None."""
    current_card_id = state["stack"]["current_card_id"]
    return get_card_by_id(state, current_card_id)


def get_card_by_id(state: dict[str, Any], card_id: int | None) -> dict[str, Any] | None:
    """Return a card by numeric id, or None."""
    if card_id is None:
        return None
    for card in state["stack"]["cards"]:
        if card["id"] == card_id:
            return card
    return None


def get_card_by_name(state: dict[str, Any], card_name: str) -> dict[str, Any] | None:
    """Return the first card whose name matches card_name."""
    for card in state["stack"]["cards"]:
        if card["name"] == card_name:
            return card
    return None


def _card_title(state: dict[str, Any]) -> str:
    card = get_current_card(state)
    if card is None:
        return "PyCard"
    return f"PyCard - {card['name']}"


def _update_window_title(state: dict[str, Any]) -> None:
    root = state["root"]
    if root is not None:
        root.title(_card_title(state))


def create_new_stack(state: dict[str, Any]) -> None:
    """Replace stack state with a fresh one-card stack."""
    clear_rendered_card(state)
    state["stack"] = {
        "cards": [],
        "current_card_id": None,
        "next_card_id": 1,
    }
    state["next_object_id"] = 1
    state["selected_object_id"] = None
    state["filename"] = "cards.json"
    create_new_card(state)


def create_new_card(state: dict[str, Any], name: str | None = None) -> dict[str, Any]:
    """Create a card, append it to the stack, and show it."""
    card_id = state["stack"]["next_card_id"]
    state["stack"]["next_card_id"] += 1
    if name is None:
        name = f"Card {card_id}"
    card = {
        "id": card_id,
        "name": name,
        "objects": [],
    }
    state["stack"]["cards"].append(card)
    show_card_by_id(state, card_id)
    return card


def show_card_by_id(state: dict[str, Any], card_id: int | None) -> None:
    """Switch the visible card by id."""
    if get_card_by_id(state, card_id) is None:
        return
    clear_rendered_card(state)
    state["stack"]["current_card_id"] = card_id
    render_current_card(state)
    _update_window_title(state)


def show_next_card(state: dict[str, Any]) -> None:
    """Show the next card in stack order."""
    cards = state["stack"]["cards"]
    if not cards:
        return
    current_card_id = state["stack"]["current_card_id"]
    current_index = 0
    for index, card in enumerate(cards):
        if card["id"] == current_card_id:
            current_index = index
            break
    next_index = (current_index + 1) % len(cards)
    show_card_by_id(state, cards[next_index]["id"])


def show_previous_card(state: dict[str, Any]) -> None:
    """Show the previous card in stack order."""
    cards = state["stack"]["cards"]
    if not cards:
        return
    current_card_id = state["stack"]["current_card_id"]
    current_index = 0
    for index, card in enumerate(cards):
        if card["id"] == current_card_id:
            current_index = index
            break
    prev_index = (current_index - 1) % len(cards)
    show_card_by_id(state, cards[prev_index]["id"])


def goto_card(state: dict[str, Any], card_name: str) -> None:
    """Switch the current card to the first card whose name matches card_name."""
    card = get_card_by_name(state, card_name)
    if card is not None:
        show_card_by_id(state, card["id"])


def _sync_tool_button_styles(state: dict[str, Any]) -> None:
    active_bg = "#b8dcff"
    default_bg = state["tool_default_bg"]
    for tool_name, button in state["tool_buttons"].items():
        relief = tk.SUNKEN if tool_name == state["current_tool"] else tk.RAISED
        bg = active_bg if tool_name == state["current_tool"] else default_bg
        button.configure(relief=relief, bg=bg)


def _sync_toolbar_visibility(state: dict[str, Any]) -> None:
    toolbar_window = state["toolbar_window"]
    root = state["root"]
    if toolbar_window is None or root is None:
        return
    if state["edit_mode"]:
        root.update_idletasks()
        x = root.winfo_rootx() + 20
        y = root.winfo_rooty() + root.winfo_height() + 8
        toolbar_window.geometry(f"+{x}+{y}")
        toolbar_window.deiconify()
        toolbar_window.lift()
    else:
        toolbar_window.withdraw()


def find_object_by_id(state: dict[str, Any], object_id: int) -> dict[str, Any] | None:
    """Return the object with this integer id, or None if not found."""
    for card in state["stack"]["cards"]:
        for obj in card["objects"]:
            if obj["id"] == object_id:
                return obj
    return None


def find_object_by_text(state: dict[str, Any], text: str) -> dict[str, Any] | None:
    """Return the first object whose visible text/content equals text."""
    for card in state["stack"]["cards"]:
        for obj in card["objects"]:
            if _get_widget_text(obj) == text:
                return obj
    return None


def find_object_by_name(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Return the first object with this name string, or None if not found."""
    target = str(name)
    for card in state["stack"]["cards"]:
        for obj in card["objects"]:
            if str(obj.get("name", "")) == target:
                return obj
    return None


def resolve_object_ref(state: dict[str, Any], obj_ref: Any) -> dict[str, Any] | None:
    """Resolve an object reference from object dict, id int, or name str."""
    if isinstance(obj_ref, dict):
        object_id = obj_ref.get("id")
        if isinstance(object_id, int):
            return find_object_by_id(state, object_id)
        return obj_ref
    if isinstance(obj_ref, int):
        return find_object_by_id(state, obj_ref)
    if isinstance(obj_ref, str):
        return find_object_by_name(state, obj_ref)
    return None


def set_object_text(state: dict[str, Any], obj_ref: Any, new_text: str) -> None:
    """Set an object's text/content by object dict, id, or name; refresh widget."""
    obj = resolve_object_ref(state, obj_ref)
    if obj is None:
        return
    obj["text"] = str(new_text)
    _set_widget_text(obj, obj["text"])
    if obj.get("widget") is not None:
        render_object(state, obj)
        draw_selection_overlay(state)


def get_object_text(state: dict[str, Any], obj_or_id: Any) -> str:
    """Return text/content for an object dict, object id, or object name string."""
    obj = resolve_object_ref(state, obj_or_id)
    if obj is None:
        return ""
    return _get_widget_text(obj)


def build_execution_context(state: dict[str, Any]) -> dict[str, Any]:
    def _find_object_by_id(object_id: int) -> dict[str, Any] | None:
        """find_object_by_id(object_id: int) -> dict | None

        Return the object with this integer id, or None if not found.
        """
        return find_object_by_id(state, object_id)

    def _find_object_by_name(name: str) -> dict[str, Any] | None:
        """find_object_by_name(name: str) -> dict | None

        Return the first object with this name string, or None if not found.
        """
        return find_object_by_name(state, name)

    def _find_object_by_text(text: str) -> dict[str, Any] | None:
        """find_object_by_text(text: str) -> dict | None

        Return the first object whose visible text/content equals text.
        """
        return find_object_by_text(state, text)

    def _get_text(obj: Any) -> str:
        """get_text(obj: dict | int | str) -> str

        Return text/content for an object dict, object id, or object name string.
        Returns empty string if the object cannot be resolved.
        """
        return get_object_text(state, obj)

    def _set_text(obj: Any, new_text: str) -> None:
        """set_text(obj: dict | int | str, new_text: str) -> None

        Set an object's text/content by object dict, id, or object name string.
        """
        set_object_text(state, obj, new_text)

    def _goto_card(card_name: str) -> None:
        """goto_card(card_name: str) -> None

        Switch the current visible card to the first card whose name matches card_name.
        """
        goto_card(state, card_name)

    return {
        "state": state,
        "find_object_by_id": _find_object_by_id,
        "find_object_by_name": _find_object_by_name,
        "find_object_by_text": _find_object_by_text,
        "get_text": _get_text,
        "set_text": _set_text,
        "goto_card": _goto_card,
        "print": print,
    }


def run_button_script(state: dict[str, Any], object_id: int) -> None:
    """Execute a button object's on_click_code in run mode."""
    if state["edit_mode"]:
        return
    obj = find_object_by_id(state, object_id)
    if obj is None or obj["type"] != "button":
        return
    code = str(obj.get("on_click_code", "")).strip()
    if not code:
        return
    local_context = build_execution_context(state)
    try:
        exec(code, {}, local_context)
    except Exception as exc:  # noqa: BLE001
        print(f"[pycard] button script error (id={object_id}): {exc}")


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
    widget = obj.get("widget")
    if widget is None:
        return str(obj.get("text", ""))
    if obj["type"] == "entry":
        return str(widget.get())
    if obj["type"] == "text":
        return str(widget.get("1.0", "end-1c"))
    return str(obj.get("text", ""))


def _set_widget_text(obj: dict[str, Any], value: str) -> None:
    widget = obj.get("widget")
    if widget is None:
        return
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


def _serialize_stack_payload(state: dict[str, Any]) -> dict[str, Any]:
    root = state["root"]
    root.update_idletasks()
    cards_payload: list[dict[str, Any]] = []
    for card in state["stack"]["cards"]:
        card_objects = []
        for obj in card["objects"]:
            card_objects.append(
                {
                    "id": int(obj["id"]),
                    "type": str(obj["type"]),
                    "name": str(obj.get("name", str(obj["id"]))),
                    "x": int(obj["x"]),
                    "y": int(obj["y"]),
                    "width": int(obj["width"]),
                    "height": int(obj["height"]),
                    "text": _get_widget_text(obj),
                    "on_click_code": str(obj.get("on_click_code", "")),
                }
            )
        cards_payload.append(
            {
                "id": int(card["id"]),
                "name": str(card["name"]),
                "objects": card_objects,
            }
        )
    return {
        "window": {
            "width": int(root.winfo_width()),
            "height": int(root.winfo_height()),
        },
        "stack": {
            "cards": cards_payload,
            "current_card_id": state["stack"]["current_card_id"],
            "next_card_id": state["stack"]["next_card_id"],
        },
        "next_object_id": state["next_object_id"],
    }


def _apply_loaded_payload(state: dict[str, Any], payload: dict[str, Any]) -> None:
    clear_rendered_card(state)
    stack_payload = payload.get("stack", {})
    cards_payload = stack_payload.get("cards", [])
    cards: list[dict[str, Any]] = []
    for raw_card in cards_payload:
        card_objects = []
        for raw_obj in raw_card.get("objects", []):
            card_objects.append(
                {
                    "id": int(raw_obj["id"]),
                    "type": str(raw_obj["type"]),
                    "name": str(raw_obj.get("name", str(raw_obj["id"]))),
                    "x": int(raw_obj["x"]),
                    "y": int(raw_obj["y"]),
                    "width": int(raw_obj["width"]),
                    "height": int(raw_obj["height"]),
                    "text": str(raw_obj.get("text", "")),
                    "on_click_code": str(raw_obj.get("on_click_code", "")),
                    "widget": None,
                    "window_id": None,
                }
            )
        cards.append(
            {
                "id": int(raw_card["id"]),
                "name": str(raw_card.get("name", f"Card {raw_card['id']}")),
                "objects": card_objects,
            }
        )

    if not cards:
        state["stack"] = {
            "cards": [],
            "current_card_id": None,
            "next_card_id": 1,
        }
        state["next_object_id"] = 1
        create_new_card(state)
        return

    state["stack"] = {
        "cards": cards,
        "current_card_id": stack_payload.get("current_card_id"),
        "next_card_id": int(stack_payload.get("next_card_id", len(cards) + 1)),
    }
    state["next_object_id"] = int(payload.get("next_object_id", 1))
    current_card_id = state["stack"]["current_card_id"]
    if get_card_by_id(state, current_card_id) is None:
        state["stack"]["current_card_id"] = cards[0]["id"]

    window = payload.get("window", {})
    width = window.get("width")
    height = window.get("height")
    if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
        state["root"].geometry(f"{width}x{height}")
    render_current_card(state)
    _update_window_title(state)


def clear_selection_overlay(state: dict[str, Any]) -> None:
    overlay = state["selection_overlay"]
    canvas = state["canvas"]
    if canvas is None:
        return
    box_item_id = overlay["box_item_id"]
    if box_item_id is not None:
        canvas.delete(box_item_id)
        overlay["box_item_id"] = None
    for item_id in overlay["handle_item_ids"]:
        canvas.delete(item_id)
    overlay["handle_item_ids"] = []


def draw_selection_overlay(state: dict[str, Any]) -> None:
    clear_selection_overlay(state)
    if not state["edit_mode"]:
        return
    obj = find_object_by_id(state, state["selected_object_id"])
    if obj is None or obj.get("window_id") is None:
        return
    canvas = state["canvas"]
    x = obj["x"]
    y = obj["y"]
    width = obj["width"]
    height = obj["height"]
    overlay = state["selection_overlay"]
    overlay["box_item_id"] = canvas.create_rectangle(
        x - 2,
        y - 2,
        x + width + 2,
        y + height + 2,
        outline="#1f78ff",
        width=2,
    )
    handle_size = 6
    corners = {
        "nw": (x, y),
        "ne": (x + width, y),
        "sw": (x, y + height),
        "se": (x + width, y + height),
    }
    for _, (cx, cy) in corners.items():
        item_id = canvas.create_rectangle(
            cx - handle_size // 2,
            cy - handle_size // 2,
            cx + handle_size // 2,
            cy + handle_size // 2,
            fill="#1f78ff",
            outline="#1f78ff",
        )
        overlay["handle_item_ids"].append(item_id)


def clear_selection(state: dict[str, Any]) -> None:
    state["selected_object_id"] = None
    state["drag"]["active"] = False
    state["drag"]["object_id"] = None
    state["resize"]["active"] = False
    state["resize"]["object_id"] = None
    state["resize"]["handle"] = None
    clear_selection_overlay(state)


def clear_rendered_card(state: dict[str, Any]) -> None:
    clear_selection(state)
    card = get_current_card(state)
    if card is None:
        return
    canvas = state["canvas"]
    if canvas is None:
        return
    for obj in card["objects"]:
        if obj.get("window_id") is not None:
            canvas.delete(obj["window_id"])
            obj["window_id"] = None
        widget = obj.get("widget")
        if widget is not None:
            widget.destroy()
            obj["widget"] = None


def _make_widget_for_object(state: dict[str, Any], obj: dict[str, Any]) -> tk.Widget:
    canvas = state["canvas"]
    if obj["type"] == "label":
        widget: tk.Widget = tk.Label(canvas, text=obj["text"], bd=1, relief=tk.FLAT, bg="#f8f8f8")
    elif obj["type"] == "button":
        widget = tk.Button(
            canvas,
            text=obj["text"],
            command=lambda oid=obj["id"]: run_button_script(state, oid),
        )
    elif obj["type"] == "entry":
        widget = tk.Entry(canvas)
    elif obj["type"] == "text":
        widget = tk.Text(canvas)
    else:
        raise ValueError(f"Unknown object type: {obj['type']}")

    widget.bind(
        "<Button-1>",
        lambda event: _forward_widget_event_to_canvas(event, state, handle_canvas_mouse_down),
        add="+",
    )
    widget.bind(
        "<B1-Motion>",
        lambda event: _forward_widget_event_to_canvas(event, state, handle_canvas_mouse_move),
        add="+",
    )
    widget.bind(
        "<ButtonRelease-1>",
        lambda event: _forward_widget_event_to_canvas(event, state, handle_canvas_mouse_up),
        add="+",
    )
    widget.bind(
        "<Double-Button-1>",
        lambda event: _forward_widget_event_to_canvas(event, state, handle_double_click),
        add="+",
    )
    return widget


def render_current_card(state: dict[str, Any]) -> None:
    card = get_current_card(state)
    if card is None:
        return
    for obj in card["objects"]:
        render_object(state, obj)
    draw_selection_overlay(state)
    _update_window_title(state)


def render_object(state: dict[str, Any], obj: dict[str, Any]) -> None:
    canvas = state["canvas"]
    if obj.get("widget") is None:
        obj["widget"] = _make_widget_for_object(state, obj)
        _set_widget_text(obj, obj["text"])
    if obj.get("window_id") is None:
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
        canvas.itemconfigure(obj["window_id"], width=obj["width"], height=obj["height"])
    _set_widget_text(obj, obj["text"])


def _current_card_objects(state: dict[str, Any]) -> list[dict[str, Any]]:
    card = get_current_card(state)
    if card is None:
        return []
    return card["objects"]


def create_object(state: dict[str, Any], type_name: str, x: int, y: int) -> dict[str, Any]:
    defaults = {
        "label": {"text": "Label", "width": 80, "height": 24, "on_click_code": ""},
        "button": {"text": "Button", "width": 100, "height": 32, "on_click_code": ""},
        "entry": {"text": "", "width": 120, "height": 24, "on_click_code": ""},
        "text": {"text": "", "width": 200, "height": 100, "on_click_code": ""},
    }
    data = defaults[type_name]
    object_id = state["next_object_id"]
    state["next_object_id"] += 1
    obj = {
        "id": object_id,
        "type": type_name,
        "name": str(object_id),
        "x": int(x - (data["width"] // 2)),
        "y": int(y - (data["height"] // 2)),
        "width": int(data["width"]),
        "height": int(data["height"]),
        "text": str(data["text"]),
        "on_click_code": str(data["on_click_code"]),
        "widget": None,
        "window_id": None,
    }
    card = get_current_card(state)
    if card is None:
        create_new_card(state)
        card = get_current_card(state)
    card["objects"].append(obj)
    render_object(state, obj)
    select_object(state, object_id)
    return obj


def create_entry_object(state: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    return create_object(state, "entry", x, y)


def create_text_object(state: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    return create_object(state, "text", x, y)


def find_object_at_position(state: dict[str, Any], x: int, y: int) -> int | None:
    for obj in reversed(_current_card_objects(state)):
        left = obj["x"]
        top = obj["y"]
        right = left + obj["width"]
        bottom = top + obj["height"]
        if left <= x <= right and top <= y <= bottom:
            return obj["id"]
    return None


def select_object(state: dict[str, Any], object_id: int | None) -> None:
    state["selected_object_id"] = object_id
    draw_selection_overlay(state)


def get_resize_handle_at_position(state: dict[str, Any], x: int, y: int) -> str | None:
    obj = find_object_by_id(state, state["selected_object_id"])
    if obj is None:
        return None
    handle_size = 8
    corners = {
        "nw": (obj["x"], obj["y"]),
        "ne": (obj["x"] + obj["width"], obj["y"]),
        "sw": (obj["x"], obj["y"] + obj["height"]),
        "se": (obj["x"] + obj["width"], obj["y"] + obj["height"]),
    }
    for handle, (cx, cy) in corners.items():
        if abs(x - cx) <= handle_size and abs(y - cy) <= handle_size:
            return handle
    return None


def start_drag(state: dict[str, Any], event: tk.Event) -> None:
    x, y = _event_xy_on_canvas(state, event)
    object_id = find_object_at_position(state, x, y)
    if object_id is None:
        clear_selection(state)
        return
    select_object(state, object_id)
    obj = find_object_by_id(state, object_id)
    if obj is None:
        return
    state["drag"]["active"] = True
    state["drag"]["object_id"] = object_id
    state["drag"]["start_mouse"] = [x, y]
    state["drag"]["start_pos"] = [obj["x"], obj["y"]]


def drag_move(state: dict[str, Any], event: tk.Event) -> None:
    if not state["drag"]["active"]:
        return
    obj = find_object_by_id(state, state["drag"]["object_id"])
    if obj is None:
        return
    x, y = _event_xy_on_canvas(state, event)
    dx = x - state["drag"]["start_mouse"][0]
    dy = y - state["drag"]["start_mouse"][1]
    update_object_geometry(
        state,
        obj["id"],
        state["drag"]["start_pos"][0] + dx,
        state["drag"]["start_pos"][1] + dy,
        obj["width"],
        obj["height"],
    )


def end_drag(state: dict[str, Any], event: tk.Event) -> None:
    _ = event
    state["drag"]["active"] = False
    state["drag"]["object_id"] = None


def start_resize(state: dict[str, Any], event: tk.Event, object_id: int, handle: str) -> None:
    obj = find_object_by_id(state, object_id)
    if obj is None:
        return
    x, y = _event_xy_on_canvas(state, event)
    state["resize"]["active"] = True
    state["resize"]["object_id"] = object_id
    state["resize"]["handle"] = handle
    state["resize"]["start_mouse"] = [x, y]
    state["resize"]["start_geom"] = {
        "x": obj["x"],
        "y": obj["y"],
        "width": obj["width"],
        "height": obj["height"],
    }


def resize_move(state: dict[str, Any], event: tk.Event) -> None:
    if not state["resize"]["active"]:
        return
    object_id = state["resize"]["object_id"]
    obj = find_object_by_id(state, object_id)
    if obj is None:
        return
    x, y = _event_xy_on_canvas(state, event)
    start = state["resize"]["start_geom"]
    dx = x - state["resize"]["start_mouse"][0]
    dy = y - state["resize"]["start_mouse"][1]
    handle = state["resize"]["handle"]

    new_x = start["x"]
    new_y = start["y"]
    new_width = start["width"]
    new_height = start["height"]

    if handle == "nw":
        new_x = start["x"] + dx
        new_y = start["y"] + dy
        new_width = start["width"] - dx
        new_height = start["height"] - dy
    elif handle == "ne":
        new_y = start["y"] + dy
        new_width = start["width"] + dx
        new_height = start["height"] - dy
    elif handle == "sw":
        new_x = start["x"] + dx
        new_width = start["width"] - dx
        new_height = start["height"] + dy
    elif handle == "se":
        new_width = start["width"] + dx
        new_height = start["height"] + dy

    min_width = 20
    min_height = 20
    if new_width < min_width:
        if handle in {"nw", "sw"}:
            new_x -= min_width - new_width
        new_width = min_width
    if new_height < min_height:
        if handle in {"nw", "ne"}:
            new_y -= min_height - new_height
        new_height = min_height

    update_object_geometry(state, object_id, new_x, new_y, new_width, new_height)


def end_resize(state: dict[str, Any], event: tk.Event) -> None:
    _ = event
    state["resize"]["active"] = False
    state["resize"]["object_id"] = None
    state["resize"]["handle"] = None


def update_object_geometry(
    state: dict[str, Any],
    object_id: int,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    obj = find_object_by_id(state, object_id)
    if obj is None:
        return
    obj["x"] = int(x)
    obj["y"] = int(y)
    obj["width"] = max(20, int(width))
    obj["height"] = max(20, int(height))
    if obj.get("widget") is not None:
        render_object(state, obj)
        draw_selection_overlay(state)


def save_to_file(state: dict[str, Any]) -> None:
    file_id = state["filename"] or "cards.json"
    state["filename"] = file_id
    payload = _serialize_stack_payload(state)
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
        title="Export Stack",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not filename:
        return
    payload = _serialize_stack_payload(state)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_from_file(state: dict[str, Any]) -> None:
    file_id = state["filename"] or "cards.json"
    state["filename"] = file_id
    reader = state["persistence_reader"]
    try:
        if reader is not None:
            payload = reader(file_id, "p")
        else:
            path = Path.cwd() / state["project_dir_name"] / file_id
            if not path.exists():
                return
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
    except FileNotFoundError:
        return
    _apply_loaded_payload(state, payload)


def load_from_dialog(state: dict[str, Any]) -> None:
    filename = filedialog.askopenfilename(
        title="Import Stack",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not filename:
        return
    with open(filename, "r", encoding="utf-8") as f:
        payload = json.load(f)
    _apply_loaded_payload(state, payload)


def open_property_editor(state: dict[str, Any], object_id: int) -> None:
    obj = find_object_by_id(state, object_id)
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

    tk.Label(top, text="Name").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    name_entry = tk.Entry(top, width=40)
    name_entry.insert(0, str(obj.get("name", str(obj["id"]))))
    name_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    tk.Label(top, text="Width").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    width_entry = tk.Entry(top, width=12)
    width_entry.insert(0, str(obj["width"]))
    width_entry.grid(row=2, column=1, sticky="w", padx=8, pady=6)

    tk.Label(top, text="Height").grid(row=3, column=0, sticky="w", padx=8, pady=6)
    height_entry = tk.Entry(top, width=12)
    height_entry.insert(0, str(obj["height"]))
    height_entry.grid(row=3, column=1, sticky="w", padx=8, pady=6)

    script_widget: Any = None
    if obj["type"] == "button":
        tk.Label(top, text="On Click Code").grid(row=4, column=0, sticky="nw", padx=8, pady=6)
        script_widget = tk.Text(top, width=40, height=8)
        script_widget.insert("1.0", str(obj.get("on_click_code", "")))
        script_widget.grid(row=4, column=1, sticky="ew", padx=8, pady=6)

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
        new_values = {
            "text": new_text,
            "name": name_entry.get().strip() or str(obj["id"]),
            "width": new_width,
            "height": new_height,
        }
        if script_widget is not None:
            new_values["on_click_code"] = script_widget.get("1.0", "end-1c")
        apply_property_changes(state, object_id, new_values)
        top.destroy()

    row = 5 if obj["type"] == "button" else 4
    tk.Button(top, text="Apply", command=on_apply).grid(row=row, column=0, padx=8, pady=10, sticky="w")
    tk.Button(top, text="Cancel", command=top.destroy).grid(row=row, column=1, padx=8, pady=10, sticky="e")


def apply_property_changes(state: dict[str, Any], object_id: int, new_values: dict[str, Any]) -> None:
    obj = find_object_by_id(state, object_id)
    if obj is None:
        return
    obj["text"] = str(new_values.get("text", obj["text"]))
    obj["name"] = str(new_values.get("name", obj["name"]))
    obj["width"] = max(20, int(new_values.get("width", obj["width"])))
    obj["height"] = max(20, int(new_values.get("height", obj["height"])))
    if obj["type"] == "button" and new_values.get("on_click_code") is not None:
        obj["on_click_code"] = str(new_values["on_click_code"])
    render_object(state, obj)
    draw_selection_overlay(state)


def handle_double_click(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    x, y = _event_xy_on_canvas(state, event)
    object_id = find_object_at_position(state, x, y)
    if object_id is None:
        return
    select_object(state, object_id)
    open_property_editor(state, object_id)


def delete_selected_object(state: dict[str, Any]) -> None:
    object_id = state["selected_object_id"]
    if object_id is None:
        return
    card = get_current_card(state)
    if card is None:
        return
    obj = find_object_by_id(state, object_id)
    if obj is None:
        clear_selection(state)
        return
    if obj.get("window_id") is not None:
        state["canvas"].delete(obj["window_id"])
    widget = obj.get("widget")
    if widget is not None:
        widget.destroy()
    card["objects"] = [item for item in card["objects"] if item["id"] != object_id]
    clear_selection(state)


def set_tool(state: dict[str, Any], tool_name: str) -> None:
    state["current_tool"] = tool_name
    _sync_tool_button_styles(state)


def toggle_edit_mode(state: dict[str, Any]) -> None:
    edit_var = state["menu_edit_var"]
    if edit_var is not None:
        state["edit_mode"] = bool(edit_var.get())
    else:
        state["edit_mode"] = not state["edit_mode"]
    if not state["edit_mode"]:
        clear_selection_overlay(state)
    else:
        draw_selection_overlay(state)
    _sync_toolbar_visibility(state)


def build_menubar(root: tk.Tk, state: dict[str, Any]) -> None:
    menubar = tk.Menu(root)

    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="New Stack", underline=0, command=lambda: create_new_stack(state))
    file_menu.add_command(label="New Card", underline=0, command=lambda: create_new_card(state))
    file_menu.add_separator()
    file_menu.add_command(label="Save", underline=0, command=lambda: save_to_file(state))
    file_menu.add_command(label="Load", underline=0, command=lambda: load_from_file(state))
    file_menu.add_separator()
    file_menu.add_command(label="Export", underline=0, command=lambda: save_as_file(state))
    file_menu.add_command(label="Import", underline=0, command=lambda: load_from_dialog(state))
    file_menu.add_separator()
    file_menu.add_command(label="Quit", underline=0, command=lambda: state["root"].destroy())
    menubar.add_cascade(label="File", underline=0, menu=file_menu)

    go_menu = tk.Menu(menubar, tearoff=0)
    go_menu.add_command(label="Previous Card", underline=0, command=lambda: show_previous_card(state))
    go_menu.add_command(label="Next Card", underline=0, command=lambda: show_next_card(state))
    menubar.add_cascade(label="Go", underline=0, menu=go_menu)

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
    toolbar_window = tk.Toplevel(root)
    toolbar_window.title("Tools")
    toolbar_window.resizable(False, False)
    toolbar_window.transient(root)
    state["toolbar_window"] = toolbar_window

    def close_toolbar() -> None:
        state["edit_mode"] = False
        edit_var = state["menu_edit_var"]
        if edit_var is not None:
            edit_var.set(False)
        clear_selection_overlay(state)
        _sync_toolbar_visibility(state)

    toolbar_window.protocol("WM_DELETE_WINDOW", close_toolbar)
    toolbar_frame = tk.Frame(toolbar_window, bd=1, relief=tk.GROOVE)
    toolbar_frame.pack(fill=tk.BOTH, expand=True)

    buttons = [
        ("select", "Select"),
        ("label", "T"),
        ("button", "Button"),
        ("entry", "Entry"),
        ("text", "Text"),
    ]
    for tool_name, label in buttons:
        button = tk.Button(toolbar_frame, text=label, command=lambda t=tool_name: set_tool(state, t))
        button.pack(side=tk.LEFT, padx=4, pady=4)
        state["tool_buttons"][tool_name] = button
    state["tool_default_bg"] = state["tool_buttons"]["select"].cget("bg")


def build_canvas(root: tk.Tk, state: dict[str, Any]) -> None:
    canvas = tk.Canvas(root, bg="white", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.bind("<Button-1>", lambda event: handle_canvas_mouse_down(event, state))
    canvas.bind("<B1-Motion>", lambda event: handle_canvas_mouse_move(event, state))
    canvas.bind("<ButtonRelease-1>", lambda event: handle_canvas_mouse_up(event, state))
    canvas.bind("<Double-Button-1>", lambda event: handle_double_click(event, state))
    state["canvas"] = canvas


def init_app() -> None:
    root = tk.Tk()
    root.resizable(True, True)
    state = g
    state["root"] = root
    build_menubar(root, state)
    build_toolbar(root, state)
    build_canvas(root, state)
    root.bind_all("<Delete>", lambda event: on_delete_key(event, state))

    create_new_stack(state)
    load_from_file(state)
    _sync_tool_button_styles(state)
    _sync_toolbar_visibility(state)
    _update_window_title(state)
    root.mainloop()


def on_delete_key(event: tk.Event, state: dict[str, Any]) -> None:
    _ = event
    if state["edit_mode"]:
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
    else:
        object_id = find_object_at_position(state, x, y)
        if object_id is None:
            clear_selection(state)
        else:
            select_object(state, object_id)


def handle_canvas_mouse_down(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    x, y = _event_xy_on_canvas(state, event)
    if state["current_tool"] != "select":
        on_canvas_click(event, state)
        return
    handle = get_resize_handle_at_position(state, x, y)
    if handle is not None and state["selected_object_id"] is not None:
        start_resize(state, event, state["selected_object_id"], handle)
        return
    object_id = find_object_at_position(state, x, y)
    if object_id is None:
        clear_selection(state)
        return
    select_object(state, object_id)
    start_drag(state, event)


def handle_canvas_mouse_move(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    if state["resize"]["active"]:
        resize_move(state, event)
    elif state["drag"]["active"]:
        drag_move(state, event)


def handle_canvas_mouse_up(event: tk.Event, state: dict[str, Any]) -> None:
    if not state["edit_mode"]:
        return
    if state["resize"]["active"]:
        end_resize(state, event)
    if state["drag"]["active"]:
        end_drag(state, event)


def on_mouse_down(event: tk.Event, state: dict[str, Any]) -> None:
    handle_canvas_mouse_down(event, state)


def on_mouse_move(event: tk.Event, state: dict[str, Any]) -> None:
    handle_canvas_mouse_move(event, state)


def on_mouse_up(event: tk.Event, state: dict[str, Any]) -> None:
    handle_canvas_mouse_up(event, state)


def main() -> int:
    init_app()
    return 0
