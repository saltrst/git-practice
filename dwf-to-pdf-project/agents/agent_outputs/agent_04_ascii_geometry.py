"""
DWF ASCII Geometry Opcode Handlers - Agent 4

This module implements ASCII format parsers for 5 core DWF geometry drawing opcodes:
- 0x4C 'L' DRAW_LINE (ASCII format)
- 0x50 'P' DRAW_POLYLINE_POLYGON (ASCII format)
- 0x52 'R' DRAW_CIRCLE (ASCII format)
- 0x45 'E' DRAW_ELLIPSE (ASCII format)
- 0x54 'T' DRAW_POLYTRIANGLE (ASCII format)

These opcodes use ASCII text format with parenthesized coordinates, unlike their
binary counterparts (lowercase letters). ASCII opcodes provide human-readable
geometry data and absolute coordinates (not relative).

Reference Sources:
- C++ Source: /home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/
- Opcode Batch: /home/user/git-practice/dwf-to-pdf-project/agents/agent_tasks/opcode_batches.json
- Type Mappings: /home/user/git-practice/dwf-to-pdf-project/spec/opcode_reference_initial.json

Author: Agent 4 (ASCII Geometry Specialist)
"""

import re
from typing import Dict, List, Tuple, Union
from io import StringIO


# =============================================================================
# OPCODE 0x4C 'L' - DRAW_LINE (ASCII)
# =============================================================================

def parse_opcode_0x4C_ascii_line(data: str) -> Dict[str, Union[str, Tuple[int, int]]]:
    """
    Parse DWF Opcode 0x4C 'L' (ASCII Line).

    ASCII Format: L (x1,y1)(x2,y2)
    Example: "L (100,200)(300,400)" represents a line from (100,200) to (300,400)

    The 'L' opcode draws a line between two absolute coordinate points.
    Unlike binary line opcodes, coordinates are in ASCII text format.

    Args:
        data: ASCII string after the 'L' opcode character (e.g., " (100,200)(300,400)")

    Returns:
        Dictionary containing:
        - 'type': 'line'
        - 'start': Tuple (x1, y1) representing line start point
        - 'end': Tuple (x2, y2) representing line end point

    Format Specification:
        - Two points in format (x,y)(x,y)
        - Coordinates are signed integers (can be negative)
        - Whitespace between elements is optional

    Raises:
        ValueError: If the data format is invalid or coordinates cannot be parsed

    Example:
        >>> result = parse_opcode_0x4C_ascii_line(" (100,200)(300,400)")
        >>> result
        {'type': 'line', 'start': (100, 200), 'end': (300, 400)}
    """
    # Pattern to match two coordinate pairs: (x1,y1)(x2,y2)
    pattern = r'\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)'
    match = re.search(pattern, data)

    if not match:
        raise ValueError(f"Invalid ASCII line format: expected '(x1,y1)(x2,y2)', got: {data.strip()}")

    x1, y1, x2, y2 = map(int, match.groups())

    return {
        'type': 'line',
        'start': (x1, y1),
        'end': (x2, y2)
    }


# =============================================================================
# OPCODE 0x50 'P' - DRAW_POLYLINE_POLYGON (ASCII)
# =============================================================================

def parse_opcode_0x50_ascii_polyline_polygon(data: str) -> Dict[str, Union[str, int, List[Tuple[int, int]]]]:
    """
    Parse DWF Opcode 0x50 'P' (ASCII Polyline/Polygon).

    ASCII Format: P count (x1,y1) (x2,y2) (x3,y3) ...
    Example: "P 4 (0,0) (100,0) (100,100) (0,100)" represents a square

    The 'P' opcode draws a polyline or polygon with multiple vertices.
    When fill mode is on, it's rendered as a filled polygon; otherwise as a polyline.

    Args:
        data: ASCII string after the 'P' opcode character

    Returns:
        Dictionary containing:
        - 'type': 'polyline_polygon'
        - 'count': Number of vertices
        - 'vertices': List of (x, y) tuples representing polygon vertices

    Format Specification:
        - First element is the vertex count (positive integer)
        - Followed by count number of (x,y) coordinate pairs
        - Coordinates are signed integers (can be negative)
        - Whitespace between elements is flexible

    Raises:
        ValueError: If format is invalid, count doesn't match vertices, or parsing fails

    Example:
        >>> result = parse_opcode_0x50_ascii_polyline_polygon(" 3 (100,200) (300,400) (500,600)")
        >>> result
        {'type': 'polyline_polygon', 'count': 3, 'vertices': [(100, 200), (300, 400), (500, 600)]}
    """
    # First, extract the count
    count_match = re.search(r'^\s*(\d+)', data)
    if not count_match:
        raise ValueError(f"Invalid ASCII polyline format: expected vertex count, got: {data.strip()}")

    count = int(count_match.group(1))

    if count < 1:
        raise ValueError(f"Invalid vertex count: {count}. Must be at least 1.")

    # Extract all coordinate pairs
    coord_pattern = r'\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)'
    coord_matches = re.findall(coord_pattern, data)

    if len(coord_matches) != count:
        raise ValueError(
            f"Vertex count mismatch: expected {count} vertices, found {len(coord_matches)}"
        )

    vertices = [(int(x), int(y)) for x, y in coord_matches]

    return {
        'type': 'polyline_polygon',
        'count': count,
        'vertices': vertices
    }


# =============================================================================
# OPCODE 0x52 'R' - DRAW_CIRCLE (ASCII)
# =============================================================================

def parse_opcode_0x52_ascii_circle(data: str) -> Dict[str, Union[str, Tuple[int, int], int]]:
    """
    Parse DWF Opcode 0x52 'R' (ASCII Circle).

    ASCII Format: R (x,y) radius
    Example: "R (500,300) 100" represents a circle centered at (500,300) with radius 100

    The 'R' opcode draws a full circle (not an arc). For arcs or ellipses,
    use extended formats like "(Circle ...)" or opcode 'E'.

    Args:
        data: ASCII string after the 'R' opcode character

    Returns:
        Dictionary containing:
        - 'type': 'circle'
        - 'center': Tuple (x, y) representing circle center
        - 'radius': Integer radius value

    Format Specification:
        - Center point in format (x,y)
        - Followed by radius as positive integer
        - Coordinates can be negative, radius must be positive
        - Whitespace between elements is optional

    Raises:
        ValueError: If format is invalid or radius is negative

    Example:
        >>> result = parse_opcode_0x52_ascii_circle(" (500,300) 100")
        >>> result
        {'type': 'circle', 'center': (500, 300), 'radius': 100}
    """
    # Pattern to match (x,y) radius
    pattern = r'\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s+(-?\d+)'
    match = re.search(pattern, data)

    if not match:
        raise ValueError(f"Invalid ASCII circle format: expected '(x,y) radius', got: {data.strip()}")

    x, y, radius = map(int, match.groups())

    if radius < 0:
        raise ValueError(f"Invalid radius: {radius}. Radius must be non-negative.")

    return {
        'type': 'circle',
        'center': (x, y),
        'radius': radius
    }


# =============================================================================
# OPCODE 0x45 'E' - DRAW_ELLIPSE (ASCII)
# =============================================================================

