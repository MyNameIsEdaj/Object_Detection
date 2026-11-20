"""
Real-Time Object Detection System - main entry point.

For now this launches the live webcam detector. When the GUI is added it will
start here instead.
"""
import sys

from detect_live import main as run_detector


def main():
    print("=" * 50)
    print("       REAL-TIME OBJECT DETECTION SYSTEM")
    print("=" * 50)
    return run_detector()


if __name__ == "__main__":
    sys.exit(main())
