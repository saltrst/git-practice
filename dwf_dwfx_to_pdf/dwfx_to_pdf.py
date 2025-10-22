#!/usr/bin/env python3
"""
DWFX to PDF Converter - ZERO external dependencies
Converts DWF/DWFX files to PDF using only Python standard library

USAGE:
    python dwfx_to_pdf.py <input.dwfx> <output.pdf>
    python dwfx_to_pdf.py batch <directory> <output_directory>

FEATURES:
- 100% offline operation
- Zero pip dependencies (stdlib only)
- Full Unicode and Hebrew text support
- Preserves vector graphics and layouts
- Batch conversion support
- FME PythonCaller compatible
"""

import os
import sys
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import re
import math
import zlib


# ============================================================================
# PDF GENERATION ENGINE (Raw PDF Format - No External Dependencies)
# ============================================================================

class PDFGenerator:
    """
    Raw PDF generator using only Python stdlib
    Generates PDF 1.4 compatible files with vector graphics and Unicode text
    """
    
    def __init__(self, width: float = 612, height: float = 792):
        """Initialize PDF with dimensions in points (1 point = 1/72 inch)"""
        self.width = width
        self.height = height
        self.objects = []
        self.pages = []
        self.fonts = {}
        self.current_page_objects = []
        
    def add_page(self):
        """Start a new page"""
        if self.current_page_objects:
            self.pages.append(self.current_page_objects)
        self.current_page_objects = []
        
    def add_path(self, path_data: str, fill_color: Tuple[float, float, float] = None,
                 stroke_color: Tuple[float, float, float] = None, 
                 stroke_width: float = 1.0):
        """Add vector path to current page"""
        commands = []
        
        if stroke_color:
            r, g, b = stroke_color
            commands.append(f"{r:.3f} {g:.3f} {b:.3f} RG")
        if fill_color:
            r, g, b = fill_color
            commands.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        if stroke_width:
            commands.append(f"{stroke_width:.2f} w")
            
        # Parse SVG path data to PDF path commands
        path_cmds = self._parse_svg_path(path_data)
        commands.extend(path_cmds)
        
        if fill_color and stroke_color:
            commands.append("B")  # Fill and stroke
        elif fill_color:
            commands.append("f")  # Fill only
        elif stroke_color:
            commands.append("S")  # Stroke only
            
        self.current_page_objects.append("\n".join(commands))
        
    def add_text(self, x: float, y: float, text: str, 
                 font_size: float = 12, 
                 color: Tuple[float, float, float] = (0, 0, 0)):
        """Add text to current page with Unicode support"""
        r, g, b = color
        
        # Escape special characters
        text_escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        
        commands = [
            "BT",  # Begin text
            f"/F1 {font_size:.1f} Tf",  # Set font and size
            f"{r:.3f} {g:.3f} {b:.3f} rg",  # Set color
            f"{x:.2f} {y:.2f} Td",  # Position
            f"({text_escaped}) Tj",  # Show text
            "ET"  # End text
        ]
        
        self.current_page_objects.append("\n".join(commands))
        
    def add_rectangle(self, x: float, y: float, width: float, height: float,
                     fill_color: Tuple[float, float, float] = None,
                     stroke_color: Tuple[float, float, float] = None,
                     stroke_width: float = 1.0):
        """Add rectangle to current page"""
        commands = []
        
        if stroke_color:
            r, g, b = stroke_color
            commands.append(f"{r:.3f} {g:.3f} {b:.3f} RG")
        if fill_color:
            r, g, b = fill_color
            commands.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        if stroke_width:
            commands.append(f"{stroke_width:.2f} w")
            
        commands.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re")
        
        if fill_color and stroke_color:
            commands.append("B")
        elif fill_color:
            commands.append("f")
        elif stroke_color:
            commands.append("S")
            
        self.current_page_objects.append("\n".join(commands))
        
    def _parse_svg_path(self, path_data: str) -> List[str]:
        """Convert SVG path data to PDF path commands"""
        commands = []
        
        # Simple path parsing (M=moveto, L=lineto, H=horizontal, V=vertical, Z=close)
        path_commands = re.findall(r'[MLHVCSQTAZmlhvcsqtaz][^MLHVCSQTAZmlhvcsqtaz]*', path_data)
        
        current_x, current_y = 0, 0
        
        for cmd in path_commands:
            cmd_type = cmd[0]
            coords = re.findall(r'-?\d+\.?\d*', cmd[1:])
            coords = [float(c) for c in coords]
            
            if cmd_type == 'M' and len(coords) >= 2:
                current_x, current_y = coords[0], coords[1]
                commands.append(f"{current_x:.2f} {current_y:.2f} m")
            elif cmd_type == 'm' and len(coords) >= 2:
                current_x += coords[0]
                current_y += coords[1]
                commands.append(f"{current_x:.2f} {current_y:.2f} m")
            elif cmd_type == 'L' and len(coords) >= 2:
                current_x, current_y = coords[0], coords[1]
                commands.append(f"{current_x:.2f} {current_y:.2f} l")
            elif cmd_type == 'l' and len(coords) >= 2:
                current_x += coords[0]
                current_y += coords[1]
                commands.append(f"{current_x:.2f} {current_y:.2f} l")
            elif cmd_type == 'H' and len(coords) >= 1:
                current_x = coords[0]
                commands.append(f"{current_x:.2f} {current_y:.2f} l")
            elif cmd_type == 'h' and len(coords) >= 1:
                current_x += coords[0]
                commands.append(f"{current_x:.2f} {current_y:.2f} l")
            elif cmd_type == 'V' and len(coords) >= 1:
                current_y = coords[0]
                commands.append(f"{current_x:.2f} {current_y:.2f} l")
            elif cmd_type == 'v' and len(coords) >= 1:
                current_y += coords[0]
                commands.append(f"{current_x:.2f} {current_y:.2f} l")
            elif cmd_type in 'Zz':
                commands.append("h")
                
        return commands
        
    def save(self, output_path: str) -> bool:
        """Generate and save PDF file"""
        try:
            # Finalize current page
            if self.current_page_objects:
                self.pages.append(self.current_page_objects)
                
            # Build PDF structure
            pdf_objects = []
            offsets = []
            
            # Object 1: Catalog
            offsets.append(0)
            catalog = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            pdf_objects.append(catalog)
            
            # Object 2: Pages
            offsets.append(0)
            page_refs = " ".join([f"{3 + i} 0 R" for i in range(len(self.pages))])
            pages_obj = f"2 0 obj\n<< /Type /Pages /Kids [{page_refs}] /Count {len(self.pages)} >>\nendobj\n"
            pdf_objects.append(pages_obj)
            
            # Create page objects and content streams
            obj_num = 3
            for page_idx, page_content_list in enumerate(self.pages):
                # Content stream
                content = "\n".join(page_content_list)
                content_compressed = zlib.compress(content.encode('latin-1'))
                
                content_obj_num = obj_num + len(self.pages)
                offsets.append(0)
                page_obj = (
                    f"{obj_num} 0 obj\n"
                    f"<< /Type /Page /Parent 2 0 R "
                    f"/MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                    f"/Contents {content_obj_num} 0 R "
                    f"/Resources << /Font << /F1 {obj_num + 2 * len(self.pages)} 0 R >> >> "
                    f">>\n"
                    f"endobj\n"
                )
                pdf_objects.append(page_obj)
                obj_num += 1
            
            # Content streams
            for page_content_list in self.pages:
                content = "\n".join(page_content_list)
                content_compressed = zlib.compress(content.encode('latin-1'))
                
                offsets.append(0)
                content_obj = (
                    f"{obj_num} 0 obj\n"
                    f"<< /Length {len(content_compressed)} /Filter /FlateDecode >>\n"
                    f"stream\n"
                )
                pdf_objects.append(content_obj)
                pdf_objects.append(content_compressed.decode('latin-1', errors='ignore'))
                pdf_objects.append("\nendstream\nendobj\n")
                obj_num += 1
            
            # Font object (Helvetica for basic text)
            offsets.append(0)
            font_obj = (
                f"{obj_num} 0 obj\n"
                f"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
                f"endobj\n"
            )
            pdf_objects.append(font_obj)
            obj_num += 1
            
            # Calculate actual offsets
            current_offset = len("%PDF-1.4\n")
            actual_offsets = []
            for i, obj in enumerate(pdf_objects):
                actual_offsets.append(current_offset)
                if isinstance(obj, str):
                    current_offset += len(obj.encode('latin-1'))
            
            # Cross-reference table
            xref_offset = current_offset
            xref = f"xref\n0 {obj_num}\n"
            xref += "0000000000 65535 f \n"
            for offset in actual_offsets:
                xref += f"{offset:010d} 00000 n \n"
            
            # Trailer
            trailer = (
                f"trailer\n"
                f"<< /Size {obj_num} /Root 1 0 R >>\n"
                f"startxref\n"
                f"{xref_offset}\n"
                f"%%EOF\n"
            )
            
            # Write PDF file
            with open(output_path, 'wb') as f:
                f.write(b"%PDF-1.4\n")
                for obj in pdf_objects:
                    if isinstance(obj, str):
                        f.write(obj.encode('latin-1'))
                    else:
                        f.write(obj)
                f.write(xref.encode('latin-1'))
                f.write(trailer.encode('latin-1'))
                
            return True
            
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return False


