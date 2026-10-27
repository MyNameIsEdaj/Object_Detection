"""
Real-Time Object Detection System
Main Entry Point
"""
import sys
from detect_live import main as run_detector


def main():
    print("==================================================")
    print("       REAL-TIME OBJECT DETECTION SYSTEM          ")
    print("==================================================")
    run_detector()


if __name__ == "__main__":
    main()
