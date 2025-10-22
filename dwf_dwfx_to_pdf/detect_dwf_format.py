#!/usr/bin/env python3
"""
DWF/DWFX Format Detector
Determines if a file is compatible with the XPS-based converter
"""

import zipfile
import sys
from pathlib import Path


def detect_dwf_format(file_path: str) -> dict:
    """
    Detect DWF/DWFX file format and compatibility
    
    Returns:
        dict with format information and compatibility status
    """
    result = {
        "file": file_path,
        "is_zip": False,
        "format": "unknown",
        "has_xps_pages": False,
        "has_w2d_files": False,
        "has_xml_files": False,
        "compatible_with_converter": False,
        "files_found": [],
        "reason": ""
    }
    
    try:
        # Check if it's a ZIP file
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            result["is_zip"] = True
            file_list = zip_ref.namelist()
            result["files_found"] = file_list[:20]  # First 20 files
            
            # Check for XPS pages (.fpage)
            fpage_files = [f for f in file_list if f.endswith('.fpage')]
            if fpage_files:
                result["has_xps_pages"] = True
                result["format"] = "DWFX (XPS-based)"
                result["compatible_with_converter"] = True
                result["reason"] = f"Found {len(fpage_files)} XPS page(s)"
            
            # Check for W2D binary files
            w2d_files = [f for f in file_list if f.endswith('.w2d')]
            if w2d_files:
                result["has_w2d_files"] = True
                if not result["has_xps_pages"]:
                    result["format"] = "DWF (W2D binary)"
                    result["compatible_with_converter"] = False
                    result["reason"] = f"Found {len(w2d_files)} W2D binary file(s) - NOT SUPPORTED"
            
            # Check for XML files
            xml_files = [f for f in file_list if f.endswith('.xml')]
            if xml_files:
                result["has_xml_files"] = True
            
            # Determine final compatibility
            if not result["has_xps_pages"] and result["has_w2d_files"]:
                result["compatible_with_converter"] = False
                result["reason"] = "W2D binary format requires different parser"
            elif not result["has_xps_pages"] and result["has_xml_files"]:
                result["format"] = "DWF (XML variant)"
                result["compatible_with_converter"] = False
                result["reason"] = "Legacy DWF XML format - untested compatibility"
                
    except zipfile.BadZipFile:
        result["reason"] = "Not a valid ZIP file"
    except Exception as e:
        result["reason"] = f"Error: {str(e)}"
    
    return result


def print_detection_result(result: dict):
    """Print formatted detection result"""
    print(f"\n{'='*60}")
    print(f"DWF/DWFX Format Detection")
    print(f"{'='*60}")
    print(f"File: {result['file']}")
    print(f"Format: {result['format']}")
    print(f"")
    print(f"Contents:")
    print(f"  ZIP archive: {'✅' if result['is_zip'] else '❌'}")
    print(f"  XPS pages (.fpage): {'✅' if result['has_xps_pages'] else '❌'}")
    print(f"  W2D binary (.w2d): {'✅' if result['has_w2d_files'] else '❌'}")
    print(f"  XML files: {'✅' if result['has_xml_files'] else '❌'}")
    print(f"")
    
    if result['compatible_with_converter']:
        print(f"✅ COMPATIBLE with dwfx_to_pdf.py converter")
    else:
        print(f"❌ NOT COMPATIBLE with dwfx_to_pdf.py converter")
    
    print(f"")
    print(f"Reason: {result['reason']}")
    
    if result['files_found']:
        print(f"")
        print(f"Files in archive (first 20):")
        for f in result['files_found'][:20]:
            print(f"  - {f}")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
DWF/DWFX Format Detector

Usage:
    python detect_format.py <file.dwfx>

This tool checks if a DWF/DWFX file is compatible with
the XPS-based converter (dwfx_to_pdf.py).
""")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    result = detect_dwf_format(file_path)
    print_detection_result(result)
    
    sys.exit(0 if result['compatible_with_converter'] else 1)
