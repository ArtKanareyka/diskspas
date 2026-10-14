"""PyInstaller entry point (keeps package-relative imports working in a frozen build)."""
import os
import sys

# windowed builds have no console: make print() harmless
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from diskspas.cli import main

if __name__ == "__main__":
    sys.exit(main())