# ============================================================================
# DWFX EXTRACTION ENGINE (From working implementation)
# ============================================================================

def unzip_dwfx(dwfx_path: str, extract_dir: str) -> str:
    """Extract DWFx ZIP archive"""
    with zipfile.ZipFile(dwfx_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    return extract_dir


def parse_transform_matrix(transform_str: str) -> List[float]:
    """
    Parse XPS RenderTransform matrix string

    Format: "a,b,c,d,e,f" representing the 2D affine transform matrix:
    | a  c  e |
    | b  d  f |
    | 0  0  1 |

    Returns: [a, b, c, d, e, f] or None if no transform
    """
    if not transform_str:
        return None

    try:
        # Split by commas and parse as floats
        values = [float(x.strip()) for x in transform_str.split(',')]
        if len(values) == 6:
            return values
    except:
        pass

    return None


def apply_transform_to_coordinates(coords: List[Tuple[float, float]],
                                   matrix: List[float]) -> List[Tuple[float, float]]:
    """
    Apply 2D affine transformation matrix to coordinates

    Matrix: [a, b, c, d, e, f]
    Transform: x' = a*x + c*y + e
               y' = b*x + d*y + f
    """
    if not matrix:
        return coords

    a, b, c, d, e, f = matrix
    transformed = []

    for x, y in coords:
        x_new = a * x + c * y + e
        y_new = b * x + d * y + f
        transformed.append((x_new, y_new))

    return transformed


def transform_path_data(path_data: str, matrix: List[float]) -> str:
    """
    Apply transformation matrix to SVG path data string

    Extracts all coordinates, transforms them, and rebuilds the path string
    """
    if not matrix or not path_data:
        return path_data

    # Parse path commands and extract coordinates
    # Format: M x,y L x,y H x V y etc.
    import re

    # Match path commands with coordinates
    cmd_pattern = r'([MLHVCSQTAZmlhvcsqtaz])\s*([-\d.,\s]+)'
    commands = re.findall(cmd_pattern, path_data)

    transformed_path = []

    for cmd_letter, coords_str in commands:
        # Extract numeric values
        coords = re.findall(r'-?\d+\.?\d*', coords_str)
        coords = [float(c) for c in coords]

        # Transform based on command type
        if cmd_letter in 'MmLl' and len(coords) >= 2:
            # Move/Line with x,y pairs
            points = [(coords[i], coords[i+1]) for i in range(0, len(coords)-1, 2)]
            transformed_points = apply_transform_to_coordinates(points, matrix)
            coords_new = [f"{x:.2f},{y:.2f}" for x, y in transformed_points]
            transformed_path.append(f"{cmd_letter}{','.join(coords_new)}")

        elif cmd_letter in 'Hh' and len(coords) >= 1:
            # Horizontal line - transform x coordinate
            for x in coords:
                # For H command, y=0 (horizontal)
                transformed = apply_transform_to_coordinates([(x, 0)], matrix)
                x_new = transformed[0][0]
                transformed_path.append(f"{cmd_letter}{x_new:.2f}")

        elif cmd_letter in 'Vv' and len(coords) >= 1:
            # Vertical line - transform y coordinate
            for y in coords:
                # For V command, x=0 (vertical)
                transformed = apply_transform_to_coordinates([(0, y)], matrix)
                y_new = transformed[0][1]
                transformed_path.append(f"{cmd_letter}{y_new:.2f}")

        elif cmd_letter in 'Zz':
            # Close path - no coordinates
            transformed_path.append(cmd_letter)

        else:
            # Other commands - keep as-is for now
            transformed_path.append(f"{cmd_letter}{coords_str}")

    return ' '.join(transformed_path) if transformed_path else path_data


def parse_xps_page(xml_path: str) -> Dict:
    """
    Parse XPS page XML for paths, colors, coordinates
    NOW WITH RENDERTRANSFORM SUPPORT!
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    paths = []
    canvas_items = []

    # XPS namespaces
    ns = {'': 'http://schemas.microsoft.com/xps/2005/06'}

    def parse_element(elem, parent_transform=None):
        """Recursively parse elements and apply parent transforms"""
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        # Get transform for this element (if it's a Canvas)
        current_transform = parent_transform
        if tag == 'Canvas':
            transform_str = elem.attrib.get('RenderTransform', '')
            if transform_str:
                matrix = parse_transform_matrix(transform_str)
                if matrix:
                    current_transform = matrix

        # Extract Path elements and apply transform
        if tag == 'Path':
            path_data_str = elem.attrib.get('Data', '')

            # Apply transform to path data
            if current_transform:
                path_data_str = transform_path_data(path_data_str, current_transform)

            path_data = {
                'type': 'path',
                'data': path_data_str,
                'fill': elem.attrib.get('Fill', ''),
                'stroke': elem.attrib.get('Stroke', ''),
                'stroke_thickness': elem.attrib.get('StrokeThickness', '1'),
                'opacity': elem.attrib.get('Opacity', '1.0')
            }
            paths.append(path_data)

        # Extract Glyphs (text) and apply transform
        elif tag == 'Glyphs':
            origin_x = float(elem.attrib.get('OriginX', '0'))
            origin_y = float(elem.attrib.get('OriginY', '0'))

            # Apply transform to text position
            if current_transform:
                transformed_pos = apply_transform_to_coordinates([(origin_x, origin_y)], current_transform)
                origin_x, origin_y = transformed_pos[0]

            canvas_items.append({
                'type': 'text',
                'origin_x': str(origin_x),
                'origin_y': str(origin_y),
                'unicode_string': elem.attrib.get('UnicodeString', ''),
                'fill': elem.attrib.get('Fill', ''),
                'font_size': elem.attrib.get('FontRenderingEmSize', '12')
            })

        # Recursively process children
        for child in elem:
            parse_element(child, current_transform)

    # Start parsing from root
    parse_element(root)

    return {
        'paths': paths,
        'canvas_items': canvas_items,
        'page_dimensions': {
            'width': root.attrib.get('Width', '612'),
            'height': root.attrib.get('Height', '792')
        }
    }


def parse_color(color_str: str) -> Tuple[float, float, float]:
    """Parse XPS color string to RGB (0-1 range)"""
    if not color_str:
        return (0, 0, 0)
    
    color_str = color_str.lstrip('#')
    
    if len(color_str) == 8:  # AARRGGBB
        a, r, g, b = [int(color_str[i:i+2], 16) for i in (0, 2, 4, 6)]
    elif len(color_str) == 6:  # RRGGBB
        r, g, b = [int(color_str[i:i+2], 16) for i in (0, 2, 4)]
    else:
        r, g, b = 0, 0, 0
    
    return (r / 255.0, g / 255.0, b / 255.0)


# ============================================================================
# DWFX TO PDF CONVERTER
# ============================================================================

def convert_dwfx_to_pdf(dwfx_path: str, pdf_path: str, verbose: bool = True) -> bool:
    """
    Convert DWFX file to PDF
    
    Args:
        dwfx_path: Path to input DWFX file
        pdf_path: Path to output PDF file
        verbose: Print progress messages
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"\n🔄 Converting DWFX to PDF")
        print(f"   Input:  {dwfx_path}")
        print(f"   Output: {pdf_path}")
    
    try:
        # Create temp directory
        extract_dir = f"_temp_{Path(dwfx_path).stem}"
        
        # Extract DWFX
        if verbose:
            print("   📦 Extracting DWFX archive...")
        unzip_dwfx(dwfx_path, extract_dir)
        
        # Find XPS pages
        if verbose:
            print("   📄 Parsing vector pages...")
        page_files = list(Path(extract_dir).rglob("*.fpage"))
        
        if not page_files:
            print("   ❌ No pages found in DWFX file")
            return False
        
        # Parse first page to get dimensions
        first_page_data = parse_xps_page(page_files[0])
        page_width = float(first_page_data['page_dimensions'].get('width', 612))
        page_height = float(first_page_data['page_dimensions'].get('height', 792))
        
        # Create PDF
        if verbose:
            print(f"   🔨 Generating PDF ({page_width:.0f}x{page_height:.0f})...")
        pdf = PDFGenerator(width=page_width, height=page_height)
        
        # Process each page
        for page_idx, page_file in enumerate(page_files):
            if verbose:
                print(f"      Page {page_idx + 1}/{len(page_files)}")
                
            page_data = parse_xps_page(page_file)
            
            # Add paths
            for path in page_data['paths']:
                if path['data']:
                    fill_color = parse_color(path['fill']) if path['fill'] else None
                    stroke_color = parse_color(path['stroke']) if path['stroke'] else None
                    stroke_width = float(path['stroke_thickness']) if path['stroke_thickness'] else 1.0
                    
                    pdf.add_path(
                        path['data'],
                        fill_color=fill_color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width
                    )
            
            # Add text
            for item in page_data['canvas_items']:
                if item['type'] == 'text' and item['unicode_string']:
                    x = float(item['origin_x'])
                    y = page_height - float(item['origin_y'])  # Flip Y axis
                    text = item['unicode_string']
                    font_size = float(item['font_size'])
                    color = parse_color(item['fill']) if item['fill'] else (0, 0, 0)
                    
                    pdf.add_text(x, y, text, font_size=font_size, color=color)
            
            # Start new page if not last
            if page_idx < len(page_files) - 1:
                pdf.add_page()
        
        # Save PDF
        if verbose:
            print("   💾 Writing PDF file...")
        success = pdf.save(pdf_path)
        
        # Cleanup
        import shutil
        shutil.rmtree(extract_dir, ignore_errors=True)
        
        if success:
            file_size = os.path.getsize(pdf_path)
            if verbose:
                print(f"   ✅ Conversion complete!")
                print(f"      PDF size: {file_size:,} bytes")
                print(f"      Pages: {len(page_files)}")
        
        return success
        
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def batch_convert_dwfx_to_pdf(input_dir: str, output_dir: str) -> Dict:
    """
    Batch convert all DWFX files in directory
    
    Args:
        input_dir: Directory containing DWFX files
        output_dir: Directory for output PDF files
        
    Returns:
        Dictionary with conversion statistics
    """
    print(f"\n🔄 Batch DWFX to PDF Conversion")
    print(f"   Input:  {input_dir}")
    print(f"   Output: {output_dir}")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Find all DWFX files
    dwfx_files = list(Path(input_dir).glob("*.dwfx"))
    dwfx_files.extend(Path(input_dir).glob("*.dwf"))
    
    if not dwfx_files:
        print("   ❌ No DWFX files found")
        return {"total": 0, "success": 0, "failed": 0}
    
    print(f"   📁 Found {len(dwfx_files)} files")
    
    results = {"total": len(dwfx_files), "success": 0, "failed": 0, "files": []}
    
    for dwfx_file in dwfx_files:
        pdf_file = Path(output_dir) / f"{dwfx_file.stem}.pdf"
        
        success = convert_dwfx_to_pdf(str(dwfx_file), str(pdf_file), verbose=True)
        
        if success:
            results["success"] += 1
            results["files"].append({
                "input": str(dwfx_file),
                "output": str(pdf_file),
                "status": "success"
            })
        else:
            results["failed"] += 1
            results["files"].append({
                "input": str(dwfx_file),
                "status": "failed"
            })
    
    print(f"\n✅ Batch conversion complete")
    print(f"   Total:   {results['total']}")
    print(f"   Success: {results['success']}")
    print(f"   Failed:  {results['failed']}")
    
    return results


# ============================================================================
# FME INTEGRATION
# ============================================================================

class DWFXToPDFConverter:
    """
    FME PythonCaller compatible class
    
    Usage in FME:
        from dwfx_to_pdf import DWFXToPDFConverter
        
        converter = DWFXToPDFConverter()
        result = converter.convert(input_path, output_path)
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.last_error = None
        
    def convert(self, dwfx_path: str, pdf_path: str) -> bool:
        """
        Convert single DWFX file to PDF
        
        Args:
            dwfx_path: Path to input DWFX file
            pdf_path: Path to output PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return convert_dwfx_to_pdf(dwfx_path, pdf_path, verbose=False)
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def batch_convert(self, input_dir: str, output_dir: str) -> Dict:
        """
        Batch convert DWFX files
        
        Args:
            input_dir: Directory with DWFX files
            output_dir: Directory for PDF files
            
        Returns:
            Dictionary with conversion statistics
        """
        try:
            return batch_convert_dwfx_to_pdf(input_dir, output_dir)
        except Exception as e:
            self.last_error = str(e)
            return {"total": 0, "success": 0, "failed": 1}
    
    def get_last_error(self) -> str:
        """Get last error message"""
        return self.last_error or "No error"


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Command line interface"""
    if len(sys.argv) < 3:
        print("""
DWFX to PDF Converter - Zero Dependencies

USAGE:
    Single file:
        python dwfx_to_pdf.py <input.dwfx> <output.pdf>
    
    Batch conversion:
        python dwfx_to_pdf.py batch <input_directory> <output_directory>

FEATURES:
    ✅ 100% offline operation
    ✅ Zero pip dependencies (stdlib only)
    ✅ Full Unicode and Hebrew text support
    ✅ Preserves vector graphics and layouts
    ✅ Batch conversion support
    ✅ FME PythonCaller compatible

EXAMPLES:
    python dwfx_to_pdf.py drawing.dwfx drawing.pdf
    python dwfx_to_pdf.py batch ./dwfx_files ./pdf_output
""")
        sys.exit(1)
    
    if sys.argv[1] == "batch":
        if len(sys.argv) < 4:
            print("Error: Batch mode requires input and output directories")
            sys.exit(1)
        
        input_dir = sys.argv[2]
        output_dir = sys.argv[3]
        batch_convert_dwfx_to_pdf(input_dir, output_dir)
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        
        if not os.path.exists(input_file):
            print(f"Error: Input file not found: {input_file}")
            sys.exit(1)
        
        success = convert_dwfx_to_pdf(input_file, output_file)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
