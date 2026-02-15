#!/bin/bash
# Create the images/ folder with zero-padded symlinks required by the detection scripts.
# Run from the code/ directory.
#
# Usage: bash setup_images.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGES_DIR="$SCRIPT_DIR/images"

mkdir -p "$IMAGES_DIR"

for i in $(seq 1 604); do
    src="$REPO_ROOT/$(printf '%d' $i).jpg"
    dst="$IMAGES_DIR/$(printf '%03d' $i).jpg"
    if [ -f "$src" ]; then
        ln -sf "$src" "$dst"
    else
        echo "Warning: $src not found"
    fi
done

echo "Created symlinks in $IMAGES_DIR (001.jpg - 604.jpg)"
