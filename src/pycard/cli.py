"""CLI bootstrap for pycard using lionscliapp."""

from __future__ import annotations

import lionscliapp as app

from . import app as stage1


def cmd_run() -> None:
    stage1.init_app()


def main() -> int:
    app.declare_app("pycard", "0.1.0")
    app.describe_app("PyCard launcher")
    app.declare_projectdir(".pycard")

    app.declare_cmd("", cmd_run)
    app.declare_cmd("run", cmd_run)
    app.describe_cmd("run", "Launch the stage 1 editor")

    app.main()
    return 0
