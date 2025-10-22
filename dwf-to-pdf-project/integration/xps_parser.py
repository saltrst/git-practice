"""
XPS Parser for DWFX Files (XPS-Only Format)

This module parses XPS FixedPage content from DWFX files that don't contain
W2D binary streams. It extracts vector paths, text glyphs, and converts them
to the same opcode format used by the W2D parser for unified rendering.

Format Support:
- XPS-based DWFX files (Microsoft XPS format)
- Parses FixedPage XML with Path and Glyphs elements
- Converts XPS paths to PDF-compatible coordinate system

Author: Claude Code
Date: October 2025
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import shutil


def parse_xps_color(color_str: str) -> Optional[Tuple[float, float, float]]:
    """
    Parse XPS color string to RGB tuple (0-1 range).

    Supports:
    - #AARRGGBB (8 hex digits with alpha)
    - #RRGGBB (6 hex digits)
    - Transparent (returns None)

    Args:
        color_str: XPS color string (e.g., "#FF0000" for red)

    Returns:
        RGB tuple (r, g, b) in 0-1 range, or None for transparent

    Example:
        >>> parse_xps_color("#FF0000")
        (1.0, 0.0, 0.0)
        >>> parse_xps_color("#80FF0000")  # 50% alpha red
        (1.0, 0.0, 0.0)
    """
    if not color_str or color_str.lower() == 'transparent':
        return None

    color_str = color_str.lstrip('#')

    try:
        if len(color_str) == 8:  # AARRGGBB
            a, r, g, b = [int(color_str[i:i+2], 16) for i in (0, 2, 4, 6)]
        elif len(color_str) == 6:  # RRGGBB
            r, g, b = [int(color_str[i:i+2], 16) for i in (0, 2, 4)]
        else:
            return (0, 0, 0)  # Default to black

        return (r / 255.0, g / 255.0, b / 255.0)
    except ValueError:
        return (0, 0, 0)


def parse_xps_path_data(path_data: str, scale: float = 1.0) -> List[Tuple[float, float]]:
    """
    Parse XPS path data string and extract coordinate points.

    Simplified parsing that extracts numeric coordinates from path commands.
    Full XPS path grammar includes: M (moveto), L (lineto), l (relative lineto),
    H (horizontal), V (vertical), C (cubic bezier), Z (close).

    Args:
        path_data: XPS path data string (e.g., "M100,200 L300,400")
        scale: Scale factor to apply to coordinates

    Returns:
        List of (x, y) coordinate tuples

    Example:
        >>> parse_xps_path_data("M100,200 L300,400", scale=0.1)
        [(10.0, 20.0), (30.0, 40.0)]
    """
    if not path_data:
        return []

    # Extract all numeric values (including negative and decimals)
    coords = re.findall(r'-?\d+\.?\d*', path_data)

    # Convert to floats and apply scale
    points = []
    for i in range(0, len(coords) - 1, 2):
        try:
            x = float(coords[i]) * scale
            y = float(coords[i + 1]) * scale
            points.append((x, y))
        except (ValueError, IndexError):
            continue

    return points


def parse_xps_page(fpage_path: str) -> Dict:
    """
    Parse XPS FixedPage XML file and extract graphics elements.

    Extracts:
    - Path elements (vector graphics)
    - Glyphs elements (text)
    - Canvas elements (containers)
    - Page dimensions

    Args:
        fpage_path: Path to .fpage XML file

    Returns:
        Dictionary with:
        - 'paths': List of path dictionaries
        - 'glyphs': List of text glyph dictionaries
        - 'width': Page width in XPS units
        - 'height': Page height in XPS units

    Example:
        >>> page_data = parse_xps_page("FixedPage.fpage")
        >>> print(f"Page: {page_data['width']}x{page_data['height']}")
        >>> print(f"Paths: {len(page_data['paths'])}")
    """
    tree = ET.parse(fpage_path)
    root = tree.getroot()

    paths = []
    glyphs = []

    # XPS namespace
    ns = {'xps': 'http://schemas.microsoft.com/xps/2005/06'}

    # Iterate through all elements
    for elem in root.iter():
        # Strip namespace from tag
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        if tag == 'Path':
            path_data = {
                'type': 'path',
                'data': elem.attrib.get('Data', ''),
                'fill': elem.attrib.get('Fill', ''),
                'stroke': elem.attrib.get('Stroke', ''),
                'stroke_thickness': elem.attrib.get('StrokeThickness', '1'),
                'opacity': elem.attrib.get('Opacity', '1.0'),
                'name': elem.attrib.get('Name', '')
            }
            if path_data['data']:  # Only include paths with data
                paths.append(path_data)

        elif tag == 'Glyphs':
            glyph_data = {
                'type': 'text',
                'unicode_string': elem.attrib.get('UnicodeString', ''),
                'origin_x': elem.attrib.get('OriginX', '0'),
                'origin_y': elem.attrib.get('OriginY', '0'),
                'fill': elem.attrib.get('Fill', '#000000'),
                'font_size': elem.attrib.get('FontRenderingEmSize', '12'),
                'font_uri': elem.attrib.get('FontUri', '')
            }
            if glyph_data['unicode_string']:  # Only include non-empty text
                glyphs.append(glyph_data)

    # Extract page dimensions
    width = float(root.attrib.get('Width', '612'))
    height = float(root.attrib.get('Height', '792'))

    return {
        'paths': paths,
        'glyphs': glyphs,
        'width': width,
        'height': height
    }


def xps_to_w2d_opcodes(page_data: Dict, scale: float = 0.1) -> List[Dict]:
    """
    Convert XPS page data to W2D-style opcodes for unified rendering.

    Converts XPS paths and glyphs to the same opcode format that the W2D
    parser produces, allowing the same PDF renderer to handle both formats.

    Args:
        page_data: Parsed XPS page data from parse_xps_page()
        scale: Scale factor to apply to coordinates (default 0.1)

    Returns:
        List of opcode dictionaries compatible with pdf_renderer_v1

    Example:
        >>> page_data = parse_xps_page("FixedPage.fpage")
        >>> opcodes = xps_to_w2d_opcodes(page_data, scale=0.1)
        >>> len(opcodes)
        4192
    """
    opcodes = []

    # Convert paths to polyline opcodes
    for path in page_data['paths']:
        # Parse path data to extract points
        points = parse_xps_path_data(path['data'], scale=scale)

        if not points:
            continue

        # Parse colors
        fill_color = parse_xps_color(path['fill'])
        stroke_color = parse_xps_color(path['stroke'])

        # Set color if available
        if fill_color:
            opcodes.append({
                'type': 'set_color_rgb',
                'r': fill_color[0],
                'g': fill_color[1],
                'b': fill_color[2],
                'opcode': 0x0A,  # Set color RGB opcode
                'opcode_name': 'SET_COLOR_RGB'
            })

        # Create polyline/polygon opcode
        if len(points) >= 2:
            opcodes.append({
                'type': 'polyline_polygon_16r',
                'points': points,
                'count': len(points),
                'opcode': 0x10,
                'opcode_name': 'DRAW_POLYLINE_POLYGON_16R',
                'relative': False,  # XPS uses absolute coordinates
                'fill': fill_color is not None,
                'stroke': stroke_color is not None
            })

    # Convert glyphs to text opcodes
    for glyph in page_data['glyphs']:
        try:
            x = float(glyph['origin_x']) * scale
            y = float(glyph['origin_y']) * scale
            text = glyph['unicode_string']
            font_size = float(glyph['font_size']) * scale

            color = parse_xps_color(glyph['fill'])
            if color:
                opcodes.append({
                    'type': 'set_color_rgb',
                    'r': color[0],
                    'g': color[1],
                    'b': color[2],
                    'opcode': 0x0A,
                    'opcode_name': 'SET_COLOR_RGB'
                })

            opcodes.append({
                'type': 'text',
                'text': text,
                'x': x,
                'y': y,
                'font_size': font_size,
                'opcode': 0x50,  # Text opcode
                'opcode_name': 'TEXT'
            })
        except ValueError:
            continue

    return opcodes


def parse_xps_dwfx(file_path: str) -> List[Dict]:
    """
    Parse XPS-based DWFX file and extract all pages as opcodes.

    Main entry point for XPS parsing. Extracts ZIP, finds FixedPage files,
    parses each page, and converts to opcode format.

    Args:
        file_path: Path to DWFX file

    Returns:
        List of opcode dictionaries compatible with pdf_renderer_v1

    Raises:
        FileNotFoundError: If DWFX file doesn't exist
        ValueError: If no FixedPage files found

    Example:
        >>> opcodes = parse_xps_dwfx("drawing.dwfx")
        >>> print(f"Parsed {len(opcodes)} opcodes from XPS")
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"DWFX file not found: {file_path}")

    # Create temp extraction directory
    extract_dir = Path(f"_temp_xps_{file_path.stem}")

    try:
        # Extract DWFX (it's a ZIP file)
        with zipfile.ZipFile(file_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Find all FixedPage files
        fpage_files = sorted(extract_dir.rglob("*.fpage"))

        if not fpage_files:
            raise ValueError(f"No XPS FixedPage files found in {file_path}")

        # Parse all pages and collect opcodes
        all_opcodes = []

        for page_idx, fpage_file in enumerate(fpage_files):
            # Parse XPS page
            page_data = parse_xps_page(str(fpage_file))

            # Calculate scale factor based on page dimensions
            # XPS uses much larger coordinate space than PDF
            page_width = page_data['width']
            page_height = page_data['height']

            # Target PDF page size (letter: 612x792 points)
            target_width = 612
            target_height = 792

            # Calculate scale to fit
            scale_x = target_width / page_width if page_width > 0 else 0.1
            scale_y = target_height / page_height if page_height > 0 else 0.1
            scale = min(scale_x, scale_y)

            # Convert to opcodes
            page_opcodes = xps_to_w2d_opcodes(page_data, scale=scale)

            # Add page break marker if not first page
            if page_idx > 0:
                all_opcodes.append({
                    'type': 'page_break',
                    'opcode': 0xFF,
                    'opcode_name': 'PAGE_BREAK'
                })

            all_opcodes.extend(page_opcodes)

        return all_opcodes

    finally:
        # Cleanup temp directory
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


def is_xps_dwfx(file_path: str) -> bool:
    """
    Check if a DWFX file contains XPS FixedPage content.

    Args:
        file_path: Path to DWFX file

    Returns:
        True if file contains .fpage files, False otherwise

    Example:
        >>> is_xps_dwfx("1.dwfx")
        True
        >>> is_xps_dwfx("3.dwf")
        False
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            return any(name.endswith('.fpage') for name in zf.namelist())
    except (zipfile.BadZipFile, FileNotFoundError):
        return False


# Module version
__version__ = "1.0.0"
__author__ = "Claude Code"
__description__ = "XPS parser for DWFX files (XPS-only format)"
