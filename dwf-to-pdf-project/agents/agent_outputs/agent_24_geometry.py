"""
Agent 24: Extended ASCII Geometry Opcodes Implementation
========================================================

This module implements 6 Extended ASCII geometry drawing opcodes for DWF to PDF conversion.

Opcodes Implemented:
1. WD_EXAO_DRAW_CIRCLE (258) - "(Circle" - Circle and arc drawing
2. WD_EXAO_DRAW_ELLIPSE (270) - "(Ellipse" - Ellipse drawing
3. WD_EXAO_DRAW_CONTOUR (259) - "(Contour" - Contour/polygon drawing
4. WD_EXAO_GOURAUD_POLYTRIANGLE (364) - "(Gouraud" - Gouraud shaded triangles
5. WD_EXAO_GOURAUD_POLYLINE (367) - "(GourLine" - Gouraud shaded polylines
6. WD_EXAO_BEZIER (368) - "(Bezier" - Bezier curve drawing

References:
- /dwf-toolkit-source/develop/global/src/dwf/whiptk/ellipse.cpp (lines 506-530, 531-558)
- /dwf-toolkit-source/develop/global/src/dwf/whiptk/contour_set.cpp (lines 367-383, 495-568)
- /dwf-toolkit-source/develop/global/src/dwf/whiptk/gouraud_pointset.cpp (lines 143-168, 288-357)
- /dwf-toolkit-source/develop/global/src/dwf/whiptk/gouraud_polytri.cpp (lines 84-87, 120-133)
- /dwf-toolkit-source/develop/global/src/dwf/whiptk/gouraud_polyline.cpp (lines 75-78, 117-130)
- /dwf-toolkit-source/develop/global/src/dwf/whiptk/preload.h (line 107)

Author: Agent 24
Date: 2025-10-22
"""

import struct
import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


# Constants
PI = math.pi
DEGREES_TO_RADIANS = PI / 180.0
# DWF uses 16-bit angles where 0x10000 (65536) = 360 degrees
ANGLE_UNITS_PER_DEGREE = 65536.0 / 360.0
ANGLE_UNITS_PER_RADIAN = 65536.0 / (2 * PI)

# Maximum point set sizes
WD_MAXIMUM_POINT_SET_SIZE = 256 + 65535


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class LogicalPoint:
    """Represents a 2D point in logical coordinates."""
    x: int
    y: int

    def __str__(self):
        return f"({self.x},{self.y})"

    def to_tuple(self):
        return (self.x, self.y)


@dataclass
class RGBA32:
    """Represents a 32-bit RGBA color."""
    r: int  # 0-255
    g: int  # 0-255
    b: int  # 0-255
    a: int  # 0-255 (alpha/opacity)

    def __str__(self):
        return f"rgba({self.r},{self.g},{self.b},{self.a})"

    def to_hex(self):
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def to_tuple(self):
        return (self.r, self.g, self.b, self.a)

    @classmethod
    def from_int(cls, value: int):
        """Create RGBA32 from a 32-bit integer (little-endian RGBA)."""
        r = value & 0xFF
        g = (value >> 8) & 0xFF
        b = (value >> 16) & 0xFF
        a = (value >> 24) & 0xFF
        return cls(r, g, b, a)


@dataclass
class Circle:
    """Represents a circle or circular arc."""
    position: LogicalPoint
    radius: int
    start_angle: int = 0        # In DWF angle units (0x10000 = 360°)
    end_angle: int = 0x10000    # Full circle by default

    def is_full_circle(self) -> bool:
        """Check if this represents a full circle (not an arc)."""
        return self.start_angle == self.end_angle or \
               (self.start_angle == 0 and self.end_angle == 0x10000)

    def start_degrees(self) -> float:
        """Get start angle in degrees."""
        return (self.start_angle & 0xFFFF) / ANGLE_UNITS_PER_DEGREE

    def end_degrees(self) -> float:
        """Get end angle in degrees."""
        return (self.end_angle & 0x1FFFF) / ANGLE_UNITS_PER_DEGREE


@dataclass
class Ellipse:
    """Represents an ellipse or elliptical arc."""
    position: LogicalPoint
    major: int          # Major axis radius
    minor: int          # Minor axis radius
    start_angle: int = 0        # In DWF angle units
    end_angle: int = 0          # 0 = full ellipse
    tilt: int = 0               # Rotation angle in DWF angle units

    def is_circle(self) -> bool:
        """Check if this is actually a circle (major == minor)."""
        return self.major == self.minor

    def is_full_ellipse(self) -> bool:
        """Check if this represents a full ellipse (not an arc)."""
        return self.start_angle == self.end_angle

    def tilt_degrees(self) -> float:
        """Get tilt angle in degrees."""
        return (self.tilt & 0xFFFF) / ANGLE_UNITS_PER_DEGREE


@dataclass
class Contour:
    """Represents a contour set (polygon with possible holes)."""
    num_contours: int
    counts: List[int]           # Number of points per contour
    points: List[LogicalPoint]  # All points for all contours

    def total_points(self) -> int:
        """Get total number of points across all contours."""
        return sum(self.counts)


@dataclass
class GouraudPoint:
    """Represents a point with Gouraud shading (point + color)."""
    point: LogicalPoint
    color: RGBA32


@dataclass
class GouraudPolytriangle:
    """Represents Gouraud-shaded triangles."""
    count: int
    points: List[GouraudPoint]

    def num_triangles(self) -> int:
        """Calculate number of triangles (vertices / 3)."""
        return self.count // 3


@dataclass
class GouraudPolyline:
    """Represents a Gouraud-shaded polyline."""
    count: int
    points: List[GouraudPoint]


@dataclass
class Bezier:
    """Represents a Bezier curve."""
    count: int
    control_points: List[LogicalPoint]

    def num_curves(self) -> int:
        """
        Calculate number of Bezier curves.
        Typically cubic Bezier uses 4 points per curve (first point shared).
        """
        if self.count < 4:
            return 0
        return (self.count - 1) // 3


# ============================================================================
# Parsing Utilities
# ============================================================================

class ASCIIParser:
    """Helper class for parsing ASCII data fields."""

    @staticmethod
    def parse_int(data: str) -> int:
        """Parse an integer from ASCII string."""
        data = data.strip()
        if data.startswith('-'):
            return -int(data[1:])
        return int(data)

    @staticmethod
    def parse_point(data: str) -> LogicalPoint:
        """
        Parse a logical point in format: x,y
        Example: "100,200"
        """
        parts = data.strip().split(',')
        if len(parts) != 2:
            raise ValueError(f"Invalid point format: {data}")
        x = ASCIIParser.parse_int(parts[0])
        y = ASCIIParser.parse_int(parts[1])
        return LogicalPoint(x, y)

    @staticmethod
    def parse_color(data: str) -> RGBA32:
        """
        Parse RGBA32 color.
        Format can be: "r,g,b,a" or a single integer value
        """
        data = data.strip()
        if ',' in data:
            parts = data.split(',')
            if len(parts) == 4:
                r, g, b, a = [int(p) for p in parts]
                return RGBA32(r, g, b, a)
            elif len(parts) == 3:
                r, g, b = [int(p) for p in parts]
                return RGBA32(r, g, b, 255)
        else:
            # Single integer value
            val = int(data)
            return RGBA32.from_int(val)

        raise ValueError(f"Invalid color format: {data}")

    @staticmethod
    def split_fields(data: str) -> List[str]:
        """
        Split ASCII data into fields, respecting nested parentheses.
        Fields are separated by whitespace.
        """
        fields = []
        current = []
        depth = 0

        for char in data:
            if char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                if depth < 0:
                    break  # End of opcode data
                current.append(char)
            elif char in ' \t\n\r' and depth == 0:
                if current:
                    fields.append(''.join(current))
                    current = []
            else:
                current.append(char)

        if current:
            fields.append(''.join(current))

        return fields


# ============================================================================
# Opcode Handlers
# ============================================================================

def handle_circle(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Handle WD_EXAO_DRAW_CIRCLE opcode: "(Circle position radius start,end)"

    Format (ellipse.cpp lines 506-530):
        (Circle position radius start_angle,end_angle)

    Args:
        stream: Input byte stream
        opcode_name: Should be "Circle"

    Returns:
        Dictionary with parsed circle data
    """
    # Read until closing paren
    data_bytes = []
    depth = 1

    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in Circle opcode")

        char = byte.decode('ascii')
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                break

        data_bytes.append(char)

    data = ''.join(data_bytes).strip()
    fields = ASCIIParser.split_fields(data)

    if len(fields) < 2:
        raise ValueError(f"Circle requires at least 2 fields (position, radius), got {len(fields)}")

    # Parse position
    position = ASCIIParser.parse_point(fields[0])

    # Parse radius
    radius = ASCIIParser.parse_int(fields[1])

    # Parse optional angles
    start_angle = 0
    end_angle = 0

    if len(fields) >= 3:
        # Angles are in format "start,end"
        angle_parts = fields[2].split(',')
        if len(angle_parts) == 2:
            start_angle = ASCIIParser.parse_int(angle_parts[0]) & 0xFFFF
            end_angle = ASCIIParser.parse_int(angle_parts[1]) & 0x1FFFF

    circle = Circle(position, radius, start_angle, end_angle)

    return {
        'type': 'circle',
        'opcode_id': 258,
        'opcode_name': 'WD_EXAO_DRAW_CIRCLE',
        'data': circle,
        'position': circle.position.to_tuple(),
        'radius': circle.radius,
        'start_angle_deg': circle.start_degrees(),
        'end_angle_deg': circle.end_degrees(),
        'is_full_circle': circle.is_full_circle()
    }


def handle_ellipse(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Handle WD_EXAO_DRAW_ELLIPSE opcode: "(Ellipse position major,minor start,end tilt)"

    Format (ellipse.cpp lines 531-558):
        (Ellipse position major,minor start_angle,end_angle tilt)

    Args:
        stream: Input byte stream
        opcode_name: Should be "Ellipse"

    Returns:
        Dictionary with parsed ellipse data
    """
    # Read until closing paren
    data_bytes = []
    depth = 1

    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in Ellipse opcode")

        char = byte.decode('ascii')
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                break

        data_bytes.append(char)

    data = ''.join(data_bytes).strip()
    fields = ASCIIParser.split_fields(data)

    if len(fields) < 4:
        raise ValueError(f"Ellipse requires at least 4 fields, got {len(fields)}")

    # Parse position
    position = ASCIIParser.parse_point(fields[0])

    # Parse major,minor
    axis_parts = fields[1].split(',')
    if len(axis_parts) != 2:
        raise ValueError(f"Invalid ellipse axes format: {fields[1]}")
    major = ASCIIParser.parse_int(axis_parts[0])
    minor = ASCIIParser.parse_int(axis_parts[1])

    # Parse start,end angles
    angle_parts = fields[2].split(',')
    if len(angle_parts) != 2:
        raise ValueError(f"Invalid ellipse angles format: {fields[2]}")
    start_angle = ASCIIParser.parse_int(angle_parts[0]) & 0xFFFF
    end_angle = ASCIIParser.parse_int(angle_parts[1]) & 0x1FFFF

    # Parse tilt
    tilt = ASCIIParser.parse_int(fields[3]) & 0xFFFF

    ellipse = Ellipse(position, major, minor, start_angle, end_angle, tilt)

    return {
        'type': 'ellipse',
        'opcode_id': 270,
        'opcode_name': 'WD_EXAO_DRAW_ELLIPSE',
        'data': ellipse,
        'position': ellipse.position.to_tuple(),
        'major': ellipse.major,
        'minor': ellipse.minor,
        'start_angle_deg': (start_angle / ANGLE_UNITS_PER_DEGREE),
        'end_angle_deg': (end_angle / ANGLE_UNITS_PER_DEGREE),
        'tilt_deg': ellipse.tilt_degrees(),
        'is_circle': ellipse.is_circle(),
        'is_full_ellipse': ellipse.is_full_ellipse()
    }


def handle_contour(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Handle WD_EXAO_DRAW_CONTOUR opcode: "(Contour num_contours count1 ... countN point1 ... pointN)"

    Format (contour_set.cpp lines 367-383, 495-568):
        (Contour num_contours count1 count2 ... countN point1 point2 ... pointN)

    A contour set can represent complex polygons with holes.
    Each contour has a count followed by that many points.

    Args:
        stream: Input byte stream
        opcode_name: Should be "Contour"

    Returns:
        Dictionary with parsed contour data
    """
    # Read until closing paren
    data_bytes = []
    depth = 1

    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in Contour opcode")

        char = byte.decode('ascii')
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                break

        data_bytes.append(char)

    data = ''.join(data_bytes).strip()
    fields = ASCIIParser.split_fields(data)

    if len(fields) < 2:
        raise ValueError(f"Contour requires at least 2 fields, got {len(fields)}")

    # Parse number of contours
    num_contours = ASCIIParser.parse_int(fields[0])

    if num_contours < 1:
        raise ValueError(f"Invalid number of contours: {num_contours}")

    # Parse counts for each contour
    counts = []
    field_idx = 1
    for i in range(num_contours):
        if field_idx >= len(fields):
            raise ValueError(f"Missing count for contour {i}")
        count = ASCIIParser.parse_int(fields[field_idx])
        counts.append(count)
        field_idx += 1

    total_points = sum(counts)

    # Parse all points
    points = []
    for i in range(total_points):
        if field_idx >= len(fields):
            raise ValueError(f"Missing point {i} (expected {total_points} points)")
        point = ASCIIParser.parse_point(fields[field_idx])
        points.append(point)
        field_idx += 1

    contour = Contour(num_contours, counts, points)

    return {
        'type': 'contour',
        'opcode_id': 259,
        'opcode_name': 'WD_EXAO_DRAW_CONTOUR',
        'data': contour,
        'num_contours': num_contours,
        'counts': counts,
        'total_points': total_points,
        'points': [p.to_tuple() for p in points]
    }


def handle_gouraud_polytriangle(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Handle WD_EXAO_GOURAUD_POLYTRIANGLE opcode: "(Gouraud count point1 color1 ... pointN colorN)"

    Format (gouraud_pointset.cpp lines 143-168):
        (Gouraud count point1 color1 point2 color2 ... pointN colorN)

    Gouraud shading interpolates colors across triangle vertices.

    Args:
        stream: Input byte stream
        opcode_name: Should be "Gouraud"

    Returns:
        Dictionary with parsed Gouraud polytriangle data
    """
    # Read until closing paren
    data_bytes = []
    depth = 1

    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in Gouraud opcode")

        char = byte.decode('ascii')
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                break

        data_bytes.append(char)

    data = ''.join(data_bytes).strip()
    fields = ASCIIParser.split_fields(data)

    if len(fields) < 1:
        raise ValueError("Gouraud requires at least count field")

    # Parse count
    count = ASCIIParser.parse_int(fields[0])

    if count < 3:
        raise ValueError(f"Gouraud polytriangle requires at least 3 points, got {count}")

    # Parse point-color pairs
    points = []
    field_idx = 1

    for i in range(count):
        if field_idx >= len(fields):
            raise ValueError(f"Missing point {i}")
        point = ASCIIParser.parse_point(fields[field_idx])
        field_idx += 1

        if field_idx >= len(fields):
            raise ValueError(f"Missing color for point {i}")
        color = ASCIIParser.parse_color(fields[field_idx])
        field_idx += 1

        points.append(GouraudPoint(point, color))

    polytri = GouraudPolytriangle(count, points)

    return {
        'type': 'gouraud_polytriangle',
        'opcode_id': 364,
        'opcode_name': 'WD_EXAO_GOURAUD_POLYTRIANGLE',
        'data': polytri,
        'count': count,
        'num_triangles': polytri.num_triangles(),
        'points': [{'position': p.point.to_tuple(), 'color': p.color.to_tuple()}
                   for p in points]
    }


def handle_gouraud_polyline(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Handle WD_EXAO_GOURAUD_POLYLINE opcode: "(GourLine count point1 color1 ... pointN colorN)"

    Format (gouraud_pointset.cpp lines 143-168):
        (GourLine count point1 color1 point2 color2 ... pointN colorN)

    Gouraud shading interpolates colors along the polyline.

    Args:
        stream: Input byte stream
        opcode_name: Should be "GourLine"

    Returns:
        Dictionary with parsed Gouraud polyline data
    """
    # Read until closing paren
    data_bytes = []
    depth = 1

    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in GourLine opcode")

        char = byte.decode('ascii')
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                break

        data_bytes.append(char)

    data = ''.join(data_bytes).strip()
    fields = ASCIIParser.split_fields(data)

    if len(fields) < 1:
        raise ValueError("GourLine requires at least count field")

    # Parse count
    count = ASCIIParser.parse_int(fields[0])

    if count < 2:
        raise ValueError(f"Gouraud polyline requires at least 2 points, got {count}")

    # Parse point-color pairs
    points = []
    field_idx = 1

    for i in range(count):
        if field_idx >= len(fields):
            raise ValueError(f"Missing point {i}")
        point = ASCIIParser.parse_point(fields[field_idx])
        field_idx += 1

        if field_idx >= len(fields):
            raise ValueError(f"Missing color for point {i}")
        color = ASCIIParser.parse_color(fields[field_idx])
        field_idx += 1

        points.append(GouraudPoint(point, color))

    polyline = GouraudPolyline(count, points)

    return {
        'type': 'gouraud_polyline',
        'opcode_id': 367,
        'opcode_name': 'WD_EXAO_GOURAUD_POLYLINE',
        'data': polyline,
        'count': count,
        'points': [{'position': p.point.to_tuple(), 'color': p.color.to_tuple()}
                   for p in points]
    }


def handle_bezier(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Handle WD_EXAO_BEZIER opcode: "(Bezier count point1 ... pointN)"

    Format (inferred from preload.h and standard Bezier curve definitions):
        (Bezier count point1 point2 ... pointN)

    Note: Bezier support is marked as TODO in the C++ toolkit (opcode.cpp line 195).
    This implementation assumes cubic Bezier curves (4 control points per curve).

    Args:
        stream: Input byte stream
        opcode_name: Should be "Bezier" or similar

    Returns:
        Dictionary with parsed Bezier curve data
    """
    # Read until closing paren
    data_bytes = []
    depth = 1

    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in Bezier opcode")

        char = byte.decode('ascii')
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                break

        data_bytes.append(char)

    data = ''.join(data_bytes).strip()
    fields = ASCIIParser.split_fields(data)

    if len(fields) < 1:
        raise ValueError("Bezier requires at least count field")

    # Parse count
    count = ASCIIParser.parse_int(fields[0])

    if count < 4:
        raise ValueError(f"Bezier curve requires at least 4 control points, got {count}")

    # Parse control points
    control_points = []
    field_idx = 1

    for i in range(count):
        if field_idx >= len(fields):
            raise ValueError(f"Missing control point {i}")
        point = ASCIIParser.parse_point(fields[field_idx])
        control_points.append(point)
        field_idx += 1

    bezier = Bezier(count, control_points)

    return {
        'type': 'bezier',
        'opcode_id': 368,
        'opcode_name': 'WD_EXAO_BEZIER',
        'data': bezier,
        'count': count,
        'num_curves': bezier.num_curves(),
        'control_points': [p.to_tuple() for p in control_points],
        'note': 'Bezier support is experimental (marked TODO in DWF toolkit)'
    }


# ============================================================================
# Main Dispatcher
# ============================================================================

OPCODE_HANDLERS = {
    'Circle': handle_circle,
    'Ellipse': handle_ellipse,
    'Contour': handle_contour,
    'Gouraud': handle_gouraud_polytriangle,
    'GourLine': handle_gouraud_polyline,
    'Bezier': handle_bezier,
}


def dispatch_opcode(stream, opcode_name: str) -> Dict[str, Any]:
    """
    Dispatch an Extended ASCII geometry opcode to its handler.

    Args:
        stream: Input byte stream positioned after the opcode name
        opcode_name: The opcode name (e.g., "Circle", "Ellipse")

    Returns:
        Dictionary with parsed opcode data

    Raises:
        ValueError: If opcode is not recognized or parsing fails
    """
    handler = OPCODE_HANDLERS.get(opcode_name)
    if handler is None:
        raise ValueError(f"Unknown geometry opcode: {opcode_name}")

    return handler(stream, opcode_name)


# ============================================================================
# Test Suite
# ============================================================================

def test_circle_full():
    """Test parsing a full circle."""
    from io import BytesIO

    # Full circle: (Circle 100,200 50)
    data = b"100,200 50)"
    stream = BytesIO(data)

    result = handle_circle(stream, "Circle")

    assert result['type'] == 'circle'
    assert result['position'] == (100, 200)
    assert result['radius'] == 50
    assert result['is_full_circle'] == True
    print("✓ test_circle_full passed")


def test_circle_arc():
    """Test parsing a circular arc."""
    from io import BytesIO

    # Arc from 0° to 90°: angles in DWF units
    # 0° = 0, 90° = 16384 (65536 / 4)
    data = b"100,200 50 0,16384)"
    stream = BytesIO(data)

    result = handle_circle(stream, "Circle")

    assert result['type'] == 'circle'
    assert result['position'] == (100, 200)
    assert result['radius'] == 50
    assert result['is_full_circle'] == False
    assert abs(result['start_angle_deg'] - 0.0) < 0.1
    assert abs(result['end_angle_deg'] - 90.0) < 0.1
    print("✓ test_circle_arc passed")


def test_ellipse_full():
    """Test parsing a full ellipse."""
    from io import BytesIO

    # Full ellipse: (Ellipse 150,300 80,40 0,0 0)
    data = b"150,300 80,40 0,0 0)"
    stream = BytesIO(data)

    result = handle_ellipse(stream, "Ellipse")

    assert result['type'] == 'ellipse'
    assert result['position'] == (150, 300)
    assert result['major'] == 80
    assert result['minor'] == 40
    assert result['is_full_ellipse'] == True
    assert result['tilt_deg'] == 0
    print("✓ test_ellipse_full passed")


def test_ellipse_tilted():
    """Test parsing a tilted ellipse."""
    from io import BytesIO

    # Tilted 45°: 45° = 8192 in DWF units
    data = b"200,400 100,50 0,0 8192)"
    stream = BytesIO(data)

    result = handle_ellipse(stream, "Ellipse")

    assert result['type'] == 'ellipse'
    assert abs(result['tilt_deg'] - 45.0) < 0.1
    print("✓ test_ellipse_tilted passed")


def test_contour_simple():
    """Test parsing a simple contour (single polygon)."""
    from io import BytesIO

    # Triangle: 1 contour, 3 points
    data = b"1 3 0,0 100,0 50,100)"
    stream = BytesIO(data)

    result = handle_contour(stream, "Contour")

    assert result['type'] == 'contour'
    assert result['num_contours'] == 1
    assert result['counts'] == [3]
    assert result['total_points'] == 3
    assert len(result['points']) == 3
    assert result['points'][0] == (0, 0)
    assert result['points'][1] == (100, 0)
    assert result['points'][2] == (50, 100)
    print("✓ test_contour_simple passed")


def test_contour_with_hole():
    """Test parsing a contour with a hole."""
    from io import BytesIO

    # Outer square + inner square hole
    data = b"2 4 4 0,0 100,0 100,100 0,100 25,25 75,25 75,75 25,75)"
    stream = BytesIO(data)

    result = handle_contour(stream, "Contour")

    assert result['type'] == 'contour'
    assert result['num_contours'] == 2
    assert result['counts'] == [4, 4]
    assert result['total_points'] == 8
    print("✓ test_contour_with_hole passed")


def test_gouraud_polytriangle():
    """Test parsing Gouraud shaded triangles."""
    from io import BytesIO

    # Single triangle with RGB colors (alpha=255)
    data = b"3 0,0 4278190080 100,0 4294901760 50,100 4278255360)"
    stream = BytesIO(data)

    result = handle_gouraud_polytriangle(stream, "Gouraud")

    assert result['type'] == 'gouraud_polytriangle'
    assert result['count'] == 3
    assert result['num_triangles'] == 1
    assert len(result['points']) == 3
    print("✓ test_gouraud_polytriangle passed")


def test_gouraud_polyline():
    """Test parsing Gouraud shaded polyline."""
    from io import BytesIO

    # Line from red to blue
    data = b"2 0,0 4278190335 100,100 4294901760)"
    stream = BytesIO(data)

    result = handle_gouraud_polyline(stream, "GourLine")

    assert result['type'] == 'gouraud_polyline'
    assert result['count'] == 2
    assert len(result['points']) == 2
    print("✓ test_gouraud_polyline passed")


def test_bezier_cubic():
    """Test parsing a cubic Bezier curve."""
    from io import BytesIO

    # Cubic Bezier: 4 control points
    data = b"4 0,0 33,100 66,100 100,0)"
    stream = BytesIO(data)

    result = handle_bezier(stream, "Bezier")

    assert result['type'] == 'bezier'
    assert result['count'] == 4
    assert result['num_curves'] == 1
    assert len(result['control_points']) == 4
    print("✓ test_bezier_cubic passed")


def test_bezier_multi():
    """Test parsing multiple connected Bezier curves."""
    from io import BytesIO

    # 2 cubic Bezier curves sharing endpoint: 7 points total
    data = b"7 0,0 20,50 40,50 60,0 80,50 100,50 120,0)"
    stream = BytesIO(data)

    result = handle_bezier(stream, "Bezier")

    assert result['type'] == 'bezier'
    assert result['count'] == 7
    assert result['num_curves'] == 2
    print("✓ test_bezier_multi passed")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*60)
    print("Agent 24: Geometry Opcodes Test Suite")
    print("="*60 + "\n")

    tests = [
        test_circle_full,
        test_circle_arc,
        test_ellipse_full,
        test_ellipse_tilted,
        test_contour_simple,
        test_contour_with_hole,
        test_gouraud_polytriangle,
        test_gouraud_polyline,
        test_bezier_cubic,
        test_bezier_multi,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


# ============================================================================
# Documentation and Usage Examples
# ============================================================================

USAGE_EXAMPLES = """
Usage Examples
==============

1. Circle (Full):
   Input:  (Circle 100,200 50)
   Output: Full circle at (100,200) with radius 50

2. Circle (Arc):
   Input:  (Circle 100,200 50 0,16384)
   Output: Arc from 0° to 90° at (100,200) with radius 50

3. Ellipse:
   Input:  (Ellipse 150,300 80,40 0,0 8192)
   Output: Ellipse at (150,300), major=80, minor=40, tilted 45°

4. Contour (Triangle):
   Input:  (Contour 1 3 0,0 100,0 50,100)
   Output: Single triangle contour with 3 vertices

5. Contour (With Hole):
   Input:  (Contour 2 4 4 0,0 100,0 100,100 0,100 25,25 75,25 75,75 25,75)
   Output: Outer square with inner square hole

6. Gouraud Polytriangle:
   Input:  (Gouraud 3 0,0 4278190080 100,0 4294901760 50,100 4278255360)
   Output: Color-interpolated triangle

7. Gouraud Polyline:
   Input:  (GourLine 2 0,0 4278190335 100,100 4294901760)
   Output: Color-interpolated line

8. Bezier Curve:
   Input:  (Bezier 4 0,0 33,100 66,100 100,0)
   Output: Cubic Bezier curve with 4 control points

Integration with DWF Parser
============================

from io import BytesIO

def parse_dwf_geometry_opcode(opcode_token, stream):
    '''
    Parse a DWF Extended ASCII geometry opcode.

    Args:
        opcode_token: The opcode name (e.g., b"Circle", b"Ellipse")
        stream: BytesIO stream positioned after the opcode name

    Returns:
        Parsed geometry data dictionary
    '''
    opcode_name = opcode_token.decode('ascii')
    return dispatch_opcode(stream, opcode_name)

# Example:
# stream contains: "(Circle 100,200 50)"
# After reading "(", you get opcode_name = "Circle"
# result = dispatch_opcode(stream, "Circle")
# result = {'type': 'circle', 'position': (100, 200), 'radius': 50, ...}

PDF Rendering Hints
===================

1. Circle/Ellipse:
   - Use PDF arc/curve operators
   - Convert DWF angles to PDF angles (0-360°)
   - For arcs, use bezier curve approximations

2. Contours:
   - Use PDF path construction operators
   - Moveto for first point, lineto for subsequent points
   - Use even-odd or non-zero winding rules for holes

3. Gouraud Shading:
   - Use PDF Type 4 (Free-form Gouraud-shaded triangle mesh)
   - Or approximate with gradient fills

4. Bezier Curves:
   - Direct mapping to PDF cubic Bezier curves
   - Use curveto operators
"""


if __name__ == '__main__':
    # Run tests when module is executed directly
    success = run_all_tests()

    if success:
        print("\n" + USAGE_EXAMPLES)
        exit(0)
    else:
        exit(1)