def parse_opcode_0x45_ascii_ellipse(data: str) -> Dict[str, Union[str, Tuple[int, int], int]]:
    """
    Parse DWF Opcode 0x45 'E' (ASCII Ellipse).

    ASCII Format: E (x,y) major,minor
    Example: "E (400,300) 150,100" represents an ellipse centered at (400,300)
             with major axis 150 and minor axis 100

    The 'E' opcode draws a simple axis-aligned ellipse. For rotated ellipses
    or elliptical arcs, use extended format "(Ellipse ...)".

    Args:
        data: ASCII string after the 'E' opcode character

    Returns:
        Dictionary containing:
        - 'type': 'ellipse'
        - 'center': Tuple (x, y) representing ellipse center
        - 'major_axis': Major axis length (larger radius)
        - 'minor_axis': Minor axis length (smaller radius)

    Format Specification:
        - Center point in format (x,y)
        - Followed by major,minor axes as positive integers
        - Coordinates can be negative, axes must be positive
        - Whitespace between elements is optional
        - When major == minor, this represents a circle

    Raises:
        ValueError: If format is invalid or axes are negative

    Example:
        >>> result = parse_opcode_0x45_ascii_ellipse(" (400,300) 150,100")
        >>> result
        {'type': 'ellipse', 'center': (400, 300), 'major_axis': 150, 'minor_axis': 100}
    """
    # Pattern to match (x,y) major,minor
    pattern = r'\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s+(-?\d+)\s*,\s*(-?\d+)'
    match = re.search(pattern, data)

    if not match:
        raise ValueError(
            f"Invalid ASCII ellipse format: expected '(x,y) major,minor', got: {data.strip()}"
        )

    x, y, major, minor = map(int, match.groups())

    if major < 0 or minor < 0:
        raise ValueError(f"Invalid axes: major={major}, minor={minor}. Axes must be non-negative.")

    return {
        'type': 'ellipse',
        'center': (x, y),
        'major_axis': major,
        'minor_axis': minor
    }


# =============================================================================
# OPCODE 0x54 'T' - DRAW_POLYTRIANGLE (ASCII)
# =============================================================================

