"""
Direct XPS to PDF Converter - No Intermediate Translation

This module renders XPS FixedPage content directly to PDF using ReportLab.
No opcode translation layer - just parse XPS XML and render immediately.

Why this approach:
- XPS is already structured XML with paths and glyphs
- No need to translate to fake "opcodes"
- Direct rendering is simpler, faster, and more accurate
- Preserves exact page dimensions from XPS (96 DPI → 72 DPI conversion)

Author: Claude Code
Date: October 2025
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import shutil

from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color


def parse_xps_color(color_str: str) -> Optional[Color]:
    """
    Parse XPS color string to ReportLab Color object.

    Args:
        color_str: XPS color (#AARRGGBB or #RRGGBB or 'Transparent')

    Returns:
        ReportLab Color object or None for transparent
    """
    if not color_str or color_str.lower() == 'transparent':
        return None

    color_str = color_str.lstrip('#')

    try:
        if len(color_str) == 8:  # AARRGGBB
            a, r, g, b = [int(color_str[i:i+2], 16) for i in (0, 2, 4, 6)]
        elif len(color_str) == 6:  # RRGGBB
            r, g, b = [int(color_str[i:i+2], 16) for i in (0, 2, 4)]
            a = 255
        else:
            return Color(0, 0, 0)  # Default to black

        return Color(r/255.0, g/255.0, b/255.0, alpha=a/255.0)
    except ValueError:
        return Color(0, 0, 0)


def convert_xps_path_to_pdf(canvas_obj, path_data: str, x_offset: float = 0, y_offset: float = 0):
    """
    Convert XPS path data to PDF path commands and draw on canvas.

    XPS uses SVG-like path syntax:
    - M x,y: Move to absolute position
    - L x,y: Line to absolute position
    - l dx,dy: Line to relative position
    - H x: Horizontal line to x
    - V y: Vertical line to y
    - Z/z: Close path

    Args:
        canvas_obj: ReportLab canvas object
        path_data: XPS path Data attribute (e.g., "M 0,0 L 100,100 z")
        x_offset: X offset to apply to all coordinates
        y_offset: Y offset to apply to all coordinates
    """
    if not path_data:
        return

    # Start a new path
    path = canvas_obj.beginPath()

    # Parse path commands
    # Split on command letters while keeping them
    tokens = re.split(r'([MLHVZzlhv])', path_data)
    tokens = [t.strip() for t in tokens if t.strip()]

    current_x, current_y = 0.0, 0.0
    i = 0

    while i < len(tokens):
        cmd = tokens[i]
        i += 1

        # Get coordinates for this command
        coords = []
        if i < len(tokens) and tokens[i] not in 'MLHVZzlhv':
            # Extract numbers from coordinate string
            coord_str = tokens[i]
            # Match numbers including decimals and negatives
            numbers = re.findall(r'-?\d+(?:\.\d+)?', coord_str)
            coords = [float(n) for n in numbers]
            i += 1

        # Execute command
        if cmd == 'M' and len(coords) >= 2:
            # Move to absolute
            current_x, current_y = coords[0] + x_offset, coords[1] + y_offset
            path.moveTo(current_x, current_y)

        elif cmd == 'm' and len(coords) >= 2:
            # Move to relative
            current_x += coords[0]
            current_y += coords[1]
            path.moveTo(current_x, current_y)

        elif cmd == 'L' and len(coords) >= 2:
            # Line to absolute
            current_x, current_y = coords[0] + x_offset, coords[1] + y_offset
            path.lineTo(current_x, current_y)

        elif cmd == 'l' and len(coords) >= 2:
            # Line to relative
            current_x += coords[0]
            current_y += coords[1]
            path.lineTo(current_x, current_y)

        elif cmd == 'H' and len(coords) >= 1:
            # Horizontal line to absolute x
            current_x = coords[0] + x_offset
            path.lineTo(current_x, current_y)

        elif cmd == 'h' and len(coords) >= 1:
            # Horizontal line to relative x
            current_x += coords[0]
            path.lineTo(current_x, current_y)

        elif cmd == 'V' and len(coords) >= 1:
            # Vertical line to absolute y
            current_y = coords[0] + y_offset
            path.lineTo(current_x, current_y)

        elif cmd == 'v' and len(coords) >= 1:
            # Vertical line to relative y
            current_y += coords[0]
            path.lineTo(current_x, current_y)

        elif cmd in 'Zz':
            # Close path
            path.close()

    return path


def render_xps_page_to_pdf(canvas_obj, fpage_path: str):
    """
    Render a single XPS FixedPage directly to PDF canvas.

    Args:
        canvas_obj: ReportLab canvas object
        fpage_path: Path to .fpage XML file
    """
    # Parse XPS page XML
    tree = ET.parse(fpage_path)
    root = tree.getroot()

    # Get page dimensions (XPS uses 96 DPI, PDF uses 72 DPI)
    page_width = float(root.attrib.get('Width', 612))
    page_height = float(root.attrib.get('Height', 792))

    # Convert XPS units (96 DPI) to PDF points (72 DPI)
    scale = 72.0 / 96.0  # 0.75

    # Iterate through all elements
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        if tag == 'Path':
            # Get path attributes
            path_data = elem.attrib.get('Data', '')
            fill_str = elem.attrib.get('Fill', '')
            stroke_str = elem.attrib.get('Stroke', '')
            stroke_thickness = float(elem.attrib.get('StrokeThickness', '1'))

            if not path_data:
                continue

            # Parse colors
            fill_color = parse_xps_color(fill_str)
            stroke_color = parse_xps_color(stroke_str)

            # Convert path data to PDF path
            path = convert_xps_path_to_pdf(canvas_obj, path_data)

            if path:
                # Set line width
                canvas_obj.setLineWidth(stroke_thickness * scale)

                # Draw path
                if fill_color and stroke_color:
                    canvas_obj.setFillColor(fill_color)
                    canvas_obj.setStrokeColor(stroke_color)
                    canvas_obj.drawPath(path, stroke=1, fill=1)
                elif fill_color:
                    canvas_obj.setFillColor(fill_color)
                    canvas_obj.drawPath(path, stroke=0, fill=1)
                elif stroke_color:
                    canvas_obj.setStrokeColor(stroke_color)
                    canvas_obj.drawPath(path, stroke=1, fill=0)

        elif tag == 'Glyphs':
            # Get text attributes
            unicode_str = elem.attrib.get('UnicodeString', '')
            origin_x = float(elem.attrib.get('OriginX', '0'))
            origin_y = float(elem.attrib.get('OriginY', '0'))
            font_size = float(elem.attrib.get('FontRenderingEmSize', '12'))
            fill_str = elem.attrib.get('Fill', '#000000')

            if unicode_str:
                # Parse color
                text_color = parse_xps_color(fill_str)

                # Convert coordinates (flip Y axis for PDF)
                pdf_x = origin_x * scale
                pdf_y = (page_height - origin_y) * scale
                pdf_font_size = font_size * scale

                # Draw text
                if text_color:
                    canvas_obj.setFillColor(text_color)
                canvas_obj.setFont('Helvetica', pdf_font_size)
                canvas_obj.drawString(pdf_x, pdf_y, unicode_str)


def convert_xps_dwfx_to_pdf_direct(dwfx_path: str, pdf_path: str, verbose: bool = False) -> bool:
    """
    Convert XPS-based DWFX file directly to PDF.
    No intermediate opcode translation - direct XPS to PDF rendering.

    Args:
        dwfx_path: Path to DWFX file
        pdf_path: Path to output PDF file
        verbose: Print progress messages

    Returns:
        True if successful, False otherwise
    """
    dwfx_path = Path(dwfx_path)

    if not dwfx_path.exists():
        if verbose:
            print(f"❌ Error: File not found: {dwfx_path}")
        return False

    # Create temp extraction directory
    extract_dir = Path(f"_temp_xps_direct_{dwfx_path.stem}")

    try:
        if verbose:
            print(f"📦 Extracting DWFX archive...")

        # Extract DWFX (it's a ZIP file)
        with zipfile.ZipFile(dwfx_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Find all FixedPage files
        fpage_files = sorted(extract_dir.rglob("*.fpage"))

        if not fpage_files:
            if verbose:
                print(f"❌ No XPS FixedPage files found in {dwfx_path}")
            return False

        if verbose:
            print(f"📄 Found {len(fpage_files)} page(s)")

        # Get dimensions of first page
        tree = ET.parse(fpage_files[0])
        root = tree.getroot()
        page_width = float(root.attrib.get('Width', 612))
        page_height = float(root.attrib.get('Height', 792))

        # Convert XPS units (96 DPI) to PDF points (72 DPI)
        scale = 72.0 / 96.0
        pdf_width = page_width * scale
        pdf_height = page_height * scale

        if verbose:
            print(f"📐 Page size: {pdf_width:.1f} x {pdf_height:.1f} pts ({pdf_width/72:.2f}\" x {pdf_height/72:.2f}\")")

        # Create PDF canvas
        c = canvas.Canvas(pdf_path, pagesize=(pdf_width, pdf_height))

        # Render each page
        for page_idx, fpage_file in enumerate(fpage_files):
            if verbose:
                print(f"🎨 Rendering page {page_idx + 1}/{len(fpage_files)}...")

            # Render this page
            render_xps_page_to_pdf(c, str(fpage_file))

            # Show page (finalize it)
            if page_idx < len(fpage_files) - 1:
                c.showPage()

        # Save PDF
        c.save()

        if verbose:
            import os
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)
            print(f"✅ Success! Created {pdf_path} ({file_size:.2f} MB)")

        return True

    except Exception as e:
        if verbose:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        return False

    finally:
        # Cleanup temp directory
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


# Module metadata
__version__ = "1.0.0"
__author__ = "Claude Code"
__description__ = "Direct XPS to PDF converter (no opcode translation)"
