"""
Multi-Class Dataset Preparation & Merger Script
Merges 5 individual datasets (marker, watch, can, water bottle, eye glasses)
into a unified YOLO training dataset with proper class remapping.
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

    # Reset output directory for clean build
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for s in splits.values():
        os.makedirs(s["images"], exist_ok=True)
        os.makedirs(s["labels"], exist_ok=True)

    # Configuration for each raw dataset:
    # (zip_filename, class_mapping_dict, max_train_samples, max_valid_samples)
    dataset_configs = [
        {
            "name": "marker",
            "files": ["Marker.v1i.yolov8.zip", ".marker.v1i.yolov8.zip"],
            # Original class 0 -> Target class 0
            "class_map": {0: 0},
            "max_train": 300,
            "max_valid": 60,
        },
        {
            "name": "watch",
            "files": ["Watch.v1-watch.yolov8.zip"],
            # Original class 0 -> Target class 1
            "class_map": {0: 1},
            "max_train": 250,
            "max_valid": 60,
        },
        {
            "name": "can",
            "files": ["Cans.v1i.yolov8.zip"],
            # Original class 0 ('metal-can') -> Target class 2
            "class_map": {0: 2},
            "max_train": 250,
            "max_valid": 60,
        },
        {
            "name": "water_bottle",
            "files": ["water bottle.v1i.yolov8.zip"],
            # In water bottle dataset: 0: leaf, 1: paper, 2: water, 3: waterbottle
            # We only map class 3 -> Target class 3 ('water bottle')
            "class_map": {3: 3},
            "max_train": 250,
            "max_valid": 60,
        },
        {
            "name": "eye_glasses",
            "files": ["Eye glasses.v1i.yolov8.zip"],
            # In eye glasses dataset: 0: goggles, 1: no_goggles, 2: spec
            # Map 0 and 2 -> Target class 4 ('eye glasses')
            "class_map": {0: 4, 2: 4},
            "max_train": 250,
            "max_valid": 60,
        },
    ]

    stats = {cls_name: {"train": 0, "valid": 0} for cls_name in class_names}

    print("=" * 65)
    print("      MERGING 5 DATASETS INTO UNIFIED YOLO FORMAT")
    print("=" * 65)
    print("Target Classes:")
    for idx, name in enumerate(class_names):
        print(f"  [{idx}] {name}")
    print("-" * 65)

    for cfg in dataset_configs:
        dataset_name = cfg["name"]
        class_map = cfg["class_map"]
        max_train = cfg["max_train"]
        max_valid = cfg["max_valid"]

        counts = {"train": 0, "valid": 0}
        limits = {"train": max_train, "valid": max_valid}

        print(f"\nProcessing object category: [{dataset_name.upper()}]...")

        for zip_name in cfg["files"]:
            zip_path = os.path.join(raw_zips_dir, zip_name)
            if not os.path.exists(zip_path):
                print(f"  Warning: File not found: {zip_path}")
                continue

            with zipfile.ZipFile(zip_path, 'r') as z:
                # Find all label files
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

                    # Read label lines and check if any class matches our class_map
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

                    # Only save image & label if at least one valid object was found
                    if not remapped_lines:
                        continue

                    base_no_ext = os.path.splitext(os.path.basename(lbl_file))[0]
                    prefix = f"{dataset_name}_{counts[split_type]:04d}"

                    # Find corresponding image in zip
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

                    # Write remapped label file
                    out_lbl_path = os.path.join(splits[split_type]["labels"], out_lbl_name)
                    with open(out_lbl_path, "w", encoding="utf-8") as lf:
                        lf.write("\n".join(remapped_lines) + "\n")

                    # Copy image file
                    out_img_path = os.path.join(splits[split_type]["images"], out_img_name)
                    with z.open(found_img) as src, open(out_img_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                    counts[split_type] += 1

        print(f"  Extracted for [{dataset_name}]: {counts['train']} train, {counts['valid']} valid")

    # Create the unified data.yaml
    yaml_content = f"""# 5-Object Detection Dataset Configuration
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
    print("      FINAL DATASET SUMMARY (5 CLASSES)")
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
