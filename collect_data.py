import cv2
import os
import time

def main():
    output_dir = os.path.join(os.path.dirname(__file__), "dataset", "raw_images")
    os.makedirs(output_dir, exist_ok=True)

    # Count existing images to avoid overwriting
    existing = [f for f in os.listdir(output_dir) if f.lower().endswith(('.jpg', '.png'))]
    count = len(existing)

    # Try DirectShow first on Windows for instant response, then default backend
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Error: Could not access the webcam. Check if another app is using it or check Windows Camera Privacy Settings.")
        return

    print("=" * 50)
    print("      OBJECT DETECTION - DATASET COLLECTOR")
    print("=" * 50)
    print(f"Target Directory: {output_dir}")
    print(f"Currently saved images: {count}")
    print("\nControls:")
    print("  [SPACEBAR] : Capture a single photo")
    print("  [A]        : Toggle Auto-Capture mode (captures every 0.8s)")
    print("  [Q] or [ESC] : Quit")
    print("=" * 50)

    auto_capture = False
    last_auto_time = 0
    auto_interval = 0.8  # seconds

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        display_frame = frame.copy()
        now = time.time()

        # Handle auto-capture
        if auto_capture and (now - last_auto_time >= auto_interval):
            count += 1
            filename = f"img_{count:04d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            last_auto_time = now
            print(f"Auto-saved: {filename} (Total: {count})")

        # Overlay HUD on display
        status_text = "AUTO: ON" if auto_capture else "AUTO: OFF"
        status_color = (0, 255, 0) if auto_capture else (0, 0, 255)

        cv2.putText(display_frame, f"Captured: {count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(display_frame, f"[{status_text}] (Press 'A' to toggle)", (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(display_frame, "SPACE: Capture | Q: Quit", (20, display_frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("Data Collector - Hold Marker in Camera", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # Q or ESC
            break
        elif key == 32:  # SPACEBAR
            count += 1
            filename = f"img_{count:04d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            print(f"Saved: {filename} (Total: {count})")
        elif key == ord('a') or key == ord('A'):
            auto_capture = not auto_capture
            last_auto_time = now
            print(f"Auto-capture is now: {'ENABLED' if auto_capture else 'DISABLED'}")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nDone! Total images collected: {count}")
    print(f"Saved in: {output_dir}")

if __name__ == "__main__":
    main()
