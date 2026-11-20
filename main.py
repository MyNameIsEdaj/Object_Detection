"""
Object Spotter - main entry point.

  uv run python main.py           # comic-style GUI
  uv run python main.py --cli     # plain OpenCV window (detect_live.py)
  uv run python main.py --theme candy   # or comic (the app remembers your last choice)
  uv run python main.py --model models\\backups\\5_objects_detector_v2_backup.onnx
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Object Spotter")
    parser.add_argument("--cli", action="store_true", help="use the plain OpenCV window")
    parser.add_argument("--model", help="path to an .onnx model")
    parser.add_argument("--theme", choices=["comic", "candy"], help="GUI theme")
    args, rest = parser.parse_known_args()

    if args.cli:
        from detect_live import main as run_cli
        return run_cli((["--model", args.model] if args.model else []) + rest)

    from gui.app import run
    return run(args.model, args.theme)


if __name__ == "__main__":
    sys.exit(main())
