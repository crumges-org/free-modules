# watermark_script.py
import os
from PIL import Image

# === CONFIGURATION ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory where the script is located
screenshot_folder = os.path.join(BASE_DIR, 'screenshots')          # Folder containing screenshots
output_folder = os.path.join(BASE_DIR, 'screenshots_with_logo')    # Output folder
logo_path = os.path.join(BASE_DIR, 'logo.jpg')                     # Path to logo image
logo_size_ratio = 0.15                     # Logo width relative to screenshot width
margin = 20                                # Margin in pixels from the edge

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Load logo image once and convert to RGBA
try:
    logo_original = Image.open(logo_path).convert("RGBA")
except Exception as e:
    print(f"❌ Error loading logo image: {e}")
    exit(1)

# Process each image in the folder
for filename in os.listdir(screenshot_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img_path = os.path.join(screenshot_folder, filename)
        try:
            image = Image.open(img_path).convert("RGBA")
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            continue

        # Resize logo proportionally based on image width
        logo_width = int(image.width * logo_size_ratio)
        logo_height = int(logo_width * logo_original.height / logo_original.width)
        logo = logo_original.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Position: top-right with margin
        position = (image.width - logo.width - margin, margin)

        # Paste logo depending on image format
        if filename.lower().endswith(('.jpg', '.jpeg')):
            image = image.convert("RGB")  # remove alpha channel
            image.paste(logo, position, logo.convert("RGBA"))
        else:
            image.paste(logo, position, logo)

        # Save the output image
        output_path = os.path.join(output_folder, filename)
        image.save(output_path)

        print(f"✅ Processed: {filename}")

print("\n🎉 All screenshots processed and saved to:", output_folder)
