"""
Multi-Class Dataset Preparation & Merger Script (Updated Batch)
Merges marker, wristwatch, cans (beverage + food cans), water bottle, and eyeglasses
into a clean, balanced 5-class YOLO dataset.
"""
import zipfile
import os
import shutil


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_zips_dir = os.path.join(base_dir, "datasets", "raw_zips")
    output_dir = os.path.join(base_dir, "datasets", "combined_5_objects")

    # Target class definitions
    # 0: marker
    # 1: watch
    # 2: can
    # 3: water bottle
    # 4: eye glasses
    class_names = [
        "marker",
        "watch",
        "can",
        "water bottle",
        "eye glasses"
    ]

    splits = {
        "train": {
            "images": os.path.join(output_dir, "train", "images"),
            "labels": os.path.join(output_dir, "train", "labels"),
        },
        "valid": {
            "images": os.path.join(output_dir, "valid", "images"),
            "labels": os.path.join(output_dir, "valid", "labels"),
        }
    }

    # Reset output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for s in splits.values():
        os.makedirs(s["images"], exist_ok=True)
        os.makedirs(s["labels"], exist_ok=True)

    dataset_configs = [
        {
            "name": "marker",
            "files": [
                ("Marker.v1i.yolov8.zip", {0: 0}),
                (".marker.v1i.yolov8.zip", {0: 0}),
            ],
            "max_train": 350,
            "max_valid": 80,
        },
        {
            "name": "watch",
            "files": [
                ("Wristwatch.v3i.yolov8.zip", {0: 1}),
                ("Watch.v1-watch.yolov8.zip", {0: 1}),
            ],
            "max_train": 350,
            "max_valid": 80,
        },
        {
            "name": "can",
            "files": [
                # Clean beverage cans (upright soda cans on tables & in hands)
                ("Cans_beverage.v1i.yolov8.zip", {0: 2}),
                # A balanced sample of food cans (Argentina, Mega Green, Mega Red)
                ("Ph Canned Goods.v2i.yolov8.zip", {0: 2, 1: 2, 2: 2}),
            ],
            "max_train": 230,
            "max_valid": 50,
        },
        {
            "name": "water_bottle",
            "files": [
                # In water bottle: class 3 is waterbottle
                ("water bottle.v1i.yolov8.zip", {3: 3}),
            ],
            "max_train": 350,
            "max_valid": 80,
        },
        {
            "name": "eye_glasses",
            "files": [
                # New clean eyeglasses dataset
                ("eyeglasses.v2i.yolov8.zip", {0: 4}),
                # Old glasses (0: goggles, 2: spec)
                ("Eye glasses.v1i.yolov8.zip", {0: 4, 2: 4}),
            ],
            "max_train": 350,
            "max_valid": 80,
        },
    ]

    stats = {cls_name: {"train": 0, "valid": 0} for cls_name in class_names}

    print("=" * 65)
    print("      MERGING 5 UPDATED DATASETS INTO UNIFIED YOLO FORMAT")
    print("=" * 65)
    print("Target Classes:")
    for idx, name in enumerate(class_names):
        print(f"  [{idx}] {name}")
    print("-" * 65)

    for cfg in dataset_configs:
        dataset_name = cfg["name"]
        max_train = cfg["max_train"]
        max_valid = cfg["max_valid"]

        counts = {"train": 0, "valid": 0}
        limits = {"train": max_train, "valid": max_valid}

        print(f"\nProcessing category: [{dataset_name.upper()}]...")

        for zip_name, class_map in cfg["files"]:
            zip_path = os.path.join(raw_zips_dir, zip_name)
            if not os.path.exists(zip_path):
                print(f"  Warning: File not found: {zip_path}")
                continue

            with zipfile.ZipFile(zip_path, 'r') as z:
                label_files = [f for f in z.namelist() if f.endswith('.txt') and not os.path.basename(f).startswith('README')]

                for lbl_file in label_files:
                    filename_clean = lbl_file.replace('\\', '/')
                    parts = filename_clean.split('/')

                    split_type = None
                    if 'train' in parts:
                        split_type = 'train'
                    elif 'valid' in parts or 'test' in parts:
                        split_type = 'valid'

                    if not split_type or counts[split_type] >= limits[split_type]:
                        continue

                    content = z.read(lbl_file).decode('utf-8').strip().splitlines()
                    remapped_lines = []

                    for line in content:
                        tokens = line.strip().split()
                        if not tokens:
                            continue
                        try:
                            orig_cls = int(tokens[0])
                        except ValueError:
                            continue

                        if orig_cls in class_map:
                            target_cls = class_map[orig_cls]
                            remapped_line = f"{target_cls} " + " ".join(tokens[1:])
                            remapped_lines.append(remapped_line)
                            stats[class_names[target_cls]][split_type] += 1

                    if not remapped_lines:
                        continue

                    prefix = f"{dataset_name}_{counts[split_type]:04d}"

                    img_candidates = [
                        lbl_file.replace('/labels/', '/images/').replace('.txt', ext)
                        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']
                    ]
                    found_img = None
                    for candidate in img_candidates:
                        if candidate in z.namelist():
                            found_img = candidate
                            break

                    if not found_img:
                        continue

                    img_ext = os.path.splitext(found_img)[1]
                    out_img_name = f"{prefix}{img_ext}"
                    out_lbl_name = f"{prefix}.txt"

                    out_lbl_path = os.path.join(splits[split_type]["labels"], out_lbl_name)
                    with open(out_lbl_path, "w", encoding="utf-8") as lf:
                        lf.write("\n".join(remapped_lines) + "\n")

                    out_img_path = os.path.join(splits[split_type]["images"], out_img_name)
                    with z.open(found_img) as src, open(out_img_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                    counts[split_type] += 1

        print(f"  Extracted for [{dataset_name}]: {counts['train']} train, {counts['valid']} valid")

    # Write data.yaml for Google Colab
    yaml_content = f"""# 5-Object Detection Dataset Configuration (Updated)
path: /content/dataset
train: train/images
val: valid/images

# Number of classes
nc: 5

# Class names
names:
  0: marker
  1: watch
  2: can
  3: water bottle
  4: eye glasses
"""
    yaml_path = os.path.join(output_dir, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print("\n" + "=" * 65)
    print("      FINAL DATASET SUMMARY (5 CLASSES - UPDATED)")
    print("=" * 65)
    total_train = 0
    total_valid = 0
    for idx, name in enumerate(class_names):
        tr = stats[name]['train']
        val = stats[name]['valid']
        total_train += tr
        total_valid += val
        print(f"  Class {idx} [{name:<12}]: {tr:>4} train annotations | {val:>3} valid annotations")
    print("-" * 65)
    print(f"  TOTAL ANNOTATIONS  : {total_train} train | {total_valid} valid")
    print(f"  Blueprint YAML     : {yaml_path}")
    print("=" * 65)

    # Package into a single zip file for Google Colab
    zip_output_path = os.path.join(base_dir, "datasets", "5_objects_dataset")
    print("\nCompressing into single zip for Google Colab...")
    shutil.make_archive(zip_output_path, 'zip', output_dir)
    final_zip = zip_output_path + ".zip"
    size_mb = os.path.getsize(final_zip) / (1024 * 1024)
    print(f"SUCCESS! Created: {final_zip} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
