import os
from typing import Tuple
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from _testing_image_overlay import create_standardized_overlay_image,get_comments_info,copy_and_rotate, create_partial_overlay_image
import pandas as pd
from PIL import Image, ExifTags
import numpy as np
from PIL import Image
import piexif
from pillow_heif import register_heif_opener

# Register HEIC support
register_heif_opener()

def convert_heic_to_jpg(image_path):
    """
    Converts a HEIC image to JPG while preserving metadata and quality.
    Returns the path to the new JPG file.
    """
    try:
        print(f"Opening file: {image_path}")
        with Image.open(image_path) as img:
            print('Inside function: Image opened successfully')

            # Extract metadata
            exif_data = img.info.get('exif')
            print(f"EXIF data extracted: {exif_data is not None}")

            # Prepare new file path
            jpg_path = os.path.splitext(image_path)[0] + '.jpg'
            print(f"Saving file as: {jpg_path}")

            # Save as JPG with the original quality and metadata
            if exif_data:
                img.save(jpg_path, 'JPEG', quality=100, exif=exif_data)
            else:
                img.save(jpg_path, 'JPEG', quality=100)

            print(f"File saved successfully at {jpg_path}")
            return jpg_path

    except Exception as e:
        print(f"Error converting {image_path}: {e}")



def get_image_rotation(image_path):
    # Open the image file
    with Image.open(image_path) as img:
        # Get the EXIF data
        exif = img._getexif()
        
        if exif:
            # Get the orientation tag code
            for tag, value in ExifTags.TAGS.items():
                if value == 'Orientation':
                    orientation_tag = tag
                    break
            
            # Get the orientation value
            orientation = exif.get(orientation_tag, None)
            
            # Map the orientation value to rotation angle
            rotation_map = {
                1: 0,    # Horizontal (normal)
                3: 180,  # Upside-down
                6: 270,  # Rotated 90° CW
                8: 90    # Rotated 90° CCW
            }
            
            rotation_angle = rotation_map.get(orientation, 0)
            return rotation_angle
        else:
            return "No EXIF data found"


def scan_and_write_excel(directory: str, excel_path: str) -> None:
    """
    Scans a directory for JPG and HEIC images, converts HEIC to JPG,
    writes the paths and rotation info to an Excel file along with empty columns for additional data.
    """
    wb = Workbook()
    ws = wb.active

    columns = ['image_path', 'glocation', 'component', 'defect_line1', 'defect_line2', 'idd', 'rotation']
    ws.append(columns)

    for file in os.listdir(directory):
        print(file)
        file_lower = file.lower()
        image_path = os.path.join(directory, file)

        # Convert HEIC to JPG
        if file_lower.endswith('.heic'):
            image_path = convert_heic_to_jpg(image_path)

        # Process JPG files
        if image_path.lower().endswith('.jpg'):
            rotation = get_image_rotation(image_path)
            ws.append([image_path, '', '', '', '', '', rotation])
        
        # Process JPG files
        if image_path.lower().endswith('.jpeg'):
            rotation = get_image_rotation(image_path)
            ws.append([image_path, '', '', '', '', '', rotation])

    wb.save(excel_path)

def process_images_from_excel(excel_path: str,output_folder:str) -> None:
    """
    Reads the Excel file and processes each image using the provided details.
    """
    # Load the Excel file
    df = pd.read_excel(excel_path)

    for index, row in df.iterrows():
        image_path = row['image_path']
        # Assuming get_comments_info is defined elsewhere and available
        cord1, cord2, date_month_year, hour_min_second, angle = get_comments_info(image_path)
        
        # Call the function with the data from the Excel and the extracted information
        create_standardized_overlay_image(image_path,
                                          cord1=cord1,
                                          cord2=cord2,
                                          date_month_year=date_month_year,
                                          hour_min_second=hour_min_second,
                                          angle=angle,
                                          glocation=row['glocation'],
                                          component=row['component'],
                                          defect_line1=row['defect_line1'],
                                          defect_line2=row['defect_line2'],
                                          idd=row['idd'],
                                          output_folder = output_folder)



def process_images_from_excel_with_rotation(excel_path: str,output_folder:str) -> None:
    """
    Reads the Excel file and processes each image using the provided details.
    """
    # Load the Excel file
    df = pd.read_excel(excel_path)

    for index, row in df.iterrows():
        image_path = row['image_path']
        # Assuming get_comments_info is defined elsewhere and available
        if row['rotation'] != 0:
            image_path = copy_and_rotate(image_path,row['rotation'])
            print('path' ,image_path)
        try:
            cord1, cord2, date_month_year, hour_min_second, angle = get_comments_info(image_path)
        except:
            cord1, cord2, date_month_year, hour_min_second, angle = 32.25315, 115.76708, '2024:06:12', '2024:06:12', -75

        # Call the function with the data from the Excel and the extracted information
        create_standardized_overlay_image(image_path,
                                          cord1=cord1,
                                          cord2=cord2,
                                          date_month_year=date_month_year,
                                          hour_min_second=hour_min_second,
                                          angle=angle,
                                          glocation=row['glocation'],
                                          component=row['component'],
                                          defect_line1=row['defect_line1'],
                                          defect_line2=row['defect_line2'],
                                          idd=row['idd'],
                                          output_folder = output_folder)


def process_partial_images_from_excel_with_rotation(excel_path: str,output_folder:str) -> None:
    """
    Reads the Excel file and processes each image using the provided details.
    """
    # Load the Excel file
    df = pd.read_excel(excel_path)

    for index, row in df.iterrows():
        image_path = row['image_path']
        # Assuming get_comments_info is defined elsewhere and available
        if row['rotation'] != 0:
            image_path = copy_and_rotate(image_path,row['rotation'])
            print('path' ,image_path)
        try:
            cord1, cord2, date_month_year, hour_min_second, angle = get_comments_info(image_path)
        except:
            cord1, cord2, date_month_year, hour_min_second, angle = 32.25315, 115.76708, '2024:06:12', '2024:06:12', -75

        # Call the function with the data from the Excel and the extracted information
        create_partial_overlay_image(image_path,
                                          cord1=cord1,
                                          cord2=cord2,
                                          date_month_year=date_month_year,
                                          hour_min_second=hour_min_second,
                                          angle=angle,
                                          glocation=row['glocation'],
                                          component=row['component'],
                                          defect_line1=row['defect_line1'],
                                          defect_line2=row['defect_line2'],
                                          idd=row['idd'],
                                          output_folder = output_folder)
# Example usage
if __name__ == '__main__':
    directory = r"C:\Users\Admin\OneDrive\Documentos\CodingProjects\contextcam_clone\belt_filter"
    excel_path = r"defects4.xlsx"
    #scan_and_write_excel(directory, excel_path)
    #process_images_from_excel_with_rotation(excel_path,output_folder=r"results")
    process_partial_images_from_excel_with_rotation(excel_path,output_folder=r"partial_results")
