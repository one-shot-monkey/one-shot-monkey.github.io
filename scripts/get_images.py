

import base64
import io
import logging
import os
import re
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from PIL import Image

app = typer.Typer()

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("_config.yml")
DEFAULT_IN_PATH = Path("~/pic/website/Raw").expanduser()
DEFAULT_PRJ_PATH = Path("~/Projekt/blog/").expanduser()
DEFAULT_CATEGORIES_YML_PATH = DEFAULT_PRJ_PATH / "_data/categories.yml"

def shorten_filename(idx: int, filename: str) -> str:
    """
    Shorten filename by replacing timestamp with index and changing extension to WebP.

    Args:
        idx (int): Index to replace the timestamp in the filename.
        filename (str): Original filename.

    Returns:
        str: Shortened filename with timestamp replaced by index and extension changed to WebP.
    """
    try:
        return re.sub(r'\d{8}-\d{6}', str(idx + 1), filename.replace('.jpg', '.webp'))
    except re.error as re_err:
        logger.error(f"Regular expression error occurred while shortening filename: {re_err}")
        raise RuntimeError
    except Exception as e:
        logger.error(f"Error occurred while shortening filename: {e}")
        raise RuntimeError

def resize_and_compress(input_path: Path, output_path: Path, width: int, quality: int) -> None:
    """
    Resize and compress image.

    Args:
        input_path (Path): Path to the input image file.
        output_path (Path): Path to save the resized and compressed image.
        width (int): Width of the resized image.
        quality (int): Quality of the compressed image (0-100).

    Raises:
        RuntimeError: If an error occurs during resizing or compressing the image.
    """
    try:
        with Image.open(input_path) as img:
            img.thumbnail((width, width//2))
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
    except Exception as e:
        logger.error(f"Error resizing or compressing image: {e}")
        raise RuntimeError(f"Error resizing or compressing image: {e}")

def convert_to_webp(input_path: Path, output_path: Path, quality: int = 90) -> None:
    """
    Convert image to WebP format.

    Args:
        input_path (Path): Path to the input image file.
        output_path (Path): Path to save the converted WebP image.
        quality (int, optional): Quality of the WebP image (0-100). Defaults to 90.

    Raises:
        RuntimeError: If an error occurs during conversion to WebP format.
    """
    try:
        with Image.open(input_path) as img:
            img.save(output_path, 'webp', quality=quality)
    except FileNotFoundError as fnf_err:
        logger.error(f"Input image file not found: {input_path}")
        raise RuntimeError(f"Error converting image to WebP: {fnf_err}")
    except OSError as os_err:
        logger.error(f"OS error occurred during WebP conversion: {os_err}")
        raise RuntimeError(f"Error converting image to WebP: {os_err}")
    except Exception as e:
        logger.error(f"Unexpected error occurred during WebP conversion: {e}")
        raise RuntimeError(f"Error converting image to WebP: {e}")


def extract_filename_without_extension(file_path: Path) -> str:
    """
    Extract the filename without the extension from a given file path.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: Filename without extension.
    """
    try:
        return file_path.stem
    except Exception as e:
        raise RuntimeError(f"Error occurred while extracting filename: {e}")

def write_to_categories_yaml(image_path: Path) -> None:
    """
    Write data to the categories YAML file.

    Args:
        image_path (str): The path to the image.
    """

    name = extract_filename_without_extension(image_path)

    # Öffnen Sie das Bild mit Pillow
    with Image.open(image_path) as img:
        # Konvertieren Sie das Bild in den RGB-Modus
        img = img.convert("RGB")

        # Reduzieren Sie die Qualität des Bildes und speichern Sie es als BytesIO-Objekt
        img_byte_array = io.BytesIO()
        img.save(img_byte_array, format='WebP', quality=0.01, optimize=True)
        img_byte_array.seek(0)

        # Kodieren Sie das komprimierte Bild in Base64
        encoded_string = base64.b64encode(img_byte_array.read()).decode("utf-8")
    
    logger.info(f"Write {name} into {DEFAULT_CATEGORIES_YML_PATH}")
    with open(DEFAULT_CATEGORIES_YML_PATH, 'a') as file:
        file.write("- name: {}\n".format(name))
        file.write("  image:\n")
        file.write("    path: /assets/img/categories/{}.webp\n".format(name))        
        file.write("    lqip: {}\n\n".format(encoded_string))

def process_image(args: Tuple[Path, str, Path, int, int]):
    """Process image by resizing/compressing and converting to WebP."""
    src_path, folder_type, dst_path, width, quality = args
    resize_and_compress(src_path, dst_path, width=width, quality=quality)
    convert_to_webp(dst_path, dst_path, quality=quality)
    if folder_type == "categories":
        write_to_categories_yaml(dst_path)


def optimize_process(images_to_process: List[Tuple[Path, Path]], folder_type: str,  width: int, quality: int) -> None:
    """Optimize image processing using ProcessPoolExecutor."""
    with ProcessPoolExecutor() as executor:
        logger.info(f"Process {len(images_to_process)} images")
        executor.map(process_image, [(src_path, folder_type, dst_path, width, quality) for src_path, dst_path in images_to_process])

def extract_gallery_from_filename(filename: str) -> Tuple[str, str]:
    """Extracts gallery name and modified filename from the given filename."""
    if "#" in filename:
        filename, ending = filename.split("#", 1)  # Use maxsplit=1 to split only once
        filename += ".jpg"
        gallery = ending.split(".", 1)[0]  # Use maxsplit=1 to split only once
    else:
        gallery = ""
    return gallery, filename

def create_gallery_folder(dst_folder: Path, gallery: str) -> Path:
    """Creates a gallery folder inside the destination folder if gallery name is provided."""
    if gallery:  # If gallery is not empty
        dst_folder_path = dst_folder / gallery  # Append gallery subfolder
        dst_folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created a new gallery folder: {dst_folder_path}")
        return dst_folder_path
    return dst_folder  # If gallery is empty, return original destination folder

def update_destination_folder(root: str, input_folder: Path, output_folder: Path) -> Tuple[Path, Path]:
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
        if folder_type != Path("."):
            shutil.rmtree(dst_folder)
            logger.info(f"Removing existing destination folder: {dst_folder}")
        dst_folder.mkdir(parents=True, exist_ok=True)
        return folder_type, dst_folder
    except Exception as e:
        logger.error(f"Error updating destination folder: {e}")
        raise RuntimeError

def organize_images(input_folder: Path, output_folder: Path, subfolder: Optional[str]=None, width: int = 1200, quality: int = 80) -> None:
    """Organize images and convert to WebP format."""

    for root, _, files in os.walk(input_folder):
        folder_type, dst_folder = update_destination_folder(root, input_folder, output_folder)
        if subfolder:
            folder_type=subfolder
        images_to_process = []

        if folder_type == "categories" and DEFAULT_CATEGORIES_YML_PATH.exists():
            # Entfernen Sie die Datei
            DEFAULT_CATEGORIES_YML_PATH.unlink()

        for idx, filename in enumerate(sorted(files)):
            try:
                if filename.endswith('.jpg'):
                    src_path = Path(root) / filename
                    gallery, filename = extract_gallery_from_filename(filename)
                    dst_folder_path = create_gallery_folder(dst_folder, gallery)
                    dst_path = dst_folder_path / shorten_filename(idx, filename)
                    images_to_process.append((src_path, dst_path))
            except ValueError:
                logger.warning(f"Error occurred while splitting filename: {filename}. Skipping this file.")
                continue

        optimize_process(images_to_process, str(folder_type), width, quality)

@app.command()
def main(subfolder: str = "") -> None:
    """Main function to organize images in folders."""
    try:
        input_folder_path = DEFAULT_IN_PATH / subfolder
        output_folder_path = DEFAULT_PRJ_PATH / "assets/img" /subfolder
        organize_images(input_folder_path, output_folder_path, subfolder)
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    app()