


import logging
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Tuple

import yaml
from PIL import Image

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PRJ_PATH = Path("~/Projekt/blog/").expanduser()
DEFAULT_CONFIG = Path("_config.yml")
DEFAULT_WIDTH = ['responsive', 'widths']

DEFAULT_CATEGORIES_YML_PATH = DEFAULT_PRJ_PATH / "_data/categories.yml"
DEFAULT_THUMBS_PATH = DEFAULT_PRJ_PATH / "assets/thumbs"
DEFAULT_IMG_PATH = DEFAULT_PRJ_PATH / "assets/img"

shutil.rmtree(DEFAULT_THUMBS_PATH)

if DEFAULT_CATEGORIES_YML_PATH.exists():
    # Entfernen Sie die Datei
    DEFAULT_CATEGORIES_YML_PATH.unlink()

def read_yaml_key(yaml_file: Path, key_path: List[str]) -> List[int]:
    """
    Read a specific key path from a YAML file.

    Args:
    - yaml_file (str): Path to the YAML file.
    - key_path (list of str): List representing the key path.

    Returns:
    - Value corresponding to the specified key path.
    """
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)
        
        # Traverse the key path
        value = data
        for key in key_path:
            value = value[key]
        
        if isinstance(value, list) and bool(value):
            return value
        return []

def extract_filename_without_extension(file_path: Path) -> str:
    """Extract the filename without the extension from a given file path."""
    try:
        return file_path.stem
    except Exception as e:
        raise RuntimeError(f"Error occurred while extracting filename: {e}")

def resize_and_compress_webp(input_path: Path, output_path: Path, target_width: int, quality:int =30):
    """
    Resize a WebP image while maintaining aspect ratio and compresses it with the given quality.
    
    Args:
    input_path (str): Path to the input WebP image file.
    output_path (str): Path to save the resized and compressed WebP image.
    target_width (int): The target width for resizing the image while maintaining aspect ratio.
    quality (int, optional): Compression quality level (0-100, higher is better). Default is 30.
    """
    # Open the WebP image
    image = Image.open(input_path)

    # Get the original width and height
    original_width, original_height = image.size

    # Calculate the new height while maintaining the aspect ratio
    new_height = int((original_height / original_width) * target_width)

    # Resize the image
    resized_image = image.resize((target_width, new_height), Image.LANCZOS)

    # Save the resized and compressed image
    resized_image.save(output_path, "WEBP", quality=quality)


def create_responsive_path(dst_path: Path, width: int) -> Path:
    """
    Creates a responsive path by appending the width to the filename without extension.

    Args:
    - dst_path (Path): The destination path containing the filename.
    - width (int): The width value to be appended to the filename.

    Returns:
    - Path: The new path with the width appended to the filename.

    Example:
    >>> create_responsive_path(Path('/home/user/images/image.jpg'), 500)
    Path('/home/user/images/image-500w.jpg')
    """
    name = extract_filename_without_extension(dst_path)
    new_name = name + f"-{width}w" + dst_path.suffix
    new_path = Path(str(dst_path.parent).replace('img', 'thumbs')) / new_name
    #new_path.mkdir(parents=True, exist_ok=True)
    return new_path

def process_images(args: Tuple[Path, Path, int, int]):
    """Process image by resizing/compressing and converting to WebP."""
    src_path, dst_path, width, quality = args
    width = read_yaml_key(DEFAULT_CONFIG, DEFAULT_WIDTH)
    for w in width:
        new_dst_path = create_responsive_path(dst_path, w)
        resize_and_compress_webp(src_path, new_dst_path, target_width=w, quality=quality)

def optimize_process(images_to_process: List[Tuple[Path, Path]],  width: int, quality: int) -> None:
    """Optimize image processing using ProcessPoolExecutor."""
    with ProcessPoolExecutor() as executor:
        logger.info(f"Process {len(images_to_process)} images")
        executor.map(process_images, [(src_path, dst_path, width, quality) for src_path, dst_path in images_to_process])


def update_destination_folder(root: str, input_folder: Path, output_folder: Path) -> Path:
    """
    Update destination folder based on root path, input folder, and output folder.

    Args:
        root (str): Root path.
        input_folder (Path): Path to the input folder.
        output_folder (Path): Path to the output folder.

    Returns:
        tuple: A tuple containing the folder type and the path to the updated destination folder.
    """
    try:
        folder_type = Path(root).relative_to(input_folder)
        dst_folder = output_folder / folder_type
        if folder_type != Path(".") and dst_folder.is_dir():
            shutil.rmtree(dst_folder)
            logger.info(f"Removing existing destination folder: {dst_folder}")
        dst_folder.mkdir(parents=True, exist_ok=True)
        return dst_folder
    except Exception as e:
        logger.error(f"Error updating destination folder: {e}")
        raise RuntimeError

def organize_images(input_folder: Path, output_folder: Path, width: int = 1200, quality: int = 40) -> None:
    """Organize images and convert to WebP format."""

    for root, _, files in os.walk(input_folder):
        dst_folder = update_destination_folder(root, input_folder, output_folder)
        images_to_process = []
        for filename in sorted(files):
            try:
                if filename.endswith('.webp'):
                    src_path = Path(root) / filename
                    dst_path = dst_folder / filename
                    images_to_process.append((src_path, dst_path))
            except ValueError:
                logger.warning(f"Error occurred while splitting filename: {filename}. Skipping this file.")
                continue

        optimize_process(images_to_process, width, quality)


def main() -> None:
    """Main function to organize images in folders."""
    try:
        input_folder_path = DEFAULT_IMG_PATH
        output_folder_path = DEFAULT_THUMBS_PATH
        organize_images(input_folder_path, output_folder_path)
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()