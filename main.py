"""Entry point:  python main.py"""
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "journal.json"


def main() -> int:
    logging.basicConfig(filename=BASE_DIR / "journal.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        from journal.gui import JournalApp  # imported late so a missing Tk gives a clear message
    except ImportError as exc:
        print(f"Missing dependency: {exc}\nInstall with: pip install -r requirements.txt "
              "(Tkinter ships with Python; on Linux: sudo apt install python3-tk)")
        return 1
    JournalApp(DATA_FILE).mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
