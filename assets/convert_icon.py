from PIL import Image
import os

source_path = 'icon.png'
dest_path = 'icon.ico'

try:
    if not os.path.exists(source_path):
        print(f"Error: {source_path} not found.")
        exit(1)

    img = Image.open(source_path)
    # Save as ICO including multiple sizes for better scaling in Windows
    img.save(dest_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Successfully converted {source_path} to {dest_path}")

except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)
