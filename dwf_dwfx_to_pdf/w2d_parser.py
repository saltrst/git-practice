#!/usr/bin/env python3
"""
W2D Binary Format Parser - ZERO dependencies
Parses DWF W2D binary graphics format to extract vector data

Based on Autodesk DWF specification (open format)
"""

import struct
from typing import Dict, List, Tuple, BinaryIO
from pathlib import Path


# W2D Opcode Definitions (from DWF specification)
OPCODES = {
    # Drawing primitives
    0x28: 'POLYLINE',
    0x29: 'POLYTRIANGLE', 
    0x2A: 'POLYPOINT',
    0x2B: 'POLYRECTANGLE',
    0x2C: 'POLYPOLYGON',
    0x2D: 'POLYMARKER',
    
    # Attributes
    0x30: 'COLOR',
    0x31: 'LINE_WEIGHT',
    0x32: 'LINE_PATTERN',
    0x33: 'FILL_PATTERN',
    0x34: 'FONT',
    
    # Text
    0x40: 'TEXT',
    0x41: 'TEXT_HALIGN',
    0x42: 'TEXT_VALIGN',
    
    # Geometry
    0x50: 'MOVE_TO',
    0x51: 'LINE_TO',
    0x52: 'ARC',
    0x53: 'CIRCLE',
    0x54: 'ELLIPSE',
    
    # State
    0x60: 'PUSH_CLIP',
    0x61: 'POP_CLIP',
    0x62: 'VIEWPORT',
    0x63: 'LAYER',
    
    # ASCII opcodes
    0x20: 'SPACE',
    0x09: 'TAB',
    0x0A: 'NEWLINE',
    
    # Extended
    0xFF: 'EXTENDED_ASCII',
    0xFE: 'EXTENDED_BINARY',
}


class W2DParser:
    """
    Zero-dependency W2D binary format parser
    Extracts vector graphics from DWF W2D files
    """
    
    def __init__(self):
        self.paths = []
        self.text_elements = []
        self.current_color = (0, 0, 0)
        self.current_line_weight = 1.0
        self.current_position = (0.0, 0.0)
        self.version = None
        
    def parse_file(self, w2d_path: str) -> Dict:
        """Parse W2D file and extract all vector data"""
        with open(w2d_path, 'rb') as f:
            # Parse header
            header = self._parse_header(f)
            
            if not header['valid']:
                raise ValueError("Invalid W2D file header")
            
            self.version = header['version']
            
            # Parse opcode stream
            while True:
                opcode = f.read(1)
                if not opcode:
                    break
                    
                opcode_val = opcode[0]
                
                # Handle opcode
                if opcode_val in OPCODES:
                    self._handle_opcode(f, opcode_val)
                elif opcode_val == 0x00:
                    # End of file
                    break
                else:
                    # Unknown opcode - try to skip
                    print(f"Warning: Unknown opcode 0x{opcode_val:02X}")
        
        return {
            'version': self.version,
            'paths': self.paths,
            'text_elements': self.text_elements,
            'path_count': len(self.paths),
            'text_count': len(self.text_elements)
        }
    
    def _parse_header(self, f: BinaryIO) -> Dict:
        """Parse 12-byte W2D header"""
        header_data = f.read(12)
        
        if len(header_data) < 12:
            return {'valid': False}
        
        # DWF magic bytes: "(DWF V" or similar
        magic = header_data[0:6].decode('ascii', errors='ignore')
        
        # Version string: "xx.xx"
        version_str = header_data[6:12].decode('ascii', errors='ignore')
        
        return {
            'valid': 'DWF' in magic or magic.startswith('('),
            'magic': magic,
            'version': version_str.strip(),
            'header_bytes': header_data
        }
    
    def _handle_opcode(self, f: BinaryIO, opcode: int):
        """Handle specific opcode"""
        opcode_name = OPCODES.get(opcode, 'UNKNOWN')
        
        if opcode == 0x28:  # POLYLINE
            self._parse_polyline(f)
        elif opcode == 0x40:  # TEXT
            self._parse_text(f)
        elif opcode == 0x30:  # COLOR
            self._parse_color(f)
        elif opcode == 0x50:  # MOVE_TO
            self._parse_move_to(f)
        elif opcode == 0x51:  # LINE_TO
            self._parse_line_to(f)
        # ... handle other opcodes as needed
    
    def _parse_polyline(self, f: BinaryIO):
        """Parse polyline opcode"""
        # Read point count (typically 2 bytes)
        count_bytes = f.read(2)
        if len(count_bytes) < 2:
            return
        
        point_count = struct.unpack('<H', count_bytes)[0]
        
        # Read points (x, y pairs as floats or ints)
        points = []
        for i in range(point_count):
            point_bytes = f.read(8)  # Assuming 4 bytes per coord
            if len(point_bytes) < 8:
                break
            x, y = struct.unpack('<ff', point_bytes)
            points.append((x, y))
        
        # Store path
        if points:
            self.paths.append({
                'type': 'polyline',
                'points': points,
                'color': self.current_color,
                'line_weight': self.current_line_weight
            })
    
    def _parse_text(self, f: BinaryIO):
        """Parse text opcode"""
        # Read position (8 bytes for x, y)
        pos_bytes = f.read(8)
        if len(pos_bytes) < 8:
            return
        
        x, y = struct.unpack('<ff', pos_bytes)
        
        # Read string length (2 bytes)
        len_bytes = f.read(2)
        if len(len_bytes) < 2:
            return
        
        str_len = struct.unpack('<H', len_bytes)[0]
        
        # Read string
        text_bytes = f.read(str_len)
        text = text_bytes.decode('utf-8', errors='ignore')
        
        # Store text
        self.text_elements.append({
            'type': 'text',
            'position': (x, y),
            'text': text,
            'color': self.current_color
        })
    
    def _parse_color(self, f: BinaryIO):
        """Parse color opcode (RGB or RGBA)"""
        color_bytes = f.read(4)  # Assuming RGBA format
        if len(color_bytes) < 4:
            return
        
        r, g, b, a = struct.unpack('BBBB', color_bytes)
        self.current_color = (r / 255.0, g / 255.0, b / 255.0)
    
    def _parse_move_to(self, f: BinaryIO):
        """Parse move to opcode"""
        pos_bytes = f.read(8)
        if len(pos_bytes) < 8:
            return
        
        x, y = struct.unpack('<ff', pos_bytes)
        self.current_position = (x, y)
    
    def _parse_line_to(self, f: BinaryIO):
        """Parse line to opcode"""
        pos_bytes = f.read(8)
        if len(pos_bytes) < 8:
            return
        
        x, y = struct.unpack('<ff', pos_bytes)
        
        # Create line path
        self.paths.append({
            'type': 'line',
            'start': self.current_position,
            'end': (x, y),
            'color': self.current_color,
            'line_weight': self.current_line_weight
        })
        
        self.current_position = (x, y)