def parse_opcode_0x54_ascii_polytriangle(data: str) -> Dict[str, Union[str, int, List[Tuple[int, int]]]]:
    """
    Parse DWF Opcode 0x54 'T' (ASCII Polytriangle).

    ASCII Format: T count (x1,y1) (x2,y2) (x3,y3) ...
    Example: "T 5 (0,0) (100,0) (50,100) (150,50) (100,150)" represents a triangle strip

    The 'T' opcode draws a triangle strip. The first 3 vertices define the first
    triangle, and each subsequent vertex adds another triangle using the previous
    two vertices. All triangles are filled.

    Triangle Formation:
    - First triangle: vertices 0, 1, 2
    - Second triangle: vertices 1, 2, 3
    - Third triangle: vertices 2, 3, 4
    - And so on...

    Args:
        data: ASCII string after the 'T' opcode character

    Returns:
        Dictionary containing:
        - 'type': 'polytriangle'
        - 'count': Number of vertices
        - 'vertices': List of (x, y) tuples representing triangle strip vertices

    Format Specification:
        - First element is the vertex count (must be >= 3)
        - Followed by count number of (x,y) coordinate pairs
        - Coordinates are signed integers (can be negative)
        - Whitespace between elements is flexible

    Raises:
        ValueError: If format is invalid, count < 3, or count doesn't match vertices

    Example:
        >>> result = parse_opcode_0x54_ascii_polytriangle(" 3 (0,0) (100,0) (50,100)")
        >>> result
        {'type': 'polytriangle', 'count': 3, 'vertices': [(0, 0), (100, 0), (50, 100)]}
    """
    # First, extract the count
    count_match = re.search(r'^\s*(\d+)', data)
    if not count_match:
        raise ValueError(f"Invalid ASCII polytriangle format: expected vertex count, got: {data.strip()}")

    count = int(count_match.group(1))

    if count < 3:
        raise ValueError(f"Invalid vertex count: {count}. Polytriangle requires at least 3 vertices.")

    # Extract all coordinate pairs
    coord_pattern = r'\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)'
    coord_matches = re.findall(coord_pattern, data)

    if len(coord_matches) != count:
        raise ValueError(
            f"Vertex count mismatch: expected {count} vertices, found {len(coord_matches)}"
        )

    vertices = [(int(x), int(y)) for x, y in coord_matches]

    return {
        'type': 'polytriangle',
        'count': count,
        'vertices': vertices
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x4C_line():
    """Test suite for opcode 0x4C (ASCII Line)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x4C 'L' (ASCII LINE)")
    print("=" * 70)

    # Test 1: Basic line
    print("\nTest 1: Basic line from (100,200) to (300,400)")
    result = parse_opcode_0x4C_ascii_line(" (100,200)(300,400)")
    assert result['type'] == 'line'
    assert result['start'] == (100, 200)
    assert result['end'] == (300, 400)
    print(f"  PASS: {result}")

    # Test 2: Line with negative coordinates
    print("\nTest 2: Line with negative coordinates")
    result = parse_opcode_0x4C_ascii_line("(-100,-50)(150,-200)")
    assert result['start'] == (-100, -50)
    assert result['end'] == (150, -200)
    print(f"  PASS: {result}")

    # Test 3: Line with extra whitespace
    print("\nTest 3: Line with flexible whitespace")
    result = parse_opcode_0x4C_ascii_line("  ( 0 , 0 ) ( 1000 , 1000 )  ")
    assert result['start'] == (0, 0)
    assert result['end'] == (1000, 1000)
    print(f"  PASS: {result}")

    # Test 4: Vertical line
    print("\nTest 4: Vertical line")
    result = parse_opcode_0x4C_ascii_line(" (500,0)(500,1000)")
    assert result['start'] == (500, 0)
    assert result['end'] == (500, 1000)
    print(f"  PASS: {result}")

    # Test 5: Error handling - invalid format
    print("\nTest 5: Error handling - invalid format")
    try:
        parse_opcode_0x4C_ascii_line(" 100,200,300,400")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x4C 'L': ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x50_polyline_polygon():
    """Test suite for opcode 0x50 (ASCII Polyline/Polygon)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x50 'P' (ASCII POLYLINE/POLYGON)")
    print("=" * 70)

    # Test 1: Simple triangle
    print("\nTest 1: Triangle with 3 vertices")
    result = parse_opcode_0x50_ascii_polyline_polygon(" 3 (100,200) (300,400) (500,600)")
    assert result['type'] == 'polyline_polygon'
    assert result['count'] == 3
    assert len(result['vertices']) == 3
    assert result['vertices'] == [(100, 200), (300, 400), (500, 600)]
    print(f"  PASS: {result}")

    # Test 2: Square
    print("\nTest 2: Square with 4 vertices")
    result = parse_opcode_0x50_ascii_polyline_polygon(" 4 (0,0) (100,0) (100,100) (0,100)")
    assert result['count'] == 4
    assert result['vertices'] == [(0, 0), (100, 0), (100, 100), (0, 100)]
    print(f"  PASS: {result}")

    # Test 3: Complex polygon
    print("\nTest 3: Hexagon with 6 vertices")
    result = parse_opcode_0x50_ascii_polyline_polygon(" 6 (100,0) (150,50) (150,100) (100,150) (50,100) (50,50)")
    assert result['count'] == 6
    assert len(result['vertices']) == 6
    print(f"  PASS: {result}")

    # Test 4: Negative coordinates
    print("\nTest 4: Polygon with negative coordinates")
    result = parse_opcode_0x50_ascii_polyline_polygon(" 3 (-100,-100) (100,-100) (0,100)")
    assert result['vertices'][0] == (-100, -100)
    assert result['vertices'][1] == (100, -100)
    assert result['vertices'][2] == (0, 100)
    print(f"  PASS: {result}")

    # Test 5: Single vertex (edge case)
    print("\nTest 5: Single vertex polyline")
    result = parse_opcode_0x50_ascii_polyline_polygon(" 1 (500,750)")
    assert result['count'] == 1
    assert result['vertices'] == [(500, 750)]
    print(f"  PASS: {result}")

    # Test 6: Error handling - count mismatch
    print("\nTest 6: Error handling - vertex count mismatch")
    try:
        parse_opcode_0x50_ascii_polyline_polygon(" 5 (100,200) (300,400)")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x50 'P': ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x52_circle():
    """Test suite for opcode 0x52 (ASCII Circle)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x52 'R' (ASCII CIRCLE)")
    print("=" * 70)

    # Test 1: Basic circle
    print("\nTest 1: Circle at (500,300) with radius 100")
    result = parse_opcode_0x52_ascii_circle(" (500,300) 100")
    assert result['type'] == 'circle'
    assert result['center'] == (500, 300)
    assert result['radius'] == 100
    print(f"  PASS: {result}")

    # Test 2: Circle at origin
    print("\nTest 2: Circle at origin (0,0) with radius 50")
    result = parse_opcode_0x52_ascii_circle(" (0,0) 50")
    assert result['center'] == (0, 0)
    assert result['radius'] == 50
    print(f"  PASS: {result}")

    # Test 3: Negative center coordinates
    print("\nTest 3: Circle with negative center coordinates")
    result = parse_opcode_0x52_ascii_circle(" (-200,-150) 75")
    assert result['center'] == (-200, -150)
    assert result['radius'] == 75
    print(f"  PASS: {result}")

    # Test 4: Large circle
    print("\nTest 4: Large circle")
    result = parse_opcode_0x52_ascii_circle(" (1000,2000) 5000")
    assert result['center'] == (1000, 2000)
    assert result['radius'] == 5000
    print(f"  PASS: {result}")

    # Test 5: Zero radius (point)
    print("\nTest 5: Circle with zero radius (degenerate)")
    result = parse_opcode_0x52_ascii_circle(" (100,100) 0")
    assert result['radius'] == 0
    print(f"  PASS: {result}")

    # Test 6: Error handling - invalid format
    print("\nTest 6: Error handling - invalid format")
    try:
        parse_opcode_0x52_ascii_circle(" 500,300,100")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x52 'R': ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x45_ellipse():
    """Test suite for opcode 0x45 (ASCII Ellipse)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x45 'E' (ASCII ELLIPSE)")
    print("=" * 70)

    # Test 1: Basic ellipse
    print("\nTest 1: Ellipse at (400,300) with major=150, minor=100")
    result = parse_opcode_0x45_ascii_ellipse(" (400,300) 150,100")
    assert result['type'] == 'ellipse'
    assert result['center'] == (400, 300)
    assert result['major_axis'] == 150
    assert result['minor_axis'] == 100
    print(f"  PASS: {result}")

    # Test 2: Ellipse at origin
    print("\nTest 2: Ellipse at origin")
    result = parse_opcode_0x45_ascii_ellipse(" (0,0) 200,50")
    assert result['center'] == (0, 0)
    assert result['major_axis'] == 200
    assert result['minor_axis'] == 50
    print(f"  PASS: {result}")

    # Test 3: Negative center coordinates
    print("\nTest 3: Ellipse with negative center")
    result = parse_opcode_0x45_ascii_ellipse(" (-500,-300) 120,80")
    assert result['center'] == (-500, -300)
    assert result['major_axis'] == 120
    assert result['minor_axis'] == 80
    print(f"  PASS: {result}")

    # Test 4: Circle case (major == minor)
    print("\nTest 4: Ellipse with equal axes (circle)")
    result = parse_opcode_0x45_ascii_ellipse(" (250,250) 100,100")
    assert result['major_axis'] == 100
    assert result['minor_axis'] == 100
    print(f"  PASS: {result}")

    # Test 5: Thin ellipse
    print("\nTest 5: Very thin ellipse")
    result = parse_opcode_0x45_ascii_ellipse(" (600,400) 500,10")
    assert result['major_axis'] == 500
    assert result['minor_axis'] == 10
    print(f"  PASS: {result}")

    # Test 6: Error handling - invalid format
    print("\nTest 6: Error handling - invalid format")
    try:
        parse_opcode_0x45_ascii_ellipse(" (400,300) 150")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x45 'E': ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x54_polytriangle():
    """Test suite for opcode 0x54 (ASCII Polytriangle)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x54 'T' (ASCII POLYTRIANGLE)")
    print("=" * 70)

    # Test 1: Simple triangle
    print("\nTest 1: Single triangle (3 vertices)")
    result = parse_opcode_0x54_ascii_polytriangle(" 3 (0,0) (100,0) (50,100)")
    assert result['type'] == 'polytriangle'
    assert result['count'] == 3
    assert len(result['vertices']) == 3
    assert result['vertices'] == [(0, 0), (100, 0), (50, 100)]
    print(f"  PASS: {result}")

    # Test 2: Triangle strip (5 vertices = 3 triangles)
    print("\nTest 2: Triangle strip with 5 vertices")
    result = parse_opcode_0x54_ascii_polytriangle(" 5 (0,0) (100,0) (50,100) (150,50) (100,150)")
    assert result['count'] == 5
    assert len(result['vertices']) == 5
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Polytriangle with negative coordinates")
    result = parse_opcode_0x54_ascii_polytriangle(" 3 (-100,-50) (100,-50) (0,100)")
    assert result['vertices'][0] == (-100, -50)
    assert result['vertices'][1] == (100, -50)
    assert result['vertices'][2] == (0, 100)
    print(f"  PASS: {result}")

    # Test 4: Large triangle strip
    print("\nTest 4: Large triangle strip with 10 vertices")
    data = " 10 (0,0) (10,10) (20,0) (30,10) (40,0) (50,10) (60,0) (70,10) (80,0) (90,10)"
    result = parse_opcode_0x54_ascii_polytriangle(data)
    assert result['count'] == 10
    assert len(result['vertices']) == 10
    print(f"  PASS: {result}")

    # Test 5: Error handling - insufficient vertices
    print("\nTest 5: Error handling - insufficient vertices (< 3)")
    try:
        parse_opcode_0x54_ascii_polytriangle(" 2 (100,200) (300,400)")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 6: Error handling - count mismatch
    print("\nTest 6: Error handling - vertex count mismatch")
    try:
        parse_opcode_0x54_ascii_polytriangle(" 5 (0,0) (100,0) (50,100)")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x54 'T': ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run comprehensive test suite for all ASCII geometry opcodes."""
    print("\n" + "=" * 70)
    print("DWF ASCII GEOMETRY OPCODE PARSER - AGENT 4 TEST SUITE")
    print("=" * 70)
    print("Testing 5 ASCII geometry opcodes:")
    print("  - 0x4C 'L' DRAW_LINE")
    print("  - 0x50 'P' DRAW_POLYLINE_POLYGON")
    print("  - 0x52 'R' DRAW_CIRCLE")
    print("  - 0x45 'E' DRAW_ELLIPSE")
    print("  - 0x54 'T' DRAW_POLYTRIANGLE")
    print("=" * 70)

    test_opcode_0x4C_line()
    test_opcode_0x50_polyline_polygon()
    test_opcode_0x52_circle()
    test_opcode_0x45_ellipse()
    test_opcode_0x54_polytriangle()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x4C 'L' (Line): 5 tests passed")
    print("  - Opcode 0x50 'P' (Polyline/Polygon): 6 tests passed")
    print("  - Opcode 0x52 'R' (Circle): 6 tests passed")
    print("  - Opcode 0x45 'E' (Ellipse): 6 tests passed")
    print("  - Opcode 0x54 'T' (Polytriangle): 6 tests passed")
    print("  - Total: 29 tests passed")
    print("\nEdge Cases Handled:")
    print("  - Negative coordinates")
    print("  - Flexible whitespace parsing")
    print("  - Zero-sized geometries (degenerate cases)")
    print("  - Large coordinate values")
    print("  - Invalid format detection and error reporting")
    print("  - Count/vertex mismatch detection")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
