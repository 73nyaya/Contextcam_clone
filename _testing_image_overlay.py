import os
import math
from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFont
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import pandas as pd
from PIL import ExifTags, ImageFilter
import piexif


# %% Functions

def calculate_initial_compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing between two points.
    Returns bearing in degrees (0–360).
    """
    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Calculate the change in coordinates
    dlon = lon2 - lon1

    # Calculate the bearing
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    bearing = math.atan2(x, y)

    # Convert bearing from radians to degrees
    bearing = math.degrees(bearing)

    # Normalize to 0–360
    bearing = (bearing + 360) % 360

    return bearing


def save_image_with_metadata(image_path: str, metadata: dict) -> None:
    # Open the image
    img = Image.open(image_path)

    # Load the existing EXIF data
    exif_dict = piexif.load(img.info.get("exif", b""))

    # Assign GPS information (make sure to follow EXIF format for GPS data)
    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: metadata["GPSLatitudeRef"],
        piexif.GPSIFD.GPSLatitude: metadata["GPSLatitude"],
        piexif.GPSIFD.GPSLongitudeRef: metadata["GPSLongitudeRef"],
        piexif.GPSIFD.GPSLongitude: metadata["GPSLongitude"],
    }

    exif_dict["GPS"] = gps_ifd

    # Convert the updated EXIF data back to bytes
    exif_bytes = piexif.dump(exif_dict)

    # Save the image with the updated EXIF data
    img.save(image_path, "JPEG", exif=exif_bytes)
    img.close()


def _rational_to_float(value) -> float:
    """
    Convert a rational EXIF value (num, den) or plain number to float.
    """
    try:
        num, den = value
        return num / den
    except (TypeError, ValueError):
        return float(value)


def get_decimal_from_dms(dms) -> float:
    """
    Convert DMS tuple from EXIF (each item may be rational) to decimal degrees.
    """
    degrees = _rational_to_float(dms[0])
    minutes = _rational_to_float(dms[1]) / 60.0
    seconds = _rational_to_float(dms[2]) / 3600.0
    return round(degrees + minutes + seconds, 5)


def get_comments_info(image_path: str) -> Optional[Tuple[float, float, str, str, float]]:
    """
    Read GPS coordinates, date/time and bearing from image EXIF.
    Returns (lat, lon, date_str, time_str, bearing_degrees) or None if not available.
    """
    GPS_TAG = 34853           # GPSInfo
    DATETIME_ORIGINAL = 36867 # DateTimeOriginal

    with Image.open(image_path) as img:
        info = img._getexif() or {}

    if GPS_TAG not in info or DATETIME_ORIGINAL not in info:
        return None

    data_dict = info[GPS_TAG]

    # GPSLatitude is tag 2, GPSLongitude is tag 4 in the GPS IFD
    cord1 = get_decimal_from_dms(data_dict[2])
    cord2 = get_decimal_from_dms(data_dict[4])

    date_time_str = info[DATETIME_ORIGINAL]  # e.g. "2025:11:24 10:23:45"
    parts = date_time_str.split(" ")
    date_month_year = parts[0].replace(":", "-")
    hour_min_second = parts[1] if len(parts) > 1 else ""

    angle = calculate_initial_compass_bearing(
        lat1=cord1, lon1=cord2, lat2=0.0, lon2=0.0
    )

    return cord1, cord2, date_month_year, hour_min_second, angle


def create_standardized_overlay_image(
    image_path: str,
    cord1: float,
    cord2: float,
    date_month_year: str,
    hour_min_second: str,
    angle: float,
    glocation: str,
    component: str,
    defect_line1: str,
    defect_line2: str,
    idd: int,
    output_folder: str,
) -> str:
    """Create an overlay with text and save a combined image."""
    with Image.open(image_path) as img:
        base_width, base_height = img.size

    text_size = int(base_height * 0.027)
    box_height = base_height // 12

    overlay_image = Image.new("RGBA", (base_width, base_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay_image, "RGBA")

    transparency = 128

    # Adjust font path if needed for your system
    font = ImageFont.FreeTypeFont(r"C:\Windows\Fonts\CONSOLA.ttf", size=text_size)

    def draw_boxes_with_text(y_position: int, text_lines):
        """
        text_lines: list of lists of text lines, e.g.
        [
            ["DIRECTION", "123 deg(T)"],
            ["-31.12345°S", "115.12345°E"],
            ...
        ]
        """
        num_boxes = len(text_lines)
        box_width = base_width // num_boxes
        for i, lines in enumerate(text_lines):
            x_position = i * box_width
            box = (x_position, y_position, x_position + box_width, y_position + box_height)
            draw.rectangle(box, fill=(0, 0, 0, transparency))

            for j, line in enumerate(lines):
                # Ensure line is always a string (this fixes the float error)
                if line is None:
                    line = ""
                else:
                    line = str(line)

                text_bbox = draw.textbbox((0, 0), line, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = x_position + (box_width - text_width) // 2

                if j == 1:
                    text_y = (
                        y_position
                        + 20
                        + (box_height - text_height * len(lines)) // 2
                        + (text_height * j)
                    )
                else:
                    text_y = (
                        y_position
                        + (box_height - text_height * len(lines)) // 2
                        + (text_height * j)
                    )

                draw.text((text_x, text_y), line, fill="white", font=font)

    # Nicely formatted text content
    top_boxes_text = [
        ["DIRECTION", f"{angle:.1f} deg(T)"],
        [f"{cord1:.5f}°S", f"{cord2:.5f}°E"],
        ["ACCURACY 10 m", "DATUM WGS84"],
    ]

    bottom_boxes_text = [
        [glocation, component],
        [defect_line1, defect_line2],
        [date_month_year, f"{hour_min_second}+10:00"],
    ]

    # Draw top and bottom boxes
    draw_boxes_with_text(0, top_boxes_text)  # Top boxes
    draw_boxes_with_text(base_height - box_height, bottom_boxes_text)  # Bottom boxes

    # Combine overlay with base image
    with Image.open(image_path) as base_img:
        combined_image = Image.alpha_composite(base_img.convert("RGBA"), overlay_image)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Build filename
    combined_image_name = f"{glocation}_{component}_{defect_line1}_{defect_line2}_{idd}.png"
    combined_image_path = os.path.join(output_folder, combined_image_name)

    combined_image.save(combined_image_path)

    return combined_image_path

def create_partial_overlay_image(
    image_path: str,
    cord1: float,
    cord2: float,
    date_month_year: str,
    hour_min_second: str,
    angle: float,
    glocation: str,
    component: str,
    defect_line1: str,
    defect_line2: str,
    idd: int,
    output_folder: str,
) -> str:
    """Create an overlay with text and save a combined image."""

    # ---- OPEN IMAGE ONCE (SAFE) ----
    base_img = Image.open(image_path)
    base_width, base_height = base_img.size

    # ---- OVERLAY SURFACE ----
    overlay_image = Image.new("RGBA", (base_width, base_height), (255,255,255,0))
    draw = ImageDraw.Draw(overlay_image, "RGBA")

    # ---- STYLING ----
    text_size = int(base_height * 0.035)
    box_height = base_height // 12 - base_height / 240
    transparency = 200
    font = ImageFont.FreeTypeFont(r"C:\Windows\Fonts\CONSOLA.ttf", size=text_size)

    # ---- DRAW ONLY YOUR CUSTOM CONTEXT-AWARE BOX ----
    draw_bottom_left_box(
        overlay_image,
        base_img,        # <-- OPEN IMAGE, NOT CLOSED
        draw,
        base_width,
        base_height,
        box_height,
        font,
        transparency,
        glocation,
        component
    )

    # ---- MERGE LAYERS ----
    combined_image = Image.alpha_composite(base_img.convert("RGBA"), overlay_image)

    # Close base image now that we're done using it
    base_img.close()

    # ---- SAVE ----
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    combined_image_name = f"{glocation}_{component}_{defect_line1}_{defect_line2}_{idd}.png"
    combined_image_path = os.path.join(output_folder, combined_image_name)

    combined_image.save(combined_image_path)

    return combined_image_path


def copy_and_rotate(image_path: str, rotation_angle: int) -> str:
    """
    Copy an image, rotate it, and preserve EXIF data if present.
    Returns the new filename.
    """
    image = Image.open(image_path)

    # Check if the image has EXIF data
    exif_data = image.info.get("exif")

    # Rotate the image
    rotated_image = image.rotate(rotation_angle, expand=True)

    # Create a new filename for the rotated image
    base, ext = os.path.splitext(image_path)
    new_filename = f"{base}_rotated{ext}"

    # Save the rotated image with the original EXIF data (if present)
    if exif_data:
        rotated_image.save(new_filename, "JPEG", exif=exif_data)
    else:
        rotated_image.save(new_filename, "JPEG")

    image.close()
    rotated_image.close()

    return new_filename


# %% engine
def draw_bottom_left_box2(draw, base_width, base_height, box_height, font, transparency,
                         glocation: str, component: str):
    """
    Draws ONLY the bottom-left shaded box containing:
        glocation
        component
    WITHOUT modifying any existing functions.
    """

    # box width = 1/3 of image (you can adjust this)
    box_width = base_width // 3

    x_position = 0
    y_position = base_height - box_height

    # Draw rectangle
    draw.rectangle(
        (x_position, y_position, x_position + box_width, y_position + box_height),
        fill=(0, 0, 0, transparency)
    )

    # Two text lines
    lines = [glocation, component]

    for j, line in enumerate(lines):
        line = "" if line is None else str(line)

        # Measure text
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Center text inside the box
        text_x = x_position + (box_width - text_width) // 2
        text_y = (
            y_position
            + (box_height - text_height * len(lines)) // 2
            + j * text_height
        )

        draw.text((text_x, text_y), line, fill="white", font=font)


if __name__ == "__main__":
    image_path = r"C:\Users\Admin\OneDrive\Documentos\CodingProjects\contextcam_clone\photos\IMG_1061.jpg"
    output_folder = "test"

    info_tuple = get_comments_info(image_path)
    if info_tuple is None:
        raise ValueError("Image does not contain required GPS/DateTime EXIF data.")

    cord1, cord2, date_month_year, hour_min_second, angle = info_tuple

    create_standardized_overlay_image(
        image_path=image_path,
        cord1=cord1,
        cord2=cord2,
        date_month_year=date_month_year,
        hour_min_second=hour_min_second,
        angle=angle,
        glocation="Microcell Building",
        component="Monorail 5024",
        defect_line1="Corrosion and ",
        defect_line2="dmg in PCaaaa",
        idd=3,
        output_folder=output_folder,
    )

from PIL import ImageFilter

from PIL import ImageFilter

def draw_bottom_left_box(
    overlay_image,
    base_img,
    draw,
    base_width,
    base_height,
    box_height,
    font,
    transparency,
    glocation,
    component
):
    """
    Bottom-left overlay box:
    - Blurs the BASE image area first
    - Then draws darkening + gradient on top
    """

    # Ensure integers
    box_height = int(round(box_height))
    x_position = 0
    box_width = base_width // 3
    y_position = base_height - box_height

    max_alpha = max(0, min(int(transparency), 255))

    # --- 1) BLUR THE BASE IMAGE WHERE THE BOX WILL BE ---
    blur_crop = base_img.crop(
        (
            x_position,
            y_position,
            x_position + box_width,
            y_position + box_height,
        )
    ).filter(ImageFilter.GaussianBlur(radius=20))

    # Paste blur BACK onto base image (we modify the base image directly)
    base_img.paste(blur_crop, (x_position, y_position))

    # --- 2) Create a shading alpha mask for 75% solid + 25% fade ---
    mask = Image.new("L", (box_width, box_height), 0)
    mask_pixels = mask.load()

    full_shade_end = int(box_width * 0.75)
    gradient_width = max(1, box_width - full_shade_end)

    for i in range(box_width):
        if i < full_shade_end:
            alpha = max_alpha
        else:
            t = (i - full_shade_end) / gradient_width
            alpha = int(max_alpha * (1 - t))

        for j in range(box_height):
            mask_pixels[i, j] = alpha

    # --- 3) Darkening overlay (black box using the alpha mask) ---
    shade = Image.new("RGBA", (box_width, box_height), (0, 0, 0, 0))
    shade_pixels = shade.load()

    for i in range(box_width):
        for j in range(box_height):
            a = mask_pixels[i, j]
            shade_pixels[i, j] = (0, 0, 0, a)

    # Paste the shaded gradient overlay
    overlay_image.paste(shade, (x_position, y_position), shade)

    # --- 4) Draw text on top of all ---
    lines = [glocation, component]

    for j, line in enumerate(lines):
        line = "" if line is None else str(line)

        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = x_position + (box_width - text_width) // 2
        text_y = y_position + (box_height - text_height*len(lines))//2 + j*text_height

        draw.text((int(text_x), int(text_y)), line, fill="white", font=font)

