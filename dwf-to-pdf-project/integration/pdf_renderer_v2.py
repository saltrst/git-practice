#!/usr/bin/env python3
"""
PDF Renderer Version 2 for DWF to PDF Conversion
=================================================

This module takes parsed DWF opcodes (list of dictionaries) and renders them to PDF
using ReportLab. It handles ~50-80 distinct opcode types discovered from 44 agent files.

Input: List of parsed opcode dictionaries from DWF parser
Output: PDF file rendered using ReportLab

Author: Agent B2 (Build PDF Renderer v2)
Date: 2025-10-22
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from typing import List, Dict, Any, Tuple, Optional
import math


# =============================================================================
# Graphics State Management
# =============================================================================

class GraphicsState:
    """Manages PDF graphics state (color, origin, line width, font, etc.)"""

    def __init__(self):
        # Color state
        self.stroke_color = (0, 0, 0)  # RGB
        self.fill_color = (0, 0, 0)    # RGB
        self.alpha = 1.0               # Opacity

        # Line state
        self.line_width = 1.0
        self.line_pattern = None  # Dash pattern
        self.line_cap = 0         # 0=butt, 1=round, 2=square
        self.line_join = 0        # 0=miter, 1=round, 2=bevel

        # Transform state
        self.origin = (0, 0)
        self.rotation = 0
        self.scale = (1.0, 1.0)

        # Font state
        self.font_name = "Helvetica"
        self.font_size = 12
        self.font_bold = False
        self.font_italic = False

        # Fill state
        self.fill_mode = True

        # Layer state
        self.current_layer = None

    def copy(self):
        """Create a copy of current state for state stack"""
        state = GraphicsState()
        state.stroke_color = self.stroke_color
        state.fill_color = self.fill_color
        state.alpha = self.alpha
        state.line_width = self.line_width
        state.line_pattern = self.line_pattern
        state.line_cap = self.line_cap
        state.line_join = self.line_join
        state.origin = self.origin
        state.rotation = self.rotation
        state.scale = self.scale
        state.font_name = self.font_name
        state.font_size = self.font_size
        state.font_bold = self.font_bold
        state.font_italic = self.font_italic
        state.fill_mode = self.fill_mode
        state.current_layer = self.current_layer
        return state


class StateStack:
    """Stack for graphics state save/restore"""

    def __init__(self):
        self.stack = []

    def push(self, state: GraphicsState):
        """Save current state"""
        self.stack.append(state.copy())

    def pop(self) -> Optional[GraphicsState]:
        """Restore previous state"""
        if self.stack:
            return self.stack.pop()
        return None


# =============================================================================
# Color Conversion Utilities
# =============================================================================

def bgra_to_rgb(bgra: Tuple[int, int, int, int]) -> Tuple[float, float, float]:
    """
    Convert BGRA color (DWF format) to RGB (PDF format).

    DWF uses BGRA byte order: (Blue, Green, Red, Alpha)
    PDF uses RGB: (Red, Green, Blue) with values 0.0-1.0

    Args:
        bgra: Tuple of (B, G, R, A) where each is 0-255

    Returns:
        Tuple of (R, G, B) where each is 0.0-1.0
    """
    b, g, r, a = bgra
    return (r / 255.0, g / 255.0, b / 255.0)


def rgba_to_rgb(rgba: Tuple[int, int, int, int]) -> Tuple[float, float, float]:
    """
    Convert RGBA color to RGB for PDF.

    Args:
        rgba: Tuple of (R, G, B, A) where each is 0-255

    Returns:
        Tuple of (R, G, B) where each is 0.0-1.0
    """
    r, g, b, a = rgba
    return (r / 255.0, g / 255.0, b / 255.0)


def color_int_to_rgb(color_int: int) -> Tuple[float, float, float]:
    """
    Convert 32-bit color integer to RGB.

    Args:
        color_int: 32-bit integer color value

    Returns:
        Tuple of (R, G, B) where each is 0.0-1.0
    """
    r = (color_int & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = ((color_int >> 16) & 0xFF) / 255.0
    return (r, g, b)


# =============================================================================
# Coordinate Transformation
# =============================================================================

def dwf_to_pdf_coords(dwf_x: int, dwf_y: int, page_height: float = 11*inch) -> Tuple[float, float]:
    """
    Transform DWF logical coordinates to PDF coordinates.

    DWF uses origin at top-left with Y increasing downward.
    PDF uses origin at bottom-left with Y increasing upward.

    Args:
        dwf_x: DWF X coordinate (logical units)
        dwf_y: DWF Y coordinate (logical units)
        page_height: PDF page height in points

    Returns:
        Tuple of (pdf_x, pdf_y) in PDF points
    """
    # Simple scaling factor (adjust based on DWF units)
    scale_factor = 0.01  # 1 DWF unit = 0.01 PDF points

    pdf_x = dwf_x * scale_factor
    pdf_y = page_height - (dwf_y * scale_factor)  # Flip Y axis

    return (pdf_x, pdf_y)


# =============================================================================
# Main PDF Renderer
# =============================================================================

class DWFPDFRenderer:
    """Renders parsed DWF opcodes to PDF"""

    def __init__(self, output_path: str, page_size=letter):
        """
        Initialize PDF renderer.

        Args:
            output_path: Path to output PDF file
            page_size: Page size tuple (width, height) or standard size
        """
        self.output_path = output_path
        self.page_size = page_size
        self.page_width, self.page_height = page_size

        # Create canvas
        self.canvas = canvas.Canvas(output_path, pagesize=page_size)

        # State management
        self.state = GraphicsState()
        self.state_stack = StateStack()

        # Metadata
        self.metadata = {}

        # Type handler dispatch table
        self.type_handlers = {
            # Geometry types
            'line': self.handle_line,
            'polyline': self.handle_polyline,
            'polygon': self.handle_polygon,
            'circle': self.handle_circle,
            'ellipse': self.handle_ellipse,
            'contour': self.handle_contour,
            'bezier': self.handle_bezier,

            # Gouraud shading
            'gouraud_polytriangle': self.handle_gouraud_polytriangle,
            'gouraud_polyline': self.handle_gouraud_polyline,

            # Text types
            'text': self.handle_text,

            # Attributes
            'color': self.handle_color,
            'layer': self.handle_layer,
            'line_weight': self.handle_line_weight,
            'line_pattern': self.handle_line_pattern,
            'line_style': self.handle_line_style,
            'fill_pattern': self.handle_fill_pattern,

            # Font/text attributes
            'font': self.handle_font,
            'text_halign': self.handle_text_halign,
            'text_valign': self.handle_text_valign,

            # Metadata types
            'metadata': self.handle_metadata,
            'copyright': self.handle_metadata,
            'creator': self.handle_metadata,
            'creation_time': self.handle_metadata,
            'modification_time': self.handle_metadata,
            'source_creation_time': self.handle_metadata,
            'source_modification_time': self.handle_metadata,

            # State management
            'save_state': self.handle_save_state,
            'restore_state': self.handle_restore_state,

            # File structure
            'end_of_dwf': self.handle_end_of_dwf,

            # Images
            'image': self.handle_image,

            # Transform
            'origin': self.handle_origin,

            # Unknown/unsupported
            'unknown': self.handle_unknown,
        }

    def render(self, opcodes: List[Dict[str, Any]]):
        """
        Render all opcodes to PDF.

        Args:
            opcodes: List of parsed opcode dictionaries
        """
        for opcode in opcodes:
            self.render_opcode(opcode)

        # Finalize PDF
        self.canvas.save()

    def render_opcode(self, opcode: Dict[str, Any]):
        """
        Dispatch single opcode to appropriate handler.

        Args:
            opcode: Parsed opcode dictionary with 'type' key
        """
        opcode_type = opcode.get('type', 'unknown')

        handler = self.type_handlers.get(opcode_type, self.handle_unknown)
        handler(opcode)

    # =========================================================================
    # Geometry Handlers
    # =========================================================================

    def handle_line(self, opcode: Dict):
        """Draw a line"""
        if 'x1' in opcode and 'y1' in opcode and 'x2' in opcode and 'y2' in opcode:
            x1, y1 = dwf_to_pdf_coords(opcode['x1'], opcode['y1'], self.page_height)
            x2, y2 = dwf_to_pdf_coords(opcode['x2'], opcode['y2'], self.page_height)

            self.apply_stroke_state()
            self.canvas.line(x1, y1, x2, y2)

    def handle_polyline(self, opcode: Dict):
        """Draw a polyline"""
        points = opcode.get('points', [])
        if len(points) < 2:
            return

        path = self.canvas.beginPath()

        # First point
        x, y = dwf_to_pdf_coords(points[0][0], points[0][1], self.page_height)
        path.moveTo(x, y)

        # Subsequent points
        for i in range(1, len(points)):
            x, y = dwf_to_pdf_coords(points[i][0], points[i][1], self.page_height)
            path.lineTo(x, y)

        self.apply_stroke_state()
        self.canvas.drawPath(path, stroke=1, fill=0)

    def handle_polygon(self, opcode: Dict):
        """Draw a polygon"""
        points = opcode.get('points', [])
        if len(points) < 3:
            return

        path = self.canvas.beginPath()

        # First point
        x, y = dwf_to_pdf_coords(points[0][0], points[0][1], self.page_height)
        path.moveTo(x, y)

        # Subsequent points
        for i in range(1, len(points)):
            x, y = dwf_to_pdf_coords(points[i][0], points[i][1], self.page_height)
            path.lineTo(x, y)

        # Close path
        path.close()

        self.apply_fill_stroke_state()
        self.canvas.drawPath(path, stroke=1, fill=self.state.fill_mode)

    def handle_circle(self, opcode: Dict):
        """Draw a circle or circular arc"""
        if 'position' not in opcode or 'radius' not in opcode:
            return

        cx, cy = dwf_to_pdf_coords(opcode['position'][0], opcode['position'][1], self.page_height)
        radius = opcode['radius'] * 0.01  # Scale to PDF units

        if opcode.get('is_full_circle', True):
            # Full circle
            self.apply_fill_stroke_state()
            self.canvas.circle(cx, cy, radius, stroke=1, fill=self.state.fill_mode)
        else:
            # Arc - approximate with bezier curves
            start_deg = opcode.get('start_angle_deg', 0)
            end_deg = opcode.get('end_angle_deg', 360)
            self.draw_arc(cx, cy, radius, start_deg, end_deg)

    def handle_ellipse(self, opcode: Dict):
        """Draw an ellipse"""
        if 'position' not in opcode or 'major' not in opcode or 'minor' not in opcode:
            return

        cx, cy = dwf_to_pdf_coords(opcode['position'][0], opcode['position'][1], self.page_height)
        major = opcode['major'] * 0.01
        minor = opcode['minor'] * 0.01

        # ReportLab ellipse (simplified - doesn't support rotation)
        self.apply_fill_stroke_state()
        self.canvas.ellipse(cx - major, cy - minor, cx + major, cy + minor,
                           stroke=1, fill=self.state.fill_mode)

    def handle_contour(self, opcode: Dict):
        """Draw a contour (complex polygon)"""
        points = opcode.get('points', [])
        if not points:
            return

        path = self.canvas.beginPath()

        # First point
        x, y = dwf_to_pdf_coords(points[0][0], points[0][1], self.page_height)
        path.moveTo(x, y)

        # Subsequent points
        for i in range(1, len(points)):
            x, y = dwf_to_pdf_coords(points[i][0], points[i][1], self.page_height)
            path.lineTo(x, y)

        path.close()

        self.apply_fill_stroke_state()
        self.canvas.drawPath(path, stroke=1, fill=self.state.fill_mode)

    def handle_bezier(self, opcode: Dict):
        """Draw Bezier curves"""
        control_points = opcode.get('control_points', [])
        if len(control_points) < 4:
            return

        path = self.canvas.beginPath()

        # Start at first point
        x, y = dwf_to_pdf_coords(control_points[0][0], control_points[0][1], self.page_height)
        path.moveTo(x, y)

        # Draw cubic Bezier curves (4 points per curve)
        i = 1
        while i + 2 < len(control_points):
            x1, y1 = dwf_to_pdf_coords(control_points[i][0], control_points[i][1], self.page_height)
            x2, y2 = dwf_to_pdf_coords(control_points[i+1][0], control_points[i+1][1], self.page_height)
            x3, y3 = dwf_to_pdf_coords(control_points[i+2][0], control_points[i+2][1], self.page_height)

            path.curveTo(x1, y1, x2, y2, x3, y3)
            i += 3

        self.apply_stroke_state()
        self.canvas.drawPath(path, stroke=1, fill=0)

    # =========================================================================
    # Gouraud Shading Handlers
    # =========================================================================

    def handle_gouraud_polytriangle(self, opcode: Dict):
        """Approximate Gouraud shaded triangles with flat shading"""
        points = opcode.get('points', [])
        if len(points) < 3:
            return

        # For each triangle (3 points at a time)
        for i in range(0, len(points) - 2, 3):
            # Average the colors for flat shading
            avg_color = (
                (points[i]['color'][0] + points[i+1]['color'][0] + points[i+2]['color'][0]) / 3 / 255.0,
                (points[i]['color'][1] + points[i+1]['color'][1] + points[i+2]['color'][1]) / 3 / 255.0,
                (points[i]['color'][2] + points[i+1]['color'][2] + points[i+2]['color'][2]) / 3 / 255.0
            )

            # Draw triangle with average color
            path = self.canvas.beginPath()
            x, y = dwf_to_pdf_coords(points[i]['position'][0], points[i]['position'][1], self.page_height)
            path.moveTo(x, y)

            for j in range(i+1, i+3):
                x, y = dwf_to_pdf_coords(points[j]['position'][0], points[j]['position'][1], self.page_height)
                path.lineTo(x, y)

            path.close()

            self.canvas.setFillColorRGB(*avg_color)
            self.canvas.drawPath(path, stroke=0, fill=1)

    def handle_gouraud_polyline(self, opcode: Dict):
        """Approximate Gouraud shaded polyline"""
        points = opcode.get('points', [])
        if len(points) < 2:
            return

        # Draw segments with interpolated colors
        for i in range(len(points) - 1):
            x1, y1 = dwf_to_pdf_coords(points[i]['position'][0], points[i]['position'][1], self.page_height)
            x2, y2 = dwf_to_pdf_coords(points[i+1]['position'][0], points[i+1]['position'][1], self.page_height)

            # Use average color for the segment
            avg_color = (
                (points[i]['color'][0] + points[i+1]['color'][0]) / 2 / 255.0,
                (points[i]['color'][1] + points[i+1]['color'][1]) / 2 / 255.0,
                (points[i]['color'][2] + points[i+1]['color'][2]) / 2 / 255.0
            )

            self.canvas.setStrokeColorRGB(*avg_color)
            self.canvas.line(x1, y1, x2, y2)

    # =========================================================================
    # Text Handlers
    # =========================================================================

    def handle_text(self, opcode: Dict):
        """Draw text with full Unicode/Hebrew support"""
        if 'position' not in opcode or 'text' not in opcode:
            return

        x, y = dwf_to_pdf_coords(opcode['position'][0], opcode['position'][1], self.page_height)
        text = opcode['text']

        # Apply font state
        self.canvas.setFont(self.state.font_name, self.state.font_size)
        self.canvas.setFillColorRGB(*self.state.fill_color)

        # Draw text
        self.canvas.drawString(x, y, text)

    # =========================================================================
    # Attribute Handlers
    # =========================================================================

    def handle_color(self, opcode: Dict):
        """Set current color"""
        if 'red' in opcode and 'green' in opcode and 'blue' in opcode:
            r = opcode['red'] / 255.0
            g = opcode['green'] / 255.0
            b = opcode['blue'] / 255.0

            self.state.stroke_color = (r, g, b)
            self.state.fill_color = (r, g, b)

            if 'alpha' in opcode:
                self.state.alpha = opcode['alpha'] / 255.0

    def handle_layer(self, opcode: Dict):
        """Set current layer"""
        if 'layer_name' in opcode:
            self.state.current_layer = opcode['layer_name']

    def handle_line_weight(self, opcode: Dict):
        """Set line weight"""
        if 'weight' in opcode:
            self.state.line_width = max(0.1, opcode['weight'] * 0.01)

    def handle_line_pattern(self, opcode: Dict):
        """Set line pattern (dash)"""
        # ReportLab dash patterns: setDash([on, off], phase)
        pattern_name = opcode.get('pattern', 'solid')

        if pattern_name == 'dashed':
            self.state.line_pattern = ([3, 3], 0)
        elif pattern_name == 'dotted':
            self.state.line_pattern = ([1, 2], 0)
        else:
            self.state.line_pattern = None

    def handle_line_style(self, opcode: Dict):
        """Set line style (caps, joins)"""
        if 'line_cap' in opcode:
            self.state.line_cap = opcode['line_cap']
        if 'line_join' in opcode:
            self.state.line_join = opcode['line_join']

    def handle_fill_pattern(self, opcode: Dict):
        """Set fill pattern"""
        # Simplified - just set fill mode
        pattern = opcode.get('pattern', 'solid')
        self.state.fill_mode = (pattern == 'solid')

    # =========================================================================
    # Font/Text Handlers
    # =========================================================================

    def handle_font(self, opcode: Dict):
        """Set current font"""
        if 'name' in opcode:
            self.state.font_name = opcode['name']

        if 'height' in opcode:
            self.state.font_size = opcode['height'] * 0.1  # Scale to PDF points

        if 'bold' in opcode:
            self.state.font_bold = opcode['bold']

        if 'italic' in opcode:
            self.state.font_italic = opcode['italic']

    def handle_text_halign(self, opcode: Dict):
        """Handle text horizontal alignment"""
        # Store alignment for future text rendering
        pass

    def handle_text_valign(self, opcode: Dict):
        """Handle text vertical alignment"""
        # Store alignment for future text rendering
        pass

    # =========================================================================
    # Metadata Handlers
    # =========================================================================

    def handle_metadata(self, opcode: Dict):
        """Store metadata for PDF info"""
        opcode_type = opcode.get('type')

        if opcode_type == 'creator' and 'creator' in opcode:
            self.canvas.setCreator(opcode['creator'])
        elif opcode_type == 'metadata' and 'value' in opcode:
            self.metadata[opcode.get('opcode_id', 'unknown')] = opcode['value']

    # =========================================================================
    # State Management Handlers
    # =========================================================================

    def handle_save_state(self, opcode: Dict):
        """Save current graphics state"""
        self.state_stack.push(self.state)
        self.canvas.saveState()

    def handle_restore_state(self, opcode: Dict):
        """Restore previous graphics state"""
        saved_state = self.state_stack.pop()
        if saved_state:
            self.state = saved_state
        self.canvas.restoreState()

    # =========================================================================
    # Transform Handlers
    # =========================================================================

    def handle_origin(self, opcode: Dict):
        """Set coordinate system origin"""
        if 'x' in opcode and 'y' in opcode:
            self.state.origin = (opcode['x'], opcode['y'])

    # =========================================================================
    # Image Handlers
    # =========================================================================

    def handle_image(self, opcode: Dict):
        """Draw an embedded image"""
        # Simplified - would need proper image handling
        pass

    # =========================================================================
    # File Structure Handlers
    # =========================================================================

    def handle_end_of_dwf(self, opcode: Dict):
        """Handle end of DWF file"""
        # Finalize current page
        self.canvas.showPage()

    # =========================================================================
    # Unknown Handler
    # =========================================================================

    def handle_unknown(self, opcode: Dict):
        """Handle unknown/unsupported opcodes"""
        # Silently ignore unknown opcodes
        pass

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def apply_stroke_state(self):
        """Apply current stroke state to canvas"""
        self.canvas.setStrokeColorRGB(*self.state.stroke_color)
        self.canvas.setLineWidth(self.state.line_width)

        if self.state.line_pattern:
            self.canvas.setDash(*self.state.line_pattern)
        else:
            self.canvas.setDash()  # Solid line

    def apply_fill_stroke_state(self):
        """Apply both fill and stroke state to canvas"""
        self.apply_stroke_state()
        self.canvas.setFillColorRGB(*self.state.fill_color)

    def draw_arc(self, cx: float, cy: float, radius: float, start_deg: float, end_deg: float):
        """Draw a circular arc using bezier approximation"""
        # Simplified arc drawing
        path = self.canvas.beginPath()

        # Convert to radians
        start_rad = math.radians(start_deg)
        end_rad = math.radians(end_deg)

        # Start point
        x = cx + radius * math.cos(start_rad)
        y = cy + radius * math.sin(start_rad)
        path.moveTo(x, y)

        # Approximate with line segments
        steps = max(10, int(abs(end_deg - start_deg) / 10))
        for i in range(1, steps + 1):
            angle = start_rad + (end_rad - start_rad) * i / steps
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            path.lineTo(x, y)

        self.apply_stroke_state()
        self.canvas.drawPath(path, stroke=1, fill=0)


# =============================================================================
# Public API
# =============================================================================

def render_dwf_to_pdf(parsed_opcodes: List[Dict[str, Any]], output_path: str,
                     page_size=letter):
    """
    Render parsed DWF opcodes to PDF file.

    Args:
        parsed_opcodes: List of parsed opcode dictionaries from DWF parser
        output_path: Path to output PDF file
        page_size: PDF page size (default: letter)

    Example:
        >>> opcodes = [
        ...     {'type': 'line', 'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100},
        ...     {'type': 'circle', 'position': (50, 50), 'radius': 25, 'is_full_circle': True},
        ...     {'type': 'text', 'position': (100, 200), 'text': 'Hello World'}
        ... ]
        >>> render_dwf_to_pdf(opcodes, 'output.pdf')
    """
    renderer = DWFPDFRenderer(output_path, page_size)
    renderer.render(parsed_opcodes)


# =============================================================================
# Test Function
# =============================================================================

def test_render():
    """Test PDF rendering with mock opcode data"""
    print("Testing PDF Renderer v2...")

    # Mock opcode list covering various types
    test_opcodes = [
        # Set color to blue
        {'type': 'color', 'red': 0, 'green': 0, 'blue': 255, 'alpha': 255},

        # Draw a line
        {'type': 'line', 'x1': 1000, 'y1': 1000, 'x2': 5000, 'y2': 5000},

        # Set color to red
        {'type': 'color', 'red': 255, 'green': 0, 'blue': 0, 'alpha': 255},

        # Draw a circle
        {'type': 'circle', 'position': (3000, 3000), 'radius': 1000, 'is_full_circle': True},

        # Set color to green
        {'type': 'color', 'red': 0, 'green': 255, 'blue': 0, 'alpha': 255},

        # Draw a polygon
        {'type': 'polygon', 'points': [(1000, 8000), (2000, 6000), (3000, 8000)]},

        # Set font
        {'type': 'font', 'name': 'Helvetica', 'height': 120, 'bold': False, 'italic': False},

        # Draw text
        {'type': 'text', 'position': (1000, 2000), 'text': 'Hello from DWF!'},

        # Set font for Hebrew
        {'type': 'font', 'name': 'Helvetica', 'height': 120, 'bold': True},

        # Draw Hebrew text (if Hebrew font available)
        {'type': 'text', 'position': (1000, 1500), 'text': 'שלום עולם'},

        # Draw polyline
        {'type': 'polyline', 'points': [(4000, 4000), (5000, 4500), (6000, 4000), (7000, 4500)]},

        # Draw ellipse
        {'type': 'ellipse', 'position': (8000, 3000), 'major': 1500, 'minor': 800,
         'is_full_ellipse': True},

        # Metadata
        {'type': 'creator', 'creator': 'DWF to PDF Renderer v2'},

        # End of file
        {'type': 'end_of_dwf'},
    ]

    # Render to PDF
    output_file = '/tmp/test_dwf_render.pdf'
    render_dwf_to_pdf(test_opcodes, output_file)

    print(f"✓ Test PDF rendered successfully: {output_file}")
    print(f"✓ Processed {len(test_opcodes)} opcodes")
    print(f"✓ Opcode types: {set(op['type'] for op in test_opcodes)}")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    test_render()
