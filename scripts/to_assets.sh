#!/bin/bash

process_images() {
  input_folder="${1:-.}"                                                     # Use current folder if no argument provided
  output_folder="/home/inco/prj/one-shot-monkey.github.io/assets/img/banner" # Default to 'processed' folder if not specified

  mkdir -p "$output_folder"

  find "$input_folder" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | while read -r file; do
    filename=$(basename "$file")
    name_without_ext="${filename%.*}"

    # Resize and crop
    convert "$file" -resize 1200x -crop 1200x630+0+0 +repage "$output_folder/temp.jpg"

    # Convert to WebP
    cwebp -q 80 "$output_folder/temp.jpg" -o "$output_folder/${name_without_ext}.webp"

    # Generate LQIP
    lqip=$(magick "$output_folder/${name_without_ext}.webp" -resize 20x20 -strip -quality 20 webp:- | base64 -w 0)

    # Print filename and LQIP with start string
    echo "path: /assets/img/banner/$name_without_ext.webp"
    echo "lqip: data:image/webp;base64,${lqip}"
    echo "---"
  done
}

# Call the function with current folder and default output folder
process_images
