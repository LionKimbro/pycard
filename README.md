# lions-pycard

`lions-pycard` is a Python HyperCard-like editor built with `tkinter`.

It provides a card-style canvas where you can place UI objects (`Label`, `Button`, `Entry`, `Text`), edit properties, save/load cards as JSON, and attach Python scripts to buttons.

## Features

- Visual card editor with select/move/create tools
- Object types: `label`, `button`, `entry`, `text`
- Property editor (double-click objects in edit mode)
- Per-button Python scripting (`on_click_code`)
- Script helpers in execution context:
  - `find_object_by_id(...)`
  - `find_object_by_name(...)`
  - `find_object_by_text(...)`
  - `get_text(...)`
  - `set_text(...)`
- Card persistence to `.pycard/cards.json`
- Window size persistence

## Repository

- https://github.com/LionKimbro/pycard

## Install

```bash
pip install lions-pycard
```

## Run

```bash
pycard
```

or:

```bash
python -m pycard
```

## Basic Use

1. Open `Window -> Edit Mode`.
2. Use the detached `Tools` window to choose an object type.
3. Click the card to create an object (auto-returns to `Select`).
4. Double-click an object to edit properties.
5. Use `File -> Save` to persist to `.pycard/cards.json`.
6. Turn off edit mode to run button scripts.

## Example Button Script

```python
target = find_object_by_name("status")
if target:
    set_text(target, "Clicked!")
print("status text:", get_text("status"))
```

## Development

Requirements:
- Python 3.10+

Commands:

```bash
python -m pytest -q
python -m py_compile src/pycard/app.py src/pycard/cli.py
```

## License

MIT
