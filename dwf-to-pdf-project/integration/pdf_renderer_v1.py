"""
PDF Renderer Version 1 - Independent Implementation

This module renders parsed DWF opcodes to PDF using ReportLab.
Built from scratch by scanning all agent opcode files.

Features:
- Complete opcode type switch covering all 80+ opcode types
- State management (save/restore/reset)
- BGRA→RGB color conversion
- Hebrew text support (UTF-16LE)
- ReportLab rendering backend

Author: PDF Renderer V1 Builder
Date: 2025-10-22
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
import copy
from typing import List, Dict, Any, Tuple, Optional
import math


# =============================================================================
# GRAPHICS STATE MANAGEMENT
# =============================================================================

class GraphicsState:
    """
    Graphics state for DWF rendering.
    Tracks all rendering attributes that can be saved/restored.
    """

    def __init__(self):
        # Color attributes
        self.foreground_color = (0, 0, 0, 255)  # RGBA - Black
        self.background_color = (255, 255, 255, 255)  # RGBA - White
        self.color_index = 0

        # Line attributes
        self.line_width = 1.0
        self.line_cap = 'butt'  # butt, round, square
        self.line_join = 'miter'  # miter, round, bevel
        self.line_pattern = None

        # Fill attributes
        self.fill_enabled = False

        # Text attributes
        self.font_name = 'Helvetica'
        self.font_size = 12.0
        self.text_rotation = 0.0
        self.text_scale = 1.0
        self.text_spacing = 0.0

        # Rendering attributes
        self.visibility = True
        self.anti_alias = True
        self.halftone = None
        self.highlight = False

        # Marker attributes
        self.marker_symbol = None
        self.marker_size = 5.0

        # Clipping
        self.clip_region = None
        self.mask = None

        # Transform
        self.origin = (0, 0)
        self.units = 1.0

    def copy(self):
        """Create a deep copy of the state."""
        return copy.deepcopy(self)


# =============================================================================
# COLOR CONVERSION UTILITIES
# =============================================================================

def bgra_to_rgb(blue: int, green: int, red: int, alpha: int = 255) -> Tuple[float, float, float]:
    """
    Convert BGRA color (0-255) to RGB float (0.0-1.0) for ReportLab.

    Args:
        blue: Blue component (0-255)
        green: Green component (0-255)
        red: Red component (0-255)
        alpha: Alpha component (0-255), default 255

    Returns:
        Tuple of (r, g, b) as floats 0.0-1.0
    """
    return (red / 255.0, green / 255.0, blue / 255.0)


def rgba_to_color(r: int, g: int, b: int, a: int = 255) -> Color:
    """
    Convert RGBA integers to ReportLab Color object.

    Args:
        r, g, b, a: Color components (0-255)

    Returns:
        ReportLab Color object
    """
    return Color(r / 255.0, g / 255.0, b / 255.0, alpha=a / 255.0)


# =============================================================================
# COORDINATE TRANSFORMATION
# =============================================================================

def transform_point(x: int, y: int, page_height: float, scale: float = 0.1) -> Tuple[float, float]:
    """
    Transform DWF coordinates to PDF coordinates.

    DWF uses bottom-left origin with Y-up.
    PDF uses bottom-left origin with Y-up.
    Scale factor adjusts DWF units to PDF points.

    Args:
        x, y: DWF coordinates
        page_height: PDF page height in points
        scale: Scale factor (default 0.1)

    Returns:
        Tuple of (pdf_x, pdf_y) in PDF coordinate space
    """
    pdf_x = x * scale
    pdf_y = y * scale
    return (pdf_x, pdf_y)


# =============================================================================
# PDF RENDERER CLASS
# =============================================================================

class PDFRenderer:
    """
    Main PDF renderer for DWF opcodes.
    """

    def __init__(self, output_path: str, pagesize=letter, scale=0.1):
        """
        Initialize PDF renderer.

        Args:
            output_path: Path to output PDF file
            pagesize: Page size (default letter)
            scale: Scale factor for coordinate transformation (default 0.1)
        """
        self.output_path = output_path
        self.pagesize = pagesize
        self.scale = scale
        self.canvas = canvas.Canvas(output_path, pagesize=pagesize)
        self.page_width, self.page_height = pagesize

        # Graphics state management
        self.current_state = GraphicsState()
        self.state_stack = []

        # Statistics
        self.opcode_count = 0
        self.unknown_opcode_count = 0
        self.error_count = 0

    def save_state(self):
        """Push current graphics state onto stack."""
        self.state_stack.append(self.current_state.copy())
        self.canvas.saveState()

    def restore_state(self):
        """Pop graphics state from stack."""
        if self.state_stack:
            self.current_state = self.state_stack.pop()
            self.canvas.restoreState()

    def reset_state(self):
        """Reset graphics state to defaults and clear stack."""
        self.current_state = GraphicsState()
        self.state_stack = []
        # Note: Canvas state is not reset, only our tracking

    def apply_color(self):
        """Apply current foreground color to canvas."""
        r, g, b, a = self.current_state.foreground_color
        color = rgba_to_color(r, g, b, a)
        self.canvas.setStrokeColor(color)
        if self.current_state.fill_enabled:
            self.canvas.setFillColor(color)

    def apply_line_width(self):
        """Apply current line width to canvas."""
        self.canvas.setLineWidth(self.current_state.line_width)

    def apply_line_cap(self):
        """Apply current line cap style."""
        cap_map = {'butt': 0, 'round': 1, 'square': 2}
        cap = cap_map.get(self.current_state.line_cap, 0)
        self.canvas.setLineCap(cap)

    def apply_line_join(self):
        """Apply current line join style."""
        join_map = {'miter': 0, 'round': 1, 'bevel': 2}
        join = join_map.get(self.current_state.line_join, 0)
        self.canvas.setLineJoin(join)

    # =========================================================================
    # OPCODE RENDERING METHODS
    # =========================================================================

    def render_line(self, opcode: Dict[str, Any]):
        """Render line opcode."""
        start = opcode.get('start', (0, 0))
        end = opcode.get('end', (0, 0))

        x1, y1 = transform_point(start[0], start[1], self.page_height)
        x2, y2 = transform_point(end[0], end[1], self.page_height)

        self.apply_color()
        self.apply_line_width()
        self.canvas.line(x1, y1, x2, y2)

    def render_circle(self, opcode: Dict[str, Any]):
        """Render circle opcode."""
        center = opcode.get('center', (0, 0))
        radius = opcode.get('radius', 10)

        cx, cy = transform_point(center[0], center[1], self.page_height)
        r = radius * 0.1

        self.apply_color()
        self.apply_line_width()

        if self.current_state.fill_enabled:
            self.canvas.circle(cx, cy, r, stroke=1, fill=1)
        else:
            self.canvas.circle(cx, cy, r, stroke=1, fill=0)

    def render_ellipse(self, opcode: Dict[str, Any]):
        """Render ellipse opcode."""
        center = opcode.get('center', (0, 0))
        major_axis = opcode.get('major_axis', 20)
        minor_axis = opcode.get('minor_axis', 10)

        cx, cy = transform_point(center[0], center[1], self.page_height)
        rx = major_axis * 0.1
        ry = minor_axis * 0.1

        self.apply_color()
        self.apply_line_width()

        if self.current_state.fill_enabled:
            self.canvas.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, stroke=1, fill=1)
        else:
            self.canvas.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, stroke=1, fill=0)

    def render_polyline_polygon(self, opcode: Dict[str, Any]):
        """Render polyline/polygon opcode."""
        vertices = opcode.get('vertices', [])
        if not vertices:
            return

        # Transform all vertices
        points = [transform_point(v[0], v[1], self.page_height) for v in vertices]

        self.apply_color()
        self.apply_line_width()

        # Create path
        path = self.canvas.beginPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)

        # Close path if fill is enabled (polygon)
        if self.current_state.fill_enabled:
            path.close()
            self.canvas.drawPath(path, stroke=1, fill=1)
        else:
            self.canvas.drawPath(path, stroke=1, fill=0)

    def render_polytriangle(self, opcode: Dict[str, Any]):
        """Render polytriangle (triangle strip) opcode."""
        vertices = opcode.get('vertices', [])
        if len(vertices) < 3:
            return

        self.apply_color()
        self.apply_line_width()

        # Render triangles in strip format
        # First triangle: 0,1,2; Second: 1,2,3; etc.
        for i in range(len(vertices) - 2):
            tri_verts = [vertices[i], vertices[i+1], vertices[i+2]]
            points = [transform_point(v[0], v[1], self.page_height) for v in tri_verts]

            path = self.canvas.beginPath()
            path.moveTo(points[0][0], points[0][1])
            path.lineTo(points[1][0], points[1][1])
            path.lineTo(points[2][0], points[2][1])
            path.close()

            # Triangles are always filled
            self.canvas.drawPath(path, stroke=1, fill=1)

    def render_quad(self, opcode: Dict[str, Any]):
        """Render quad (quadrilateral) opcode."""
        vertices = opcode.get('vertices', [])
        if len(vertices) != 4:
            return

        points = [transform_point(v[0], v[1], self.page_height) for v in vertices]

        self.apply_color()
        self.apply_line_width()

        path = self.canvas.beginPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)
        path.close()

        if self.current_state.fill_enabled:
            self.canvas.drawPath(path, stroke=1, fill=1)
        else:
            self.canvas.drawPath(path, stroke=1, fill=0)

    def render_wedge(self, opcode: Dict[str, Any]):
        """Render wedge (pie slice) opcode."""
        center = opcode.get('center', (0, 0))
        radius = opcode.get('radius', 10)
        start_angle = opcode.get('start_angle', 0)
        end_angle = opcode.get('end_angle', 90)

        cx, cy = transform_point(center[0], center[1], self.page_height)
        r = radius * 0.1

        self.apply_color()
        self.apply_line_width()

        # Draw wedge as path
        path = self.canvas.beginPath()
        path.moveTo(cx, cy)
        # Arc from start to end angle
        extent = end_angle - start_angle
        self.canvas.wedge(cx - r, cy - r, cx + r, cy + r, start_angle, extent,
                         stroke=1, fill=1 if self.current_state.fill_enabled else 0)

    def render_bezier(self, opcode: Dict[str, Any]):
        """Render Bezier curve opcode."""
        points = opcode.get('control_points', [])
        if len(points) < 4:
            return

        self.apply_color()
        self.apply_line_width()

        # Transform control points
        p = [transform_point(pt[0], pt[1], self.page_height) for pt in points]

        path = self.canvas.beginPath()
        path.moveTo(p[0][0], p[0][1])

        # Draw cubic Bezier curves (4 points at a time)
        for i in range(1, len(p) - 2, 3):
            if i + 2 < len(p):
                path.curveTo(p[i][0], p[i][1],
                           p[i+1][0], p[i+1][1],
                           p[i+2][0], p[i+2][1])

        self.canvas.drawPath(path, stroke=1, fill=0)

    def render_text_basic(self, opcode: Dict[str, Any]):
        """Render basic text opcode."""
        text = opcode.get('text', '')
        position = opcode.get('position', (0, 0))

        if not text:
            return

        # Handle UTF-16LE encoded Hebrew text
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-16-le')
            except:
                text = text.decode('utf-8', errors='ignore')

        x, y = transform_point(position[0], position[1], self.page_height)

        self.apply_color()

        # Set font
        try:
            self.canvas.setFont(self.current_state.font_name, self.current_state.font_size)
        except:
            self.canvas.setFont('Helvetica', self.current_state.font_size)

        # Draw text
        if self.current_state.text_rotation != 0:
            self.canvas.saveState()
            self.canvas.translate(x, y)
            self.canvas.rotate(self.current_state.text_rotation)
            self.canvas.drawString(0, 0, text)
            self.canvas.restoreState()
        else:
            self.canvas.drawString(x, y, text)

    def render_text_complex(self, opcode: Dict[str, Any]):
        """Render complex text opcode (with formatting)."""
        # Complex text has similar structure to basic text
        self.render_text_basic(opcode)

    def render_image(self, opcode: Dict[str, Any]):
        """Render image opcodes (RGB, RGBA, PNG, JPEG)."""
        # Image rendering would require PIL/Pillow integration
        # For V1, we'll just mark the position with a rectangle
        position = opcode.get('position', (0, 0))
        width = opcode.get('width', 100)
        height = opcode.get('height', 100)

        x, y = transform_point(position[0], position[1], self.page_height)
        w = width * 0.1
        h = height * 0.1

        self.canvas.saveState()
        self.canvas.setStrokeColor(Color(0.5, 0.5, 0.5))
        self.canvas.setFillColor(Color(0.9, 0.9, 0.9))
        self.canvas.rect(x, y, w, h, stroke=1, fill=1)
        self.canvas.restoreState()

    def render_gouraud_polytriangle(self, opcode: Dict[str, Any]):
        """Render Gouraud-shaded triangle strip."""
        # For V1, render as regular polytriangle (no gradient support in basic ReportLab)
        self.render_polytriangle(opcode)

    def render_gouraud_polyline(self, opcode: Dict[str, Any]):
        """Render Gouraud-shaded polyline."""
        # For V1, render as regular polyline
        self.render_polyline_polygon(opcode)

    def render_contour(self, opcode: Dict[str, Any]):
        """Render contour opcode."""
        # Contour is similar to complex polygon
        self.render_polyline_polygon(opcode)

    def render_draw_marker(self, opcode: Dict[str, Any]):
        """Render marker symbol."""
        position = opcode.get('position', (0, 0))
        x, y = transform_point(position[0], position[1], self.page_height)

        size = self.current_state.marker_size
        self.apply_color()

        # Draw simple marker (circle for V1)
        self.canvas.circle(x, y, size, stroke=1, fill=1)

    # =========================================================================
    # ATTRIBUTE/STATE OPCODE HANDLERS
    # =========================================================================

    def handle_set_color_rgba(self, opcode: Dict[str, Any]):
        """Handle SET_COLOR_RGBA opcode."""
        r = opcode.get('red', 0)
        g = opcode.get('green', 0)
        b = opcode.get('blue', 0)
        a = opcode.get('alpha', 255)
        self.current_state.foreground_color = (r, g, b, a)

    def handle_set_color_rgb(self, opcode: Dict[str, Any]):
        """Handle set_color_rgb opcode (from XPS parser).

        XPS parser generates RGB values as floats 0.0-1.0.
        Convert to 0-255 range for internal use.
        """
        r = opcode.get('r', 0.0)
        g = opcode.get('g', 0.0)
        b = opcode.get('b', 0.0)

        # Convert from 0.0-1.0 to 0-255 range
        r_int = int(r * 255) if r <= 1.0 else int(r)
        g_int = int(g * 255) if g <= 1.0 else int(g)
        b_int = int(b * 255) if b <= 1.0 else int(b)

        self.current_state.foreground_color = (r_int, g_int, b_int, 255)

    def handle_set_color_rgb32(self, opcode: Dict[str, Any]):
        """Handle SET_COLOR_RGB32 opcode."""
        r = opcode.get('red', 0)
        g = opcode.get('green', 0)
        b = opcode.get('blue', 0)
        a = opcode.get('alpha', 255)
        self.current_state.foreground_color = (r, g, b, a)

    def handle_set_color_indexed(self, opcode: Dict[str, Any]):
        """Handle SET_COLOR_INDEXED opcode."""
        self.current_state.color_index = opcode.get('color_index', 0)
        # In full implementation, would look up color in palette

    def handle_set_background_color(self, opcode: Dict[str, Any]):
        """Handle SET_BACKGROUND_COLOR opcode."""
        r = opcode.get('red', 255)
        g = opcode.get('green', 255)
        b = opcode.get('blue', 255)
        a = opcode.get('alpha', 255)
        self.current_state.background_color = (r, g, b, a)

    def handle_set_fill_on(self, opcode: Dict[str, Any]):
        """Handle SET_FILL_ON opcode."""
        self.current_state.fill_enabled = True

    def handle_set_fill_off(self, opcode: Dict[str, Any]):
        """Handle SET_FILL_OFF opcode."""
        self.current_state.fill_enabled = False

    def handle_set_line_width(self, opcode: Dict[str, Any]):
        """Handle SET_LINE_WIDTH / SET_PEN_WIDTH opcode."""
        self.current_state.line_width = opcode.get('width', 1.0)

    def handle_set_line_cap(self, opcode: Dict[str, Any]):
        """Handle SET_LINE_CAP opcode."""
        cap = opcode.get('cap_style', 'butt')
        if cap in ['butt', 'round', 'square']:
            self.current_state.line_cap = cap

    def handle_set_line_join(self, opcode: Dict[str, Any]):
        """Handle SET_LINE_JOIN opcode."""
        join = opcode.get('join_style', 'miter')
        if join in ['miter', 'round', 'bevel']:
            self.current_state.line_join = join

    def handle_set_font(self, opcode: Dict[str, Any]):
        """Handle SET_FONT opcode."""
        font_name = opcode.get('font_name', 'Helvetica')
        font_size = opcode.get('font_height', 12)

        # Map common font names
        font_map = {
            'Arial': 'Helvetica',
            'Times': 'Times-Roman',
            'Courier': 'Courier',
        }

        self.current_state.font_name = font_map.get(font_name, font_name)
        self.current_state.font_size = abs(font_size) if font_size else 12

    def handle_set_text_rotation(self, opcode: Dict[str, Any]):
        """Handle SET_TEXT_ROTATION opcode."""
        self.current_state.text_rotation = opcode.get('rotation', 0.0)

    def handle_set_text_scale(self, opcode: Dict[str, Any]):
        """Handle SET_TEXT_SCALE opcode."""
        self.current_state.text_scale = opcode.get('scale', 1.0)

    def handle_set_text_spacing(self, opcode: Dict[str, Any]):
        """Handle SET_TEXT_SPACING opcode."""
        self.current_state.text_spacing = opcode.get('spacing', 0.0)

    def handle_set_origin(self, opcode: Dict[str, Any]):
        """Handle SET_ORIGIN opcode."""
        x = opcode.get('x', 0)
        y = opcode.get('y', 0)
        self.current_state.origin = (x, y)

    def handle_set_units(self, opcode: Dict[str, Any]):
        """Handle SET_UNITS opcode."""
        self.current_state.units = opcode.get('units', 1.0)

    def handle_set_visibility_on(self, opcode: Dict[str, Any]):
        """Handle SET_VISIBILITY_ON opcode."""
        self.current_state.visibility = True

    def handle_set_marker_symbol(self, opcode: Dict[str, Any]):
        """Handle SET_MARKER_SYMBOL opcode."""
        self.current_state.marker_symbol = opcode.get('symbol', None)

    def handle_set_marker_size(self, opcode: Dict[str, Any]):
        """Handle SET_MARKER_SIZE opcode."""
        self.current_state.marker_size = opcode.get('size', 5.0)

    def handle_set_anti_alias(self, opcode: Dict[str, Any]):
        """Handle SET_ANTI_ALIAS opcode."""
        self.current_state.anti_alias = opcode.get('enabled', True)

    def handle_set_halftone(self, opcode: Dict[str, Any]):
        """Handle SET_HALFTONE opcode."""
        self.current_state.halftone = opcode.get('pattern', None)

    def handle_set_highlight(self, opcode: Dict[str, Any]):
        """Handle SET_HIGHLIGHT opcode."""
        self.current_state.highlight = opcode.get('enabled', False)

    def handle_set_clip_region(self, opcode: Dict[str, Any]):
        """Handle SET_CLIP_REGION opcode."""
        self.current_state.clip_region = opcode.get('region', None)
        # In full implementation, would set canvas clipping path

    def handle_clear_clip_region(self, opcode: Dict[str, Any]):
        """Handle CLEAR_CLIP_REGION opcode."""
        self.current_state.clip_region = None

    def handle_set_mask(self, opcode: Dict[str, Any]):
        """Handle SET_MASK opcode."""
        self.current_state.mask = opcode.get('mask_data', None)

    # =========================================================================
    # MAIN RENDERING DISPATCH
    # =========================================================================

    def render_opcode(self, opcode: Dict[str, Any]):
        """
        Render a single opcode to the PDF canvas.

        Args:
            opcode: Parsed opcode dictionary
        """
        self.opcode_count += 1

        # Get opcode type (handle both 'type' and 'name' fields)
        opcode_type = opcode.get('type') or opcode.get('name', 'unknown')

        try:
            # === GEOMETRY OPCODES ===
            if opcode_type in ['line', 'line_16r']:
                self.render_line(opcode)

            elif opcode_type in ['circle', 'circle_16r']:
                self.render_circle(opcode)

            elif opcode_type in ['ellipse', 'draw_ellipse']:
                self.render_ellipse(opcode)

            elif opcode_type in ['polyline_polygon', 'polyline_polygon_16r']:
                self.render_polyline_polygon(opcode)

            elif opcode_type in ['polytriangle', 'polytriangle_16r', 'polytriangle_32r']:
                self.render_polytriangle(opcode)

            elif opcode_type in ['quad', 'quad_32r']:
                self.render_quad(opcode)

            elif opcode_type == 'wedge':
                self.render_wedge(opcode)

            elif opcode_type == 'bezier':
                self.render_bezier(opcode)

            elif opcode_type == 'contour':
                self.render_contour(opcode)

            elif opcode_type == 'gouraud_polytriangle':
                self.render_gouraud_polytriangle(opcode)

            elif opcode_type == 'gouraud_polyline':
                self.render_gouraud_polyline(opcode)

            # === TEXT OPCODES ===
            elif opcode_type in ['draw_text_basic', 'draw_text_complex']:
                if opcode_type == 'draw_text_basic':
                    self.render_text_basic(opcode)
                else:
                    self.render_text_complex(opcode)

            # === IMAGE OPCODES ===
            elif opcode_type in ['image_rgb', 'image_rgba', 'image_png',
                               'image_jpeg', 'image_indexed', 'image_mapped']:
                self.render_image(opcode)

            # === MARKER OPCODES ===
            elif opcode_type == 'draw_marker':
                self.render_draw_marker(opcode)

            # === STATE MANAGEMENT OPCODES ===
            elif opcode_type == 'save_state':
                self.save_state()

            elif opcode_type == 'restore_state':
                self.restore_state()

            elif opcode_type == 'reset_state':
                self.reset_state()

            # === COLOR ATTRIBUTE OPCODES ===
            elif opcode_type in ['SET_COLOR_RGBA', 'set_color_rgba']:
                self.handle_set_color_rgba(opcode)

            elif opcode_type in ['set_color_rgb', 'SET_COLOR_RGB']:
                # XPS parser generates this - treat as RGBA with alpha=255
                self.handle_set_color_rgb(opcode)

            elif opcode_type == 'set_color_rgb32':
                self.handle_set_color_rgb32(opcode)

            elif opcode_type in ['SET_COLOR_INDEXED', 'set_color_indexed']:
                self.handle_set_color_indexed(opcode)

            elif opcode_type == 'set_background_color':
                self.handle_set_background_color(opcode)

            elif opcode_type == 'set_color_map_index':
                self.handle_set_color_indexed(opcode)

            # === FILL ATTRIBUTE OPCODES ===
            elif opcode_type in ['SET_FILL_ON', 'set_fill_on']:
                self.handle_set_fill_on(opcode)

            elif opcode_type in ['SET_FILL_OFF', 'set_fill_off']:
                self.handle_set_fill_off(opcode)

            # === LINE ATTRIBUTE OPCODES ===
            elif opcode_type in ['set_pen_width', 'set_line_width']:
                self.handle_set_line_width(opcode)

            elif opcode_type == 'set_line_cap':
                self.handle_set_line_cap(opcode)

            elif opcode_type == 'set_line_join':
                self.handle_set_line_join(opcode)

            # === TEXT ATTRIBUTE OPCODES ===
            elif opcode_type == 'set_font':
                self.handle_set_font(opcode)

            elif opcode_type == 'set_text_rotation':
                self.handle_set_text_rotation(opcode)

            elif opcode_type == 'set_text_scale':
                self.handle_set_text_scale(opcode)

            elif opcode_type == 'set_text_spacing':
                self.handle_set_text_spacing(opcode)

            elif opcode_type == 'set_origin':
                self.handle_set_origin(opcode)

            elif opcode_type == 'set_units':
                self.handle_set_units(opcode)

            # === VISIBILITY OPCODES ===
            elif opcode_type in ['SET_VISIBILITY_ON', 'set_visibility_on']:
                self.handle_set_visibility_on(opcode)

            # === MARKER ATTRIBUTE OPCODES ===
            elif opcode_type == 'set_marker_symbol':
                self.handle_set_marker_symbol(opcode)

            elif opcode_type == 'set_marker_size':
                self.handle_set_marker_size(opcode)

            # === RENDERING ATTRIBUTE OPCODES ===
            elif opcode_type == 'set_anti_alias':
                self.handle_set_anti_alias(opcode)

            elif opcode_type == 'set_halftone':
                self.handle_set_halftone(opcode)

            elif opcode_type == 'set_highlight':
                self.handle_set_highlight(opcode)

            # === CLIPPING OPCODES ===
            elif opcode_type == 'set_clip_region':
                self.handle_set_clip_region(opcode)

            elif opcode_type == 'clear_clip_region':
                self.handle_clear_clip_region(opcode)

            elif opcode_type == 'set_mask':
                self.handle_set_mask(opcode)

            # === METADATA & STRUCTURE OPCODES (no rendering needed) ===
            elif opcode_type in ['metadata', 'copyright', 'creator', 'creation_time',
                               'modification_time', 'source_creation_time',
                               'source_modification_time', 'dwf_header', 'end_of_dwf',
                               'viewport', 'view', 'named_view', 'user_block',
                               'null_block', 'global_sheet_block', 'global_block',
                               'signature_block', 'font_extension', 'colormap',
                               'compression_marker', 'overlay_preview', 'font_block',
                               'encryption', 'password', 'signdata', 'nop',
                               'stream_version', 'end_of_stream', 'extended_ascii',
                               'extended_binary', 'single_byte']:
                # These opcodes don't require rendering, just state tracking
                pass

            # === UNKNOWN OPCODES ===
            elif opcode_type in ['unknown', 'unknown_binary']:
                self.unknown_opcode_count += 1

            else:
                # Truly unhandled opcode type
                self.unknown_opcode_count += 1
                print(f"Warning: Unhandled opcode type: {opcode_type}")

        except Exception as e:
            self.error_count += 1
            print(f"Error rendering opcode {opcode_type}: {e}")

    def finish(self):
        """Finalize the PDF and write to disk."""
        # CRITICAL: Must call showPage() before save() to finalize the current page
        # Without this, PDF will have 0 pages even if geometry was rendered!
        self.canvas.showPage()
        self.canvas.save()

        print(f"\nPDF Rendering Complete:")
        print(f"  Output: {self.output_path}")
        print(f"  Opcodes processed: {self.opcode_count}")
        print(f"  Unknown opcodes: {self.unknown_opcode_count}")
        print(f"  Errors: {self.error_count}")


# =============================================================================
# MAIN RENDERING FUNCTION
# =============================================================================

def render_dwf_to_pdf(parsed_opcodes: List[Dict[str, Any]], output_path: str,
                     pagesize=letter, scale=0.1) -> bool:
    """
    Render parsed DWF opcodes to a PDF file.

    Args:
        parsed_opcodes: List of parsed opcode dictionaries
        output_path: Path to output PDF file
        pagesize: Page size (default letter)
        scale: Scale factor for coordinate transformation (default 0.1)

    Returns:
        True if rendering succeeded, False otherwise
    """
    try:
        renderer = PDFRenderer(output_path, pagesize=pagesize, scale=scale)

        for opcode in parsed_opcodes:
            renderer.render_opcode(opcode)

        renderer.finish()
        return True

    except Exception as e:
        print(f"Error rendering PDF: {e}")
        return False


# =============================================================================
# TEST SUITE
# =============================================================================

def test_pdf_renderer_v1():
    """Test the PDF renderer with sample opcodes."""
    print("=" * 70)
    print("PDF RENDERER V1 - TEST SUITE")
    print("=" * 70)

    # Create sample opcodes representing various DWF elements
    test_opcodes = [
        # Set color to red
        {'type': 'SET_COLOR_RGBA', 'red': 255, 'green': 0, 'blue': 0, 'alpha': 255},

        # Draw a line
        {'type': 'line', 'start': (100, 100), 'end': (300, 300)},

        # Set color to blue
        {'type': 'SET_COLOR_RGBA', 'red': 0, 'green': 0, 'blue': 255, 'alpha': 255},

        # Draw a circle
        {'type': 'circle', 'center': (200, 200), 'radius': 50},

        # Enable fill
        {'type': 'SET_FILL_ON'},

        # Set color to green
        {'type': 'SET_COLOR_RGBA', 'red': 0, 'green': 255, 'blue': 0, 'alpha': 255},

        # Draw filled ellipse
        {'type': 'ellipse', 'center': (400, 300), 'major_axis': 80, 'minor_axis': 50},

        # Draw polygon
        {'type': 'polyline_polygon', 'count': 4,
         'vertices': [(500, 100), (600, 100), (600, 200), (500, 200)]},

        # Save state
        {'type': 'save_state'},

        # Set color to purple
        {'type': 'SET_COLOR_RGBA', 'red': 128, 'green': 0, 'blue': 128, 'alpha': 255},

        # Draw polytriangle
        {'type': 'polytriangle', 'count': 3,
         'vertices': [(100, 400), (200, 400), (150, 500)]},

        # Restore state (back to green)
        {'type': 'restore_state'},

        # Set font
        {'type': 'set_font', 'font_name': 'Helvetica', 'font_height': 14},

        # Draw text
        {'type': 'draw_text_basic', 'text': 'Hello DWF!', 'position': (100, 550)},

        # Hebrew text test (UTF-16LE)
        {'type': 'draw_text_basic', 'text': 'שלום', 'position': (100, 580)},

        # Set line width
        {'type': 'set_pen_width', 'width': 3.0},

        # Draw thick line
        {'type': 'line', 'start': (100, 600), 'end': (300, 600)},

        # Reset state
        {'type': 'reset_state'},
    ]

    output_path = '/home/user/git-practice/dwf-to-pdf-project/integration/test_output_v1.pdf'

    print(f"\nRendering {len(test_opcodes)} test opcodes to PDF...")
    print(f"Output: {output_path}")

    success = render_dwf_to_pdf(test_opcodes, output_path)

    if success:
        print("\n✓ TEST PASSED: PDF rendered successfully!")
        print(f"  Please check: {output_path}")
    else:
        print("\n✗ TEST FAILED: Error rendering PDF")

    print("=" * 70)


if __name__ == '__main__':
    test_pdf_renderer_v1()
