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
    run_button = next(button for button in app.button if button.label == "Run synthetic demo")
    run_button.click()
    app.run(timeout=90)
    assert not app.exception, [item.value for item in app.exception]
    assert app.tabs and {tab.label for tab in app.tabs} >= {
        "Overview",
        "Fat-loss signal",
        "Strength",
        "Food plan",
        "Data & privacy",
    }
    assert any(item.value == "Evidence-gated result" for item in app.subheader)
    app.radio[0].set_value("Casebook")
    app.run(timeout=20)
    assert not app.exception, [item.value for item in app.exception]
    case_button = next(button for button in app.button if button.label == "Run selected case")
    case_button.click()
    app.run(timeout=45)
    assert not app.exception, [item.value for item in app.exception]
    assert any(item.value == "All stated assertions passed." for item in app.success)
    print("Streamlit application startup: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
