#!/usr/bin/env python3
"""
Fetch authoritative Quran page-verse mapping from the mushaf-layout dataset.

Downloads the correct surah:verse list for each of the 604 Madani Mushaf pages
from https://github.com/zonetecde/mushaf-layout

Output: page_verses.json - mapping of page number to list of [surah, verse] pairs

Usage:
  python3 fetch_page_verses.py
"""
import urllib.request
import json
import ssl
import os
import sys

# Standard Hafs verse counts (used for cross-surah line handling)
SURAH_VERSE_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109,
    123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85,
    54, 53, 89, 59, 37, 35, 38, 29, 18, 45,
    60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
    14, 11, 11, 18, 12, 12, 30, 52, 52, 44,
    28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20,
    15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
    11, 8, 3, 9, 5, 4, 7, 3, 6, 3,
    5, 4, 5, 6
]


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "page_verses.json")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    page_verses = {}
    errors = []

    for page in range(1, 605):
        url = f"https://raw.githubusercontent.com/zonetecde/mushaf-layout/main/mushaf/page-{page:03d}.json"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read())

                verses = []
                for line in data.get('lines', []):
                    vr = line.get('verseRange', '')
                    if not vr:
                        continue
                    start, end = vr.split('-')
                    s_surah, s_verse = int(start.split(':')[0]), int(start.split(':')[1])
                    e_surah, e_verse = int(end.split(':')[0]), int(end.split(':')[1])

                    if s_surah == e_surah:
                        for v in range(s_verse, e_verse + 1):
                            verses.append((s_surah, v))
                    else:
                        for v in range(s_verse, SURAH_VERSE_COUNTS[s_surah - 1] + 1):
                            verses.append((s_surah, v))
                        for v in range(1, e_verse + 1):
                            verses.append((e_surah, v))

                # Deduplicate preserving order
                seen = set()
                unique = []
                for v in verses:
                    if v not in seen:
                        seen.add(v)
                        unique.append(v)

                page_verses[page] = unique

        except Exception as e:
            errors.append((page, str(e)))
            print(f"  Error page {page}: {e}")

        if page % 100 == 0:
            print(f"Fetched {page}/604...")

    if errors:
        print(f"\n{len(errors)} errors occurred. Cannot proceed.")
        sys.exit(1)

    # Verify total
    total = sum(len(v) for v in page_verses.values())
    print(f"\nFetched {len(page_verses)} pages, {total} total verses")

    if total != 6236:
        print(f"WARNING: Expected 6236 verses, got {total}")

    # Save
    with open(output_path, 'w') as f:
        json.dump({str(k): v for k, v in page_verses.items()}, f)

    print(f"Saved to {output_path}")


if __name__ == '__main__':
    main()
