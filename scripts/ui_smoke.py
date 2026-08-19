#!/usr/bin/env python3
"""Start the Streamlit script in its test runtime without opening a browser."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "src" / "cutsignal" / "app.py"), default_timeout=20).run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.title and app.title[0].value == "CutSignal"
    assert app.warning
    print("Streamlit application startup: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
