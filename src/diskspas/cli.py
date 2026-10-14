"""Запуск программы: открывает окно в браузере. Вся работа происходит в окне."""
import argparse
import sys

from . import __version__
from .launcher import run_ui


def main(argv=None):
    p = argparse.ArgumentParser(prog="diskspas", description="ДискСпас: скачивание файлов с Яндекс Диска.")
    p.add_argument("--port", type=int, default=8765, help="порт окна на этом компьютере (по умолчанию 8765)")
    p.add_argument("--no-browser", action="store_true", help="не открывать браузер автоматически")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)
    return run_ui(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    sys.exit(main())
