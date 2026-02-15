#!/usr/bin/env python3
"""
Generate the final data.csv with correct surah/verse mapping and normalized coordinates.

This is the main script that produces the data.csv used by the Quran app.
It combines:
1. OpenCV template matching to detect aya marker positions in page images
2. Authoritative page-verse mapping from the mushaf-layout dataset
3. HoughCircles fallback for pages where template matching fails
4. Coordinate normalization (0.0-1.0) for screen-size independence

Output: data.csv with columns: surah_number, verse_number, page, x, y
  - x, y are normalized (0.0-1.0) center coordinates of each aya marker
  - App usage: display_x = x * displayWidth, display_y = y * displayHeight

Prerequisites:
  pip install opencv-python numpy

Usage:
  1. Place Quran page images (1.jpg - 604.jpg) in a sibling folder called 'hafs-tajweed/'
  2. Place template_1.jpg and template_2.jpg in the same folder as this script
  3. Create an 'images/' folder with zero-padded symlinks (001.jpg - 604.jpg)
  4. Place page_verses.json (authoritative mapping) in the same folder
  5. Run: python3 generate_data.py
"""
import json
import csv
import cv2
import numpy as np
import os
import sys


def group_and_sort(points, group_y_threshold):
    """Group points by y-coordinate rows, then sort right-to-left within each row."""
    groups, current_group = [], []
    for point in sorted(points, key=lambda p: p[1]):
        if not current_group or abs(point[1] - current_group[0][1]) <= group_y_threshold:
            current_group.append(point)
        else:
            groups.append(current_group)
            current_group = [point]
    groups.append(current_group)
    for group in groups:
        group.sort(key=lambda p: -p[0])
    return [point for group in groups for point in group]


def detect_ayas_template(page_num, threshold, images_folder, template_1, template_2):
    """Detect aya markers using OpenCV template matching."""
    template = template_1 if page_num <= 2 else template_2
    th, tw = template.shape[:2]
    img = cv2.imread(os.path.join(images_folder, f"{page_num:03}.jpg"))
    if img is None:
        return []
    result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    locations = list(zip(*np.where(result >= threshold)[::-1]))
    min_dist = max(th, tw)
    distinct = []
    for l1 in locations:
        if all(np.sqrt((l1[0]-l2[0])**2 + (l1[1]-l2[1])**2) >= min_dist for l2 in distinct):
            distinct.append(l1)
    return group_and_sort(distinct, th / 2)


def detect_ayas_hough(page_num, images_folder, template_2, param2=30, min_r=12, max_r=22):
    """Detect aya markers using HoughCircles as fallback."""
    img = cv2.imread(os.path.join(images_folder, f"{page_num:03}.jpg"))
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th, tw = template_2.shape[:2]
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=15,
                              param1=50, param2=param2, minRadius=min_r, maxRadius=max_r)
    if circles is None:
        return []
    good = [(int(c[0] - tw//2), int(c[1] - th//2)) for c in circles[0]
            if 40 < c[1] < img.shape[0] - 50 and min_r <= c[2] <= max_r]
    return group_and_sort(good, th / 2)


def normalize_coordinates(page, x, y):
    """Convert raw pixel coords (top-left of template) to normalized center coords (0-1)."""
    if page <= 2:
        # Pages 1-2: 486x738 pixels, template 52x52
        return round((x + 26) / 486, 4), round((y + 26) / 738, 4)
    else:
        # Pages 3-604: 645x1000 pixels, template 42x42
        return round((x + 21) / 645, 4), round((y + 21) / 1000, 4)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)  # repo root where images are
    images_folder = os.path.join(script_dir, "images")

    # Load templates
    template_1 = cv2.imread(os.path.join(script_dir, "template_1.jpg"))
    template_2 = cv2.imread(os.path.join(script_dir, "template_2.jpg"))
    if template_1 is None or template_2 is None:
        print("Error: template_1.jpg and template_2.jpg must be in the code/ folder")
        sys.exit(1)

    # Load authoritative page-verse mapping
    pv_path = os.path.join(script_dir, "page_verses.json")
    if not os.path.exists(pv_path):
        print(f"Error: {pv_path} not found. Run fetch_page_verses.py first.")
        sys.exit(1)
    with open(pv_path) as f:
        auth_verses = json.load(f)

    # Check images folder
    if not os.path.exists(images_folder):
        print(f"Error: {images_folder} not found.")
        print("Create it with zero-padded symlinks: ln -s ../1.jpg images/001.jpg etc.")
        sys.exit(1)

    output_rows = []
    issues = []

    for page in range(1, 605):
        expected_verses = auth_verses[str(page)]
        expected_count = len(expected_verses)

        # Default threshold
        default_thresh = 0.4 if page <= 2 else 0.2685
        coords = detect_ayas_template(page, default_thresh, images_folder, template_1, template_2)

        if len(coords) == expected_count:
            for (surah, verse), (x, y) in zip(expected_verses, coords):
                output_rows.append((surah, verse, page, x, y))
            continue

        # Try adjusting threshold
        best_coords, best_diff = coords, abs(len(coords) - expected_count)
        for t in [i/1000 for i in range(200, 500, 5)]:
            c = detect_ayas_template(page, t, images_folder, template_1, template_2)
            d = abs(len(c) - expected_count)
            if d < best_diff:
                best_diff, best_coords = d, c
                if d == 0:
                    break

        if best_diff == 0:
            for (surah, verse), (x, y) in zip(expected_verses, best_coords):
                output_rows.append((surah, verse, page, x, y))
            continue

        # HoughCircles fallback
        for p2 in [30, 28, 25]:
            hcoords = detect_ayas_hough(page, images_folder, template_2, param2=p2)
            if len(hcoords) == expected_count:
                best_coords, best_diff = hcoords, 0
                break

        if best_diff == 0:
            for (surah, verse), (x, y) in zip(expected_verses, best_coords):
                output_rows.append((surah, verse, page, x, y))
        else:
            issues.append((page, expected_count, len(best_coords)))
            for i, (surah, verse) in enumerate(expected_verses):
                if i < len(best_coords):
                    x, y = best_coords[i]
                elif best_coords:
                    x, y = best_coords[-1]
                else:
                    x, y = 0, 0
                output_rows.append((surah, verse, page, x, y))

        if page % 100 == 0:
            print(f"Processed {page}/604...")

    # Write normalized CSV to repo root
    output_path = os.path.join(parent_dir, "data.csv")
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['surah_number', 'verse_number', 'page', 'x', 'y'])
        for surah, verse, page, raw_x, raw_y in output_rows:
            nx, ny = normalize_coordinates(page, raw_x, raw_y)
            writer.writerow([surah, verse, page, nx, ny])

    print(f"\nWrote {len(output_rows)} rows to {output_path}")

    if issues:
        print(f"\nWarning: {len(issues)} pages had detection issues:")
        for p, exp, got in issues:
            print(f"  Page {p}: expected {exp}, detected {got}")
    else:
        print("All 604 pages matched perfectly!")

    # Verify key pages
    with open(output_path) as f:
        rows = list(csv.DictReader(f))
    for p in [1, 2, 22, 50, 604]:
        pg = [r for r in rows if r['page'] == str(p)]
        first, last = pg[0], pg[-1]
        print(f"  Page {p}: {first['surah_number']}:{first['verse_number']} - "
              f"{last['surah_number']}:{last['verse_number']} ({len(pg)} verses)")


if __name__ == '__main__':
    main()
