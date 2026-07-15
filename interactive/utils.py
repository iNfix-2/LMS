import os
import zipfile
import xml.etree.ElementTree as ET
from django.conf import settings

def extract_and_parse_package(interactive_content):
    """
    Extracts the uploaded SCORM/H5P zip package to a directory inside media/extracted_packages/
    and for SCORM packages, parses the imsmanifest.xml to find the launch entry point.
    """
    if not interactive_content.package_file:
        return

    # Create destination directory
    package_name = os.path.basename(interactive_content.package_file.name)
    base_name, _ = os.path.splitext(package_name)
    
    extracted_rel_path = os.path.join('extracted_packages', f"lesson_{interactive_content.lesson.id}_{base_name}")
    extracted_abs_path = os.path.join(settings.MEDIA_ROOT, extracted_rel_path)
    
    os.makedirs(extracted_abs_path, exist_ok=True)
    
    # Extract zip file
    with zipfile.ZipFile(interactive_content.package_file.path, 'r') as zip_ref:
        zip_ref.extractall(extracted_abs_path)
        
    interactive_content.extracted_dir = extracted_rel_path
    
    # For SCORM, parse manifest
    if interactive_content.content_type == 'scorm':
        manifest_path = os.path.join(extracted_abs_path, 'imsmanifest.xml')
        if os.path.exists(manifest_path):
            try:
                tree = ET.parse(manifest_path)
                root = tree.getroot()
                
                # Check for standard resource tag
                launch_href = None
                for elem in root.iter():
                    if elem.tag.endswith('resource') and 'href' in elem.attrib:
                        launch_href = elem.attrib['href']
                        break
                
                if launch_href:
                    interactive_content.launch_path = launch_href
            except Exception as e:
                print("Failed to parse imsmanifest.xml:", e)
                
        # Fallback default
        if not interactive_content.launch_path:
            interactive_content.launch_path = 'index.html'
            
    interactive_content.save()
