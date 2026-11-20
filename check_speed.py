"""
Speed check: finds what limits the FPS (camera or model).

    uv run python check_speed.py

Close the Object Spotter app first (the camera can only be used by one program).
Takes about a minute. Paste the summary at the end back to Claude.
"""
import subprocess
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

from core import DEFAULT_MODEL_PATH
from core.camera import open_camera
from core.config import CAMERA_INDICES

RUNS = 40


def gpu_names():
    if not sys.platform.startswith("win"):
        return []
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }"],
            capture_output=True, text=True, timeout=20).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def time_model(providers, options=None):
    """Average milliseconds per frame for the model with these providers."""
    try:
        so = ort.SessionOptions()
        so.log_severity_level = 3
        provider_list = [(p, options) if options and p == "DmlExecutionProvider" else p
                         for p in providers]
        sess = ort.InferenceSession(str(DEFAULT_MODEL_PATH), so, providers=provider_list)
        inp = sess.get_inputs()[0]
        h = inp.shape[2] if isinstance(inp.shape[2], int) else 640
        w = inp.shape[3] if isinstance(inp.shape[3], int) else 640
        x = np.random.rand(1, 3, h, w).astype(np.float32)
        for _ in range(5):  # warm-up
            sess.run(None, {inp.name: x})
        t0 = time.perf_counter()
        for _ in range(RUNS):
            sess.run(None, {inp.name: x})
        ms = (time.perf_counter() - t0) / RUNS * 1000
        return ms, sess.get_providers()[0]
    except Exception as e:
        return None, f"failed: {str(e).splitlines()[0][:90]}"


def time_camera(index, resolution=None, frames=60):
    cap = open_camera(index, resolution)
    if not cap.isOpened():
        return None
    for _ in range(5):  # let exposure settle
        cap.read()
    ok_frames, t0 = 0, time.perf_counter()
    shape = None
    for _ in range(frames):
        ok, frame = cap.read()
        if ok and frame is not None:
            ok_frames += 1
            shape = frame.shape
    dt = time.perf_counter() - t0
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_txt = "".join(chr((fourcc >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00") or "?"
    cap.release()
    if not ok_frames:
        return None
    return {"fps": ok_frames / dt, "size": f"{shape[1]}x{shape[0]}", "fourcc": fourcc_txt}


def main():
    print("=" * 64)
    print("SPEED CHECK")
    print("=" * 64)
    print(f"onnxruntime {ort.__version__} | providers: {', '.join(ort.get_available_providers())}")
    gpus = gpu_names()
    print("graphics adapters:", " | ".join(gpus) if gpus else "(could not list)")
    print(f"model: {DEFAULT_MODEL_PATH.name}")

    print("\n-- model speed (lower is better) --")
    results = {}
    ms, used = time_model(["CPUExecutionProvider"])
    results["CPU"] = ms
    print(f"CPU                      : {ms:6.1f} ms/frame" if ms else f"CPU: {used}")
    if "DmlExecutionProvider" in ort.get_available_providers():
        ms, used = time_model(["DmlExecutionProvider", "CPUExecutionProvider"])
        results["DirectML default"] = ms
        print(f"DirectML default adapter : {ms:6.1f} ms/frame ({used})" if ms
              else f"DirectML default: {used}")
        for dev in range(3):
            ms, used = time_model(["DmlExecutionProvider", "CPUExecutionProvider"],
                                  {"device_id": str(dev)})
            if ms and used == "DmlExecutionProvider":
                results[f"DirectML device {dev}"] = ms
                print(f"DirectML device_id={dev}     : {ms:6.1f} ms/frame")
        ms, used = time_model(["DmlExecutionProvider", "CPUExecutionProvider"],
                              {"performance_preference": "high_performance"})
        if ms and used == "DmlExecutionProvider":
            results["DirectML high_performance"] = ms
            print(f"DirectML high_performance: {ms:6.1f} ms/frame")

    print("\n-- camera speed (higher is better) --")
    cams = {}
    for idx in CAMERA_INDICES:
        for label, res in (("default", None), ("1280x720", (1280, 720))):
            r = time_camera(idx, res)
            if r:
                cams[(idx, label)] = r
                print(f"camera {idx} {label:<9}: {r['fps']:5.1f} fps  ({r['size']}, {r['fourcc']})")
        if any(k[0] == idx for k in cams):
            break  # one working camera is enough

    print("\n" + "=" * 64)
    print("SUMMARY (paste this to Claude)")
    print("=" * 64)
    best = min(((k, v) for k, v in results.items() if v), key=lambda kv: kv[1], default=None)
    for k, v in results.items():
        if v:
            print(f"model {k}: {v:.1f} ms  (~{1000 / v:.0f} fps max)")
    for (idx, label), r in cams.items():
        print(f"camera {idx} {label}: {r['fps']:.1f} fps {r['size']} {r['fourcc']}")
    if best:
        print(f"fastest model setting: {best[0]}")
    print("=" * 64)


if __name__ == "__main__":
    main()
