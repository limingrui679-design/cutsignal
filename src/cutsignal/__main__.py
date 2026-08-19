"""Allow ``python -m cutsignal`` to behave like the installed command."""

from cutsignal.cli import app

if __name__ == "__main__":
    app()
