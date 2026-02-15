# Hifzai Mushaf Images

604 Hafs Tajweed Quran page images with aya (verse) coordinate mapping for building Quran apps.

## Contents

- `1.jpg` - `604.jpg` — Quran page images (Hafs Tajweed, easyquran.com edition)
- `data.csv` — Verse coordinate mapping (6236 ayat across 604 pages)

## data.csv Format

```csv
surah_number,verse_number,page,x,y
1,1,1,0.1543,0.164
1,2,1,0.2654,0.2737
...
114,6,604,0.2791,0.9
```

| Column | Description |
|--------|-------------|
| `surah_number` | Surah number (1-114) |
| `verse_number` | Verse number within the surah |
| `page` | Mushaf page number (1-604) |
| `x` | Normalized X coordinate of aya marker center (0.0-1.0) |
| `y` | Normalized Y coordinate of aya marker center (0.0-1.0) |

### Usage in your app

```kotlin
// Convert normalized coords to screen position
val displayX = x * imageView.width
val displayY = y * imageView.height
```

Works on **any screen size** — no hardcoded dimensions needed.

## Regenerating data.csv

All code is in the `code/` folder. See [code/README.md](code/README.md) for steps.

## License

Images sourced from [easyquran.com](https://easyquran.com). Page-verse mapping from [mushaf-layout](https://github.com/zonetecde/mushaf-layout).
