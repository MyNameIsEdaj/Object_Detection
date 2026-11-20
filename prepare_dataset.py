"""
Merge many Roboflow YOLO exports into one balanced 5-class dataset for Colab.

Classes (index = YOLO class id):
    0: can   1: glasses   2: marker   3: watch   4: water bottle

- Each source zip's own class ids are remapped to ours with "mapping".
- Hard-negative zips (hands, classrooms, desks...) get empty label files so the
  model learns that those scenes contain none of the 5 objects.
- Output: datasets/combined_5_objects/ (train/valid + data.yaml) and a
  ready-to-upload datasets/combined_5_objects_dataset.zip.

Upload the zip to Colab and unzip it to /content/dataset (that is the "path"
written in data.yaml).

To add a source, add an entry to DATASET_SOURCES. The script prints each zip's
own class names next to your mapping so you can check the numbers line up.
"""
import random
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import PurePosixPath

import cv2
import numpy as np

from core import DATASETS_DIR, RAW_ZIPS_DIR

CLASS_NAMES = ["can", "glasses", "marker", "watch", "water bottle"]

OUTPUT_DIR = DATASETS_DIR / "combined_5_objects"
ZIP_OUTPUT_PATH = DATASETS_DIR / "combined_5_objects_dataset.zip"
COLAB_DATASET_PATH = "/content/dataset"
SEED = 42
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# category = sub-folder of datasets/raw_zips ("" = directly in raw_zips)
# mapping  = {source_class_id: our_class_id}; source classes not listed are dropped
# max_train / max_valid = how many images to sample from that zip
# is_negative = True -> every image gets an empty label (background only)
# blur_copies = N    -> also add N motion-blurred copies of each TRAIN image
#                       (same labels). Use it on your own webcam photos so the
#                       model learns what moving objects look like.
DATASET_SOURCES = [
    # --- CLASS 0: CAN ---
    {
        "category": "cans",
        "file": "SODA CAN.v2i.yolov8.zip",
        "mapping": {0: 0},
        "max_train": 220,
        "max_valid": 40,
    },
    {
        "category": "cans",
        "file": "Ph Canned Goods.v2i.yolov8.zip",
        "mapping": {0: 0, 1: 0, 2: 0},
        "max_train": 70,
        "max_valid": 16,
    },
    {
        "category": "cans",
        "file": "Cans_beverage.v1i.yolov8.zip",
        "mapping": {0: 0},
        "max_train": 80,
        "max_valid": 20,
    },

    # --- CLASS 1: GLASSES ---
    {
        "category": "glasses",
        "file": "eyeglasses.v2i.yolov8.zip",
        "mapping": {0: 1},
        "max_train": 180,
        "max_valid": 35,
    },
    {
        "category": "glasses",
        "file": "SPECTACLES.v1i.yolov8.zip",
        "mapping": {0: 1},
        "max_train": 90,
        "max_valid": 15,
    },
    {
        "category": "glasses",
        "file": "glasses.v4i.yolov8.zip",
        "mapping": {0: 1, 1: 1},
        "max_train": 50,
        "max_valid": 14,
    },

    # --- CLASS 2: MARKER ---
    {
        "category": "marker",
        "file": "Camlin Whiteboard Marker.v2i.yolov8.zip",
        "mapping": {0: 2, 1: 2},
        "max_train": 100,
        "max_valid": 25,
    },
    {
        "category": "marker",
        "file": "Marker colors.v1i.yolov8.zip",
        "mapping": {0: 2, 1: 2},
        "max_train": 120,
        "max_valid": 30,
    },
    {
        "category": "marker",
        "file": "Marker.v1i.yolov8.zip",
        "mapping": {0: 2},
        "max_train": 90,
        "max_valid": 20,
    },

    # --- CLASS 3: WATCH ---
    {
        "category": "watch",
        "file": "smartwatch.v1i.yolov8.zip",
        "mapping": {0: 3},
        "max_train": 150,  # mostly product shots on white backgrounds
        "max_valid": 30,
    },
    # test-apple-watch.v1i removed: 62 of 91 images have overlapping boxes and 30
    # have a box covering over half the picture (bad labels).
    {
        "category": "watch",
        "file": "Wristwatch.v3i.yolov8.zip",
        "mapping": {0: 3},
        "max_train": 350,  # real watches in hands / on surfaces: closest to our webcam
        "max_valid": 60,
    },

    # --- CLASS 4: WATER BOTTLE ---
    {
        "category": "water_bottle",
        "file": "Bottle Water.v4i.yolov8.zip",
        "mapping": {0: 4},
        "max_train": 110,
        "max_valid": 25,
    },
    {
        "category": "water_bottle",
        "file": "water bottle.v1i.yolov8.zip",
        "mapping": {3: 4},
        "max_train": 200,
        "max_valid": 40,
    },

    # --- USER'S WEBCAM CUSTOM PHOTOS ---
    # Labelled webcam photos from custom_photo.v1i (your Roboflow labels + checked
    # auto-labels), already split 80/20. Replaces custom_photo.v1i, where 265 of 330
    # photos had no labels yet.
    {
        "category": "",
        "file": "own_webcam_photos.zip",
        "mapping": {0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
        "blur_copies": 3,
        "max_train": 1000,
        "max_valid": 1000,
    },
    {
        "category": "",
        "file": "CUSTOM2.v1i.yolov8.zip",
        "mapping": {0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
        "blur_copies": 2,
        "max_train": 100,
        "max_valid": 30,
    },

    # --- HARD NEGATIVES (BACKGROUND & EMPTY HANDS) ---
    # 1. Classroom Backgrounds
    {
        "category": "negative",
        "file": "classroom.v1i.yolov8.zip",
        "mapping": {},
        "max_train": 40,
        "max_valid": 10,
        "is_negative": True
    },
    # 2. Desks, Monitors & Keyboards
    {
        "category": "negative",
        "file": "Computer.v1i.yolov8.zip",
        "mapping": {},
        "max_train": 30,
        "max_valid": 4,
        "is_negative": True
    },
    # 3. Empty Hands (Crucial for stopping hands from triggering Marker)
    {
        "category": "negative",
        "file": "Hand Gesture.v1i.yolov8.zip",
        "mapping": {},
        "max_train": 100,
        "max_valid": 25,
        "is_negative": True
    },
    # 4. Lab Surfaces & Backgrounds
    {
        "category": "negative",
        "file": "Laboratory.v8i.yolov8.zip",
        "mapping": {},
        "max_train": 40,
        "max_valid": 10,
        "is_negative": True
    },
]

# ---------------------------------------------------------------- helpers
def split_of(path):
    """'train', 'valid' or None, based on the folder names in the zip path.

    The old check ("val" in path) matched words anywhere in the file name,
    e.g. "oval_marker.jpg" or "interval", which could put the same image in
    both train and valid.
    """
    dirs = {p.lower() for p in PurePosixPath(path).parts[:-1]}
    if "train" in dirs:
        return "train"
    if dirs & {"valid", "val", "test"}:
        return "valid"
    return None


def label_path_for(image_path):
    """train/images/x.jpg -> train/labels/x.txt (also works with no split folder)."""
    parts = list(PurePosixPath(image_path).parts)
    for i in range(len(parts) - 2, -1, -1):
        if parts[i] == "images":
            parts[i] = "labels"
            break
    return str(PurePosixPath(*parts).with_suffix(".txt"))


def read_source_class_names(z):
    """Best-effort read of names: [...] from the zip's data.yaml (for display only)."""
    for name in z.namelist():
        if PurePosixPath(name).name == "data.yaml":
            for line in z.read(name).decode("utf-8", errors="ignore").splitlines():
                if line.strip().startswith("names:"):
                    return line.split(":", 1)[1].strip()
    return "?"


def motion_blur(img_bytes, rng):
    """Return a JPEG of the image with random-direction motion blur, or None."""
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    length = rng.randint(9, 25)  # blur streak length in pixels
    kernel = np.zeros((length, length), np.float32)
    kernel[length // 2, :] = 1.0
    centre = ((length - 1) / 2, (length - 1) / 2)
    rot = cv2.getRotationMatrix2D(centre, rng.uniform(0, 180), 1.0)
    kernel = cv2.warpAffine(kernel, rot, (length, length))
    kernel /= max(kernel.sum(), 1e-6)
    ok, buf = cv2.imencode(".jpg", cv2.filter2D(img, -1, kernel),
                           [cv2.IMWRITE_JPEG_QUALITY, 92])
    return buf.tobytes() if ok else None


def remap_labels(text, mapping):
    """Return (lines, class_ids) with class ids remapped; unmapped classes dropped."""
    lines, ids = [], []
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) < 5:
            continue
        try:
            src_cls = int(float(parts[0]))
        except ValueError:
            continue
        if src_cls not in mapping:
            continue
        coords = parts[1:]
        if len(coords) > 4:
            # Polygon (x1 y1 x2 y2 ...) -> bounding box. Mixing polygons and boxes in
            # one file makes Ultralytics misread the boxes, so always write boxes.
            try:
                xs = [float(v) for v in coords[0::2]]
                ys = [float(v) for v in coords[1::2]]
            except ValueError:
                continue
            x1, x2 = max(0.0, min(xs)), min(1.0, max(xs))
            y1, y2 = max(0.0, min(ys)), min(1.0, max(ys))
            if x2 <= x1 or y2 <= y1:
                continue
            coords = [f"{(x1 + x2) / 2:.6f}", f"{(y1 + y2) / 2:.6f}",
                      f"{x2 - x1:.6f}", f"{y2 - y1:.6f}"]
        new_cls = mapping[src_cls]
        lines.append(" ".join([str(new_cls)] + coords))
        ids.append(new_cls)
    return lines, ids


def process_source(cfg, rng, dirs, instance_stats, image_stats, negative_stats):
    zip_path = RAW_ZIPS_DIR / cfg["category"] / cfg["file"] if cfg["category"] \
        else RAW_ZIPS_DIR / cfg["file"]
    if not zip_path.exists():
        print(f"[!] Zip not found, skipping: {zip_path}")
        return

    is_negative = cfg.get("is_negative", False)
    prefix = cfg["file"].split(".")[0].replace(" ", "_")

    with zipfile.ZipFile(zip_path) as z:
        names = list(dict.fromkeys(z.namelist()))  # de-duplicate entries
        name_set = set(names)
        images = sorted(n for n in names
                        if PurePosixPath(n).suffix.lower() in IMAGE_EXTS
                        and not n.startswith("__MACOSX"))

        mapping_txt = "negative (empty labels)" if is_negative else cfg["mapping"]
        print(f"\n{cfg['file']}")
        print(f"  source classes: {read_source_class_names(z)}")
        print(f"  mapping       : {mapping_txt}")

        by_split = {"train": [], "valid": []}
        unsplit = []
        for img in images:
            s = split_of(img)
            (by_split[s] if s else unsplit).append(img)
        if unsplit:  # no train/valid folders: make an 80/20 split ourselves
            rng.shuffle(unsplit)
            cut = int(len(unsplit) * 0.8)
            by_split["train"] += unsplit[:cut]
            by_split["valid"] += unsplit[cut:]

        skipped_no_label = skipped_unmapped = blurred_count = 0
        for split, limit in (("train", cfg["max_train"]), ("valid", cfg["max_valid"])):
            candidates = by_split[split][:]
            rng.shuffle(candidates)  # random sample, not just the first N in the zip
            taken = 0
            for img in candidates:
                if taken >= limit:
                    break

                if is_negative:
                    label_lines, ids = [], []
                else:
                    lbl = label_path_for(img)
                    if lbl not in name_set:
                        # The old script wrote an EMPTY label here, silently teaching
                        # the model that a photo of an object is background.
                        skipped_no_label += 1
                        continue
                    text = z.read(lbl).decode("utf-8", errors="ignore")
                    label_lines, ids = remap_labels(text, cfg["mapping"])
                    if not label_lines:
                        # Only contains classes we don't use - it may still show one
                        # of our objects unlabelled, so don't use it as a negative.
                        skipped_unmapped += 1
                        continue

                # Unique name: source prefix + split + running number + original name
                stem = PurePosixPath(img).stem.replace(" ", "_")
                ext = PurePosixPath(img).suffix.lower()
                out_name = f"{prefix}_{split}_{taken:04d}_{stem}"[:180]
                img_bytes = z.read(img)
                label_txt = "\n".join(label_lines) + ("\n" if label_lines else "")
                outputs = [(out_name, ext, img_bytes)]
                if split == "train":  # never blur validation: it must stay realistic
                    for k in range(cfg.get("blur_copies", 0)):
                        blurred = motion_blur(img_bytes, rng)
                        if blurred:
                            outputs.append((f"{out_name}_blur{k}", ".jpg", blurred))
                            blurred_count += 1

                for name, suffix, data in outputs:
                    (dirs[split]["images"] / f"{name}{suffix}").write_bytes(data)
                    (dirs[split]["labels"] / f"{name}.txt").write_text(label_txt)
                    if is_negative:
                        negative_stats[split] += 1
                    else:
                        for cid, n in Counter(ids).items():
                            instance_stats[CLASS_NAMES[cid]][split] += n
                        for cid in set(ids):
                            image_stats[CLASS_NAMES[cid]][split] += 1
                taken += 1

            print(f"  {split:<5}: took {taken} / {len(by_split[split])} available (max {limit})")

        if blurred_count:
            print(f"  [+] added {blurred_count} motion-blurred training copies")
        if skipped_no_label:
            print(f"  [!] skipped {skipped_no_label} images with no label file")
        if skipped_unmapped:
            print(f"  [i] skipped {skipped_unmapped} images whose labels were all unmapped classes")


def write_data_yaml():
    names = ", ".join(f"'{n}'" for n in CLASS_NAMES)
    (OUTPUT_DIR / "data.yaml").write_text(
        f"path: {COLAB_DATASET_PATH}\n"
        "train: train/images\n"
        "val: valid/images\n"
        "\n"
        f"nc: {len(CLASS_NAMES)}\n"
        f"names: [{names}]\n"
    )


def zip_output():
    if ZIP_OUTPUT_PATH.exists():
        ZIP_OUTPUT_PATH.unlink()
    with zipfile.ZipFile(ZIP_OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as zout:
        for f in sorted(OUTPUT_DIR.rglob("*")):
            if f.is_file():
                zout.write(f, f.relative_to(OUTPUT_DIR).as_posix())


def main():
    print("=" * 65)
    print("   PREPARING 5-CLASS DATASET + NEGATIVE SAMPLES")
    print("=" * 65)

    for src in DATASET_SOURCES:
        for cid in src["mapping"].values():
            if not 0 <= cid < len(CLASS_NAMES):
                raise ValueError(f"{src['file']}: mapping target {cid} is not a valid class id")

    if OUTPUT_DIR.exists():
        print(f"Clearing old {OUTPUT_DIR.name} folder...")
        shutil.rmtree(OUTPUT_DIR)
    dirs = {s: {"images": OUTPUT_DIR / s / "images", "labels": OUTPUT_DIR / s / "labels"}
            for s in ("train", "valid")}
    for d in dirs.values():
        d["images"].mkdir(parents=True, exist_ok=True)
        d["labels"].mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)  # same seed -> same dataset every run
    instance_stats = defaultdict(lambda: {"train": 0, "valid": 0})
    image_stats = defaultdict(lambda: {"train": 0, "valid": 0})
    negative_stats = {"train": 0, "valid": 0}

    for cfg in DATASET_SOURCES:
        try:
            process_source(cfg, rng, dirs, instance_stats, image_stats, negative_stats)
        except zipfile.BadZipFile as e:
            print(f"[!] {cfg['file']} is not a valid zip: {e}")

    write_data_yaml()

    print("\n" + "=" * 65)
    print("DATASET MERGE SUMMARY            images (boxes)")
    print("=" * 65)
    for c in CLASS_NAMES:
        i, b = image_stats[c], instance_stats[c]
        print(f"  {c:<15}: train {i['train']:>4} ({b['train']:>4})   "
              f"valid {i['valid']:>4} ({b['valid']:>4})")
    print(f"  {'[negatives]':<15}: train {negative_stats['train']:>4}          "
          f"valid {negative_stats['valid']:>4}")
    print("-" * 65)
    n_train = sum(1 for _ in dirs["train"]["images"].iterdir())
    n_valid = sum(1 for _ in dirs["valid"]["images"].iterdir())
    print(f"Total images: train {n_train}, valid {n_valid}, combined {n_train + n_valid}")

    print(f"\nCompressing into {ZIP_OUTPUT_PATH.name}...")
    zip_output()
    size_mb = ZIP_OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Done: {ZIP_OUTPUT_PATH} ({size_mb:.1f} MB)")
    print("=" * 65)


if __name__ == "__main__":
    main()
