"""pycard package."""

from .app import g, init_app

__all__ = ["g", "init_app", "main"]

def main() -> int:
    """Run the stage 1 editor directly."""
    init_app()
    return 0
