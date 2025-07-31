import datetime
import logging
import os
import shutil
from pathlib import Path

# Define paths
FOTO_INBOX_DIR = '/Users/fluffyoctopus/Documents/FotoInbox'
FOTOS_DIR = '/Users/fluffyoctopus/kDrive/Common documents/Fotos'


def find_jpg_match(raw_filename):
    """Find the matching JPG file in the Fotos directory structure."""
    # Get the base name without extension
    base_name = os.path.splitext(os.path.basename(raw_filename))[0]

    # Create the jpg filename pattern to search for
    jpg_filename = f"{base_name}.jpg"

    # Search for the jpg file in all subdirectories
    jpg_matches = []
    for root, dirs, files in os.walk(FOTOS_DIR):
        for file in files:
            if file.lower() == jpg_filename.lower():
                # if file was modified in the last 24h, only then add it
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) > (datetime.datetime.now() - datetime.timedelta(days=1)).timestamp():
                    jpg_matches.append(os.path.join(root, file))

    return jpg_matches


def find_closest_raw_folder(jpg_path):
    """Find the closest RAW folder starting from the JPG's path and going up."""
    path = Path(jpg_path).parent

    while str(path).startswith(FOTOS_DIR):
        # Check if this directory has a RAW subfolder
        raw_dir = path / "RAW"
        if raw_dir.exists() and raw_dir.is_dir():
            return raw_dir

        # Check if this directory has any subfolder containing "RAW" in its name
        for item in path.iterdir():
            if item.is_dir() and "RAW" in item.name.upper():
                return item

        # Move up one directory
        path = path.parent

    return None


def process_inbox():
    """Process all files in the FotoInbox directory."""
    # Get all .ARW files
    raw_files = [f for f in os.listdir(FOTO_INBOX_DIR)
                 if f.lower().endswith('.arw') and not f.lower().endswith('.dop')]

    moved_files = []
    no_match_found = []

    for raw_file in raw_files:
        raw_path = os.path.join(FOTO_INBOX_DIR, raw_file)
        dop_file = raw_file + '.dop'
        dop_path = os.path.join(FOTO_INBOX_DIR, dop_file)

        # Find matching JPG files
        jpg_matches = find_jpg_match(raw_file)

        if not jpg_matches:
            no_match_found.append(raw_file)
            continue

        # If multiple matches, use the first one
        jpg_path = jpg_matches[0]

        # Find closest RAW folder
        raw_folder = find_closest_raw_folder(jpg_path)

        if not raw_folder:
            continue

        # Move the RAW file
        dest_raw_path = os.path.join(raw_folder, raw_file)
        try:
            shutil.move(raw_path, dest_raw_path)
            moved_files.append(raw_file)

            # Move the DOP file if it exists
            if os.path.exists(dop_path):
                dest_dop_path = os.path.join(raw_folder, dop_file)
                shutil.move(dop_path, dest_dop_path)
                moved_files.append(dop_file)
        except Exception as e:
            print(f"Error moving {raw_file}: {str(e)}")

    # Clean up remaining files (excluding moved files)
    print(f"Moved {int(len(moved_files) / 2)} files")
    print(f"Found no match for {len(no_match_found)} files")
    cleanup_inbox(moved_files)


def cleanup_inbox(moved_files):
    """Delete all remaining files in the FotoInbox directory."""
    remaining_files = [f for f in os.listdir(FOTO_INBOX_DIR)
                       if os.path.isfile(os.path.join(FOTO_INBOX_DIR, f))]

    for file in remaining_files:
        file_path = os.path.join(FOTO_INBOX_DIR, file)
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting {file}: {str(e)}")

    print(f"Deleted {len(remaining_files)} files")


if __name__ == "__main__":
    process_inbox()
