#!/usr/bin/env python3
"""
Generate data_verse.csv with start and end coordinates for each verse for highlighting.

Verse segments are computed using the same logic as the app's getVerseHighlightRows():
- Input: data.csv (surah_number, verse_number, page, x, y) where x,y is the verse END (marker).
- Single line: one segment from verse.x to prevVerse.x on that line.
- Multi-line: first line (prevVerse.y) from left edge to prevVerse.x; middle lines full width;
  last line (verse.y) from verse.x to right edge.
Constants: LINE_HEIGHT=0.055, LEFT_EDGE=0.05, RIGHT_EDGE=0.95 (match app).

Output: data_verse.csv with columns:
  page, surah_number, verse_number, segment, x_start, y_start, x_end, y_end
  - All coordinates normalized 0.0–1.0
  - App usage: highlight_rect = (x_start*w, y_start*h, x_end*w, y_end*h)

Prerequisites: same as generate_data.py
  pip install opencv-python numpy

Usage:
  1. Ensure images/ symlinks and page_verses.json exist (see code/README.md)
  2. Run: python3 generate_verse_data.py
     Or use existing data.csv: python3 generate_verse_data.py --from-csv
  3. Output: ../data_verse.csv
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
        return round((x + 26) / 486, 4), round((y + 26) / 738, 4)
    else:
        return round((x + 21) / 645, 4), round((y + 21) / 1000, 4)


# App-style constants (match TypeScript getVerseHighlightRows / findVerseAtCoordinate)
LINE_HEIGHT = 0.055
TOP_FIRST_LINE_Y = LINE_HEIGHT / 2  # 0.0275
LEFT_EDGE = 0.05
RIGHT_EDGE = 0.95


def get_verse_highlight_rows(page_data, verse_index):
    """
    Mirror of app's getVerseHighlightRows: from data.csv (x,y = verse END marker),
    return list of (y_center, start_x, end_x) for each line the verse occupies.
    RTL: verse.x is at END of verse (marker on left); text flows right to left.
    """
    if verse_index < 0 or verse_index >= len(page_data):
        return []
    surah, verse_num, page, x, y = page_data[verse_index]
    prev_verse = page_data[verse_index - 1] if verse_index > 0 else None

    rows = []  # list of (y, start_x, end_x)

    # Case 1: First verse on page
    if prev_verse is None or prev_verse[2] != page:
        is_on_first_line = y <= TOP_FIRST_LINE_Y + LINE_HEIGHT / 2
        if is_on_first_line:
            rows.append((y, x, RIGHT_EDGE))
            return rows
        # Multi-line first verse: leave 1/4 line at top for frame, then full-width rows down to verse line
        current_y = TOP_FIRST_LINE_Y + LINE_HEIGHT / 4
        while current_y < y - LINE_HEIGHT / 2:
            rows.append((current_y, LEFT_EDGE, RIGHT_EDGE))
            current_y += LINE_HEIGHT
        rows.append((y, x, RIGHT_EDGE))
        return rows

    prev_x, prev_y = prev_verse[3], prev_verse[4]

    # Case 2: Single line verse (prev and current on same line)
    if abs(prev_y - y) < LINE_HEIGHT:
        rows.append((y, x, prev_x))
        return rows

    # Case 3: Multi-line verse (prev on line above)
    # First line (prevVerse's line): from left edge to prevVerse.x
    rows.append((prev_y, LEFT_EDGE, prev_x))
    current_y = prev_y + LINE_HEIGHT
    while current_y < y - LINE_HEIGHT / 2:
        rows.append((current_y, LEFT_EDGE, RIGHT_EDGE))
        current_y += LINE_HEIGHT
    rows.append((y, x, RIGHT_EDGE))
    return rows


def verse_boxes_from_app_logic(rows):
    """
    Build data_verse.csv segments using the same logic as the app's getVerseHighlightRows.
    Input: list of (surah, verse, page, x, y) in reading order; x,y = verse end (marker).
    Output: list of (surah, verse, page, segment, x_start, y_start, x_end, y_end).
    Each highlight row (y, start_x, end_x) becomes one segment with y_start/y_end = y ± LINE_HEIGHT/2.
    """
    out = []
    # Group by page to get page_data lists
    by_page = {}
    for r in rows:
        page = r[2]
        if page not in by_page:
            by_page[page] = []
        by_page[page].append(r)

    for page, page_data in by_page.items():
        for verse_index in range(len(page_data)):
            surah, verse_num, _page, _x, _y = page_data[verse_index]
            highlight_rows = get_verse_highlight_rows(page_data, verse_index)
            for seg_idx, (y_center, start_x, end_x) in enumerate(highlight_rows):
                y_lo = y_center - LINE_HEIGHT / 2
                y_hi = y_center + LINE_HEIGHT / 2
                x_lo = min(start_x, end_x)
                x_hi = max(start_x, end_x)
                out.append((
                    surah, verse_num, page, seg_idx,
                    round(max(0, min(1, x_lo)), 4), round(max(0, min(1, y_lo)), 4),
                    round(max(0, min(1, x_hi)), 4), round(max(0, min(1, y_hi)), 4)
                ))
    return out


def load_markers_from_csv(data_csv_path):
    """Load (surah, verse, page, x, y) rows from data.csv in reading order."""
    rows = []
    with open(data_csv_path) as f:
        for r in csv.DictReader(f):
            rows.append((
                int(r['surah_number']), int(r['verse_number']), int(r['page']),
                float(r['x']), float(r['y'])
            ))
    return rows


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    images_folder = os.path.join(script_dir, "images")
    data_csv_path = os.path.join(parent_dir, "data.csv")
    use_csv = '--from-csv' in sys.argv

    output_rows = []

    issues = []
    if use_csv and os.path.exists(data_csv_path):
        print("Loading marker positions from data.csv...")
        output_rows = load_markers_from_csv(data_csv_path)
        print(f"Loaded {len(output_rows)} verses.")
    else:
        if use_csv and not os.path.exists(data_csv_path):
            print("Error: data.csv not found. Run generate_data.py first or omit --from-csv.")
            sys.exit(1)

        template_1 = cv2.imread(os.path.join(script_dir, "template_1.jpg"))
        template_2 = cv2.imread(os.path.join(script_dir, "template_2.jpg"))
        if template_1 is None or template_2 is None:
            print("Error: template_1.jpg and template_2.jpg must be in the code/ folder")
            sys.exit(1)

        pv_path = os.path.join(script_dir, "page_verses.json")
        if not os.path.exists(pv_path):
            print(f"Error: {pv_path} not found. Run fetch_page_verses.py first.")
            sys.exit(1)
        with open(pv_path) as f:
            auth_verses = json.load(f)

        if not os.path.exists(images_folder):
            print(f"Error: {images_folder} not found. Run setup_images.sh first.")
            sys.exit(1)

        issues = []
        for page in range(1, 605):
            expected_verses = auth_verses[str(page)]
            expected_count = len(expected_verses)
            default_thresh = 0.4 if page <= 2 else 0.2685
            coords = detect_ayas_template(page, default_thresh, images_folder, template_1, template_2)

            if len(coords) != expected_count:
                best_coords, best_diff = coords, abs(len(coords) - expected_count)
                for t in [i/1000 for i in range(200, 500, 5)]:
                    c = detect_ayas_template(page, t, images_folder, template_1, template_2)
                    d = abs(len(c) - expected_count)
                    if d < best_diff:
                        best_diff, best_coords = d, c
                        if d == 0:
                            break
                if best_diff != 0:
                    for p2 in [30, 28, 25]:
                        hcoords = detect_ayas_hough(page, images_folder, template_2, param2=p2)
                        if len(hcoords) == expected_count:
                            best_coords, best_diff = hcoords, 0
                            break
                coords = best_coords
                if best_diff != 0:
                    issues.append((page, expected_count, len(coords)))

            for (surah, verse), (raw_x, raw_y) in zip(expected_verses, coords):
                nx, ny = normalize_coordinates(page, raw_x, raw_y)
                output_rows.append((surah, verse, page, nx, ny))
            for k in range(len(coords), expected_count):
                surah, verse = expected_verses[k]
                output_rows.append((surah, verse, page, 0.0, 0.0))

            if page % 100 == 0:
                print(f"Processed page {page}/604...")

    # --- Build verse segments from app logic (getVerseHighlightRows) using data.csv only ---
    verse_boxes = verse_boxes_from_app_logic(output_rows)

    # --- Write data_verse.csv ---
    output_path = os.path.join(parent_dir, "data_verse.csv")
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['page', 'surah_number', 'verse_number', 'segment', 'x_start', 'y_start', 'x_end', 'y_end'])
        for surah, verse, page, segment, x_start, y_start, x_end, y_end in verse_boxes:
            writer.writerow([page, surah, verse, segment, x_start, y_start, x_end, y_end])

    print(f"\nWrote {len(verse_boxes)} rows to {output_path}")

    if issues:
        print(f"Warning: {len(issues)} pages had detection issues:")
        for p, exp, got in issues[:5]:
            print(f"  Page {p}: expected {exp}, detected {got}")
        if len(issues) > 5:
            print(f"  ... and {len(issues)-5} more")
    elif not use_csv:
        print("All 604 pages matched perfectly.")

    print("\nUsage in app: highlight rect = (x_start * width, y_start * height, x_end * width, y_end * height)")


if __name__ == '__main__':
    main()