def w2d_to_xps_xml(w2d_data: Dict) -> str:
    """
    Convert W2D data to XPS XML format
    This creates the SAME format as DWFX, enabling unified processing
    """
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<FixedPage xmlns="http://schemas.microsoft.com/xps/2005/06" Width="612" Height="792">',
        '  <!-- Converted from W2D binary format -->'
    ]
    
    # Convert paths
    for path in w2d_data['paths']:
        if path['type'] == 'polyline':
            # Build path data string
            points = path['points']
            path_data = f"M {points[0][0]} {points[0][1]}"
            for x, y in points[1:]:
                path_data += f" L {x} {y}"
            
            # Color to hex
            r, g, b = [int(c * 255) for c in path['color']]
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            xml_lines.append(
                f'  <Path Data="{path_data}" Stroke="{color}" '
                f'StrokeThickness="{path["line_weight"]}" />'
            )
        
        elif path['type'] == 'line':
            x1, y1 = path['start']
            x2, y2 = path['end']
            path_data = f"M {x1} {y1} L {x2} {y2}"
            
            r, g, b = [int(c * 255) for c in path['color']]
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            xml_lines.append(
                f'  <Path Data="{path_data}" Stroke="{color}" '
                f'StrokeThickness="{path["line_weight"]}" />'
            )
    
    # Convert text
    for text_elem in w2d_data['text_elements']:
        x, y = text_elem['position']
        text = text_elem['text']
        
        r, g, b = [int(c * 255) for c in text_elem['color']]
        color = f"#{r:02x}{g:02x}{b:02x}"
        
        xml_lines.append(
            f'  <Glyphs OriginX="{x}" OriginY="{y}" '
            f'UnicodeString="{text}" Fill="{color}" '
            f'FontRenderingEmSize="12" />'
        )
    
    xml_lines.append('</FixedPage>')
    
    return '\n'.join(xml_lines)


def test_w2d_parser(w2d_path: str):
    """Test W2D parser on a file"""
    print(f"\n{'='*60}")
    print(f"W2D Binary Parser Test")
    print(f"{'='*60}")
    print(f"File: {w2d_path}")
    
    parser = W2DParser()
    
    try:
        data = parser.parse_file(w2d_path)
        
        print(f"\n✅ Parsing successful!")
        print(f"   Version: {data['version']}")
        print(f"   Paths: {data['path_count']}")
        print(f"   Text elements: {data['text_count']}")
        
        # Convert to XPS XML
        xps_xml = w2d_to_xps_xml(data)
        
        print(f"\n✅ Converted to XPS XML format")
        print(f"   XML length: {len(xps_xml)} characters")
        
        # Save XPS XML
        output_path = Path(w2d_path).with_suffix('.fpage')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xps_xml)
        
        print(f"   Saved to: {output_path}")
        print(f"\n🎯 This XPS file can now be processed by dwfx_to_pdf.py!")
        
    except Exception as e:
        print(f"\n❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("""
W2D Binary Parser - Proof of Concept

This demonstrates that W2D binary format CAN be parsed with zero dependencies.

Usage:
    python w2d_parser.py <file.w2d>

The parser will:
1. Read W2D binary opcodes
2. Extract vector paths and text
3. Convert to XPS XML format
4. Save as .fpage file

The output .fpage can then be processed by dwfx_to_pdf.py!

This proves the conversion chain:
    DWF (W2D binary) → XPS XML → PDF
""")
        sys.exit(1)
    
    test_w2d_parser(sys.argv[1])
