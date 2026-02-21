# Code — Regenerating data.csv

Scripts to detect aya marker positions in Quran page images and generate the verse coordinate mapping.

## Prerequisites

```bash
pip install opencv-python numpy
```

Python 3.6+

## Files

| File | Purpose |
|------|---------|
| `generate_data.py` | **Main script** — detects aya markers, maps to surah/verse, outputs `data.csv` |
| `generate_verse_data.py` | Builds verse bounding boxes from markers; outputs `data_verse.csv` for verse highlighting |
| `fetch_page_verses.py` | Downloads authoritative page-verse mapping from GitHub |
| `aya_locator.py` | Original template-matching detector (simpler, used as reference) |
| `setup_images.sh` | Creates zero-padded symlinks needed by detection scripts |
| `template_1.jpg` | Aya marker template for pages 1-2 (larger ornate markers) |
| `template_2.jpg` | Aya marker template for pages 3-604 (standard markers) |
| `page_verses.json` | Authoritative surah:verse mapping for each of 604 pages |

## Steps to Regenerate

### 1. Set up image symlinks

```bash
cd code/
bash setup_images.sh
```

This creates `code/images/001.jpg` → `code/images/604.jpg` symlinks pointing to the repo root images.

### 2. Fetch page-verse mapping (optional — already included)

```bash
python3 fetch_page_verses.py
```

Downloads the correct verse list for each page from the [mushaf-layout](https://github.com/zonetecde/mushaf-layout) dataset. The result `page_verses.json` is already included, so this step is only needed if you want to refresh it.

### 3. Generate data.csv

```bash
python3 generate_data.py
```

This will:
- Detect aya markers on all 604 pages using OpenCV template matching
- Auto-tune thresholds per page to match the expected verse count
- Fall back to HoughCircles for pages where template matching fails
- Normalize coordinates to 0.0-1.0 range (center of each marker)
- Write `../data.csv` with columns: `surah_number, verse_number, page, x, y`

Takes ~5-10 minutes depending on your machine.

### 4. Generate data_verse.csv (verse highlighting)

```bash
python3 generate_verse_data.py
```

Or, if you already have `data.csv`, run:

```bash
python3 generate_verse_data.py --from-csv
```

This produces `../data_verse.csv` with columns: `page`, `surah_number`, `verse_number`, `x_start`, `y_start`, `x_end`, `y_end` (all coordinates normalized 0–1). Use in your app to draw highlight rectangles: `(x_start * width, y_start * height)` to `(x_end * width, y_end * height)`.

## How It Works

1. **Template matching** (`cv2.matchTemplate`) finds aya marker circles in each page image
2. **Authoritative mapping** (`page_verses.json`) provides the correct surah:verse for each page
3. The detected coordinates are paired with the known verse sequence in reading order (right-to-left, top-to-bottom)
4. Coordinates are normalized: `(x + half_template) / image_width` to produce 0.0-1.0 values
5. Pages 1-2 have different image dimensions (486x738) and larger templates (52x52) vs pages 3-604 (645x1000, template 42x42)
