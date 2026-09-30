#!/usr/bin/env python3
"""Organize scanned documents into YEAR/DATE/HOUR folders.

Example output:
    Documents/2026/2026-09-30/14/2026-09-30_14-23-05.jpg

The script uses, in order:
1. EXIF capture time for image files;
2. file modified time for PDFs and images without EXIF data.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # Pillow is optional for PDFs and files without EXIF data
    Image = None

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".pdf",
}

# EXIF tags for DateTimeOriginal and DateTimeDigitized.
EXIF_DATE_TAGS = (36867, 36868, 306)


def file_datetime(path: Path) -> datetime:
    """Return the best available date/time for a file."""
    if Image is not None and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}:
        try:
            with Image.open(path) as image:
                exif = image.getexif()
                for tag in EXIF_DATE_TAGS:
                    value = exif.get(tag)
                    if value:
                        try:
                            return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            pass
        except Exception:
            # A damaged or unsupported image falls back to its filesystem time.
            pass

    return datetime.fromtimestamp(path.stat().st_mtime)


def unique_destination(directory: Path, filename: str) -> Path:
    """Avoid overwriting a file that already exists."""
    destination = directory / filename
    counter = 1
    while destination.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        destination = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return destination


def organize(folder: Path, recursive: bool = False, dry_run: bool = False) -> int:
    """Move supported documents into YEAR/DATE/HOUR folders."""
    if not folder.is_dir():
        raise NotADirectoryError(f"Folder does not exist: {folder}")

    files = folder.rglob("*") if recursive else folder.iterdir()
    moved = 0

    for source in sorted(files):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        # When scanning recursively, do not reorganize files already under a year folder.
        if recursive and source.parent != folder and source.parts[len(folder.parts)] not in {""}:
            continue

        captured = file_datetime(source)
        year = captured.strftime("%Y")
        date = captured.strftime("%Y-%m-%d")
        hour = captured.strftime("%H")
        destination_dir = folder / year / date / hour
        filename = f"{captured.strftime('%Y-%m-%d_%H-%M-%S')}{source.suffix.lower()}"
        destination = unique_destination(destination_dir, filename)

        print(f"{source.name} -> {destination.relative_to(folder)}")
        if not dry_run:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        moved += 1

    return moved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize scanned documents into YEAR/DATE/HOUR folders."
    )
    parser.add_argument("folder", nargs="?", type=Path, help="Documents folder to organize")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without moving or renaming files",
    )
    args = parser.parse_args()

    folder = args.folder or Path(input("Documents folder path: ").strip().strip('"'))
    try:
        count = organize(folder, dry_run=args.dry_run)
        action = "would be organized" if args.dry_run else "organized"
        print(f"Done: {count} file(s) {action}.")
    except NotADirectoryError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
