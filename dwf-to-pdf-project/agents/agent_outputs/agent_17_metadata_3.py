"""
DWF Extended ASCII Metadata Opcodes (Part 3) - Agent 17

This module implements Extended ASCII format parsers for 6 DWF metadata opcodes:
- WD_EXAO_SOURCE_FILENAME (ID 286) - (SourceFilename "string") - Original filename
- WD_EXAO_DEFINE_PLOT_INFO (ID 282) - (PlotInfo ...) - Plot configuration
- WD_EXAO_DEFINE_UNITS (ID 289) - (Units "string" matrix) - Units of measurement
- WD_EXAO_SET_INKED_AREA (ID 316) - (InkedArea pt1 pt2 pt3 pt4) - Inked area bounds
- WD_EXAO_FILETIME (ID 334) - (Time low high) - File timestamp
- WD_EXAO_DRAWING_INFO (ID 365) - Drawing metadata container

These opcodes handle file metadata, plot settings, coordinate units, and timestamps.
All use Extended ASCII format with parenthesized syntax: (OpcodeName ...data...)

Reference Sources:
- C++ Source: /home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/
  - informational.cpp (Source Filename)
  - plotinfo.cpp (Plot Info)
  - units.cpp (Units)
  - inked_area.cpp (Inked Area)
  - filetime.cpp (FileTime)
  - dwginfo.h/cpp (Drawing Info)
- Research: /home/user/git-practice/dwf-to-pdf-project/agents/agent_outputs/agent_13_extended_opcodes_research.md

Author: Agent 17 (Extended ASCII Metadata Specialist)
"""

import re
import struct
from typing import Dict, List, Tuple, Union, Optional
from datetime import datetime


# =============================================================================
# OPCODE 286 (WD_EXAO_SOURCE_FILENAME) - (SourceFilename "string")
# =============================================================================

def parse_opcode_286_source_filename(data: str) -> Dict[str, Union[str, int]]:
    """
    Parse DWF Opcode 286 WD_EXAO_SOURCE_FILENAME - (SourceFilename "string").

    ASCII Format: (SourceFilename "original_file.dwg")
    Example: '(SourceFilename "C:\\MyDrawings\\Floor_Plan.dwg")'

    This opcode stores the original source filename from which the DWF was created,
    typically the CAD application's native file format (e.g., .dwg, .dxf).

    C++ Reference: informational.cpp, line 30
        IMPLEMENT_INFORMATIONAL_CLASS_FUNCTIONS(Source_Filename, source_filename,
                                                Informational, "SourceFilename")

    Format Specification:
        - Format: (SourceFilename string)
        - String can be quoted or unquoted
        - Whitespace between elements is optional
        - String contains full path or filename

    Args:
        data: String content after '(SourceFilename' up to closing ')'

    Returns:
        Dictionary containing:
        - 'opcode_id': 286
        - 'opcode_name': 'SourceFilename'
        - 'type': 'metadata'
        - 'filename': String containing the source filename

    Raises:
        ValueError: If the data format is invalid

    Example:
        >>> result = parse_opcode_286_source_filename(' "Floor_Plan.dwg")')
        >>> result['filename']
        'Floor_Plan.dwg'
    """
    # Extract string value (handles quoted and unquoted strings)
    # Remove leading/trailing whitespace and closing paren
    content = data.strip().rstrip(')')

    # Check for quoted string
    quoted_match = re.match(r'^"([^"]*)"', content)
    if quoted_match:
        filename = quoted_match.group(1)
    else:
        # Unquoted string - take everything until closing paren
        filename = content.strip()

    if not filename:
        raise ValueError(f"Invalid SourceFilename format: missing filename in: {data}")

    return {
        'opcode_id': 286,
        'opcode_name': 'SourceFilename',
        'type': 'metadata',
        'filename': filename
    }


# =============================================================================
# OPCODE 282 (WD_EXAO_DEFINE_PLOT_INFO) - (PlotInfo ...)
# =============================================================================

def parse_opcode_282_plot_info(data: str) -> Dict[str, Union[str, int, float, List[float]]]:
    """
    Parse DWF Opcode 282 WD_EXAO_DEFINE_PLOT_INFO - (PlotInfo ...).

    ASCII Format: (PlotInfo show/hide rotation units width height ll_x ll_y ur_x ur_y matrix)
    Example: '(PlotInfo show 0 in 11.0 8.5 0.0 0.0 11.0 8.5 1.0 0.0 0.0 1.0 0.0 0.0)'

    This opcode defines plot/print configuration including paper size, printable area,
    and transformation matrix from DWF coordinates to paper coordinates.

    C++ Reference: plotinfo.cpp, lines 22-76
        Format: (PlotInfo [show|hide] [rotation] [mm|in] width height
                 ll_x ll_y ur_x ur_y matrix_elements)

    Format Specification:
        - show/hide: Visibility flag for plot border
        - rotation: Rotation angle in degrees (0, 90, 180, 270)
        - units: "mm" (millimeters) or "in" (inches)
        - width, height: Paper dimensions in specified units
        - ll_x, ll_y: Lower-left corner of printable area
        - ur_x, ur_y: Upper-right corner of printable area
        - matrix: 2D transformation matrix (6 elements: m00 m01 m10 m11 tx ty)

    Args:
        data: String content after '(PlotInfo' up to closing ')'

    Returns:
        Dictionary containing:
        - 'opcode_id': 282
        - 'opcode_name': 'PlotInfo'
        - 'type': 'metadata'
        - 'show': Boolean - whether to show plot border
        - 'rotation': Float - rotation angle in degrees
        - 'units': String - 'mm' or 'in'
        - 'paper_width': Float - paper width
        - 'paper_height': Float - paper height
        - 'lower_left': Tuple (x, y) - printable area lower-left
        - 'upper_right': Tuple (x, y) - printable area upper-right
        - 'transform_matrix': List of 6 floats [m00, m01, m10, m11, tx, ty]

    Raises:
        ValueError: If the data format is invalid

    Example:
        >>> result = parse_opcode_282_plot_info(' show 0 in 11.0 8.5 0.5 0.5 10.5 8.0 1.0 0.0 0.0 1.0 0.0 0.0)')
        >>> result['paper_width']
        11.0
    """
    # Remove closing paren and split into tokens
    content = data.strip().rstrip(')')
    tokens = content.split()

    if len(tokens) < 13:
        raise ValueError(f"Invalid PlotInfo format: expected at least 13 tokens, got {len(tokens)}")

    idx = 0

    # Parse show/hide flag
    show_str = tokens[idx].lower()
    if show_str not in ('show', 'hide'):
        raise ValueError(f"Invalid PlotInfo show flag: expected 'show' or 'hide', got '{show_str}'")
    show = (show_str == 'show')
    idx += 1

    # Parse rotation (optional in older versions, but we expect it)
    rotation = float(tokens[idx])
    idx += 1

    # Parse units
    units = tokens[idx].lower()
    if units not in ('mm', 'in'):
        raise ValueError(f"Invalid PlotInfo units: expected 'mm' or 'in', got '{units}'")
    idx += 1

    # Parse paper dimensions
    paper_width = float(tokens[idx])
    idx += 1
    paper_height = float(tokens[idx])
    idx += 1

    # Parse printable area bounds
    ll_x = float(tokens[idx])
    idx += 1
    ll_y = float(tokens[idx])
    idx += 1
    ur_x = float(tokens[idx])
    idx += 1
    ur_y = float(tokens[idx])
    idx += 1

    # Parse transformation matrix (6 elements for 2D affine transform)
    if len(tokens) < idx + 6:
        raise ValueError(f"Invalid PlotInfo format: missing transformation matrix elements")

    matrix = [float(tokens[idx + i]) for i in range(6)]

    return {
        'opcode_id': 282,
        'opcode_name': 'PlotInfo',
        'type': 'metadata',
        'show': show,
        'rotation': rotation,
        'units': units,
        'paper_width': paper_width,
        'paper_height': paper_height,
        'lower_left': (ll_x, ll_y),
        'upper_right': (ur_x, ur_y),
        'transform_matrix': matrix
    }


# =============================================================================
# OPCODE 289 (WD_EXAO_DEFINE_UNITS) - (Units "string" matrix)
# =============================================================================

def parse_opcode_289_units(data: str) -> Dict[str, Union[str, int, List[float]]]:
    """
    Parse DWF Opcode 289 WD_EXAO_DEFINE_UNITS - (Units "string" matrix).

    ASCII Format: (Units "unit_name" m00 m01 m10 m11 tx ty)
    Example: '(Units "meters" 1.0 0.0 0.0 1.0 0.0 0.0)'

    This opcode defines the units of measurement and transformation matrix
    from application (source) coordinates to DWF coordinates.

    C++ Reference: units.cpp, lines 35-67
        Format: (Units string matrix_elements)
        Matrix is 2D affine transform with 6 elements

    Format Specification:
        - unit_name: String describing units (e.g., "millimeters", "inches", "meters")
        - matrix: 2D transformation matrix (6 elements: m00 m01 m10 m11 tx ty)
        - Standard unit names (non-localized):
            - millimeters, centimeters, meters, kilometers
            - inches, feet, "feet and inches", yards, miles

    Args:
        data: String content after '(Units' up to closing ')'

    Returns:
        Dictionary containing:
        - 'opcode_id': 289
        - 'opcode_name': 'Units'
        - 'type': 'metadata'
        - 'units': String - unit name/description
        - 'transform_matrix': List of 6 floats [m00, m01, m10, m11, tx, ty]

    Raises:
        ValueError: If the data format is invalid

    Example:
        >>> result = parse_opcode_289_units(' "meters" 1.0 0.0 0.0 1.0 0.0 0.0)')
        >>> result['units']
        'meters'
    """
    # Remove closing paren
    content = data.strip().rstrip(')')

    # Extract quoted string and matrix elements
    quoted_match = re.match(r'^"([^"]*)"(.*)$', content.strip())
    if not quoted_match:
        raise ValueError(f"Invalid Units format: missing quoted unit name in: {data}")

    units = quoted_match.group(1)
    matrix_str = quoted_match.group(2).strip()

    # Parse matrix elements (should be 6 floats)
    try:
        matrix_tokens = matrix_str.split()
        if len(matrix_tokens) != 6:
            raise ValueError(f"Invalid Units format: expected 6 matrix elements, got {len(matrix_tokens)}")
        matrix = [float(token) for token in matrix_tokens]
    except ValueError as e:
        raise ValueError(f"Invalid Units format: could not parse matrix elements: {e}")

    return {
        'opcode_id': 289,
        'opcode_name': 'Units',
        'type': 'metadata',
        'units': units,
        'transform_matrix': matrix
    }


# =============================================================================
# OPCODE 316 (WD_EXAO_SET_INKED_AREA) - (InkedArea pt1 pt2 pt3 pt4)
# =============================================================================

def parse_opcode_316_inked_area(data: str) -> Dict[str, Union[str, int, List[Tuple[int, int]]]]:
    """
    Parse DWF Opcode 316 WD_EXAO_SET_INKED_AREA - (InkedArea pt1 pt2 pt3 pt4).

    ASCII Format: (InkedArea (x1,y1) (x2,y2) (x3,y3) (x4,y4))
    Example: '(InkedArea (0,0) (8500,0) (8500,11000) (0,11000))'

    This opcode defines the "inked area" - the bounding region containing all
    drawn content. Typically represents a rectangular bounds with 4 corner points.

    C++ Reference: inked_area.cpp, lines 41-64
        Format: (InkedArea point1 point2 point3 point4)
        Each point is a WT_Logical_Point (x, y coordinate pair)

    Format Specification:
        - 4 logical points defining the inked area bounds
        - Points are typically corners of a bounding rectangle
        - Format: (x,y) for each point
        - Coordinates are signed 32-bit integers

    Args:
        data: String content after '(InkedArea' up to closing ')'

    Returns:
        Dictionary containing:
        - 'opcode_id': 316
        - 'opcode_name': 'InkedArea'
        - 'type': 'metadata'
        - 'bounds': List of 4 tuples [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]

    Raises:
        ValueError: If the data format is invalid

    Example:
        >>> result = parse_opcode_316_inked_area(' (0,0) (100,0) (100,100) (0,100))')
        >>> len(result['bounds'])
        4
    """
    # Remove closing paren and extra whitespace
    content = data.strip()
    if content.endswith(')'):
        content = content[:-1]

    # Pattern to match 4 coordinate pairs: (x1,y1) (x2,y2) (x3,y3) (x4,y4)
    # Use DOTALL to handle any whitespace between coordinates
    pattern = r'\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)'
    matches = re.findall(pattern, content)

    if len(matches) != 4:
        raise ValueError(f"Invalid InkedArea format: expected 4 points, got {len(matches)}")

    bounds = [(int(x), int(y)) for x, y in matches]

    return {
        'opcode_id': 316,
        'opcode_name': 'InkedArea',
        'type': 'metadata',
        'bounds': bounds
    }


# =============================================================================
# OPCODE 334 (WD_EXAO_FILETIME) - (Time low high)
# =============================================================================

def parse_opcode_334_filetime(data: str) -> Dict[str, Union[str, int]]:
    """
    Parse DWF Opcode 334 WD_EXAO_FILETIME - (Time low high).

    ASCII Format: (Time low_date_time high_date_time)
    Example: '(Time 3577643008 30828055)'

    This opcode stores a file timestamp using Windows FILETIME format
    (64-bit value split into low and high 32-bit integers).

    C++ Reference: filetime.cpp, lines 36-67
        ASCII format: (Time low_date_time high_date_time)
        Binary format also available: {opcode low high}

    Format Specification:
        - low_date_time: Lower 32 bits of FILETIME
        - high_date_time: Upper 32 bits of FILETIME
        - FILETIME: 100-nanosecond intervals since January 1, 1601 UTC
        - Can be converted to Unix timestamp and Python datetime

    Args:
        data: String content after '(Time' up to closing ')'

    Returns:
        Dictionary containing:
        - 'opcode_id': 334
        - 'opcode_name': 'FileTime'
        - 'type': 'metadata'
        - 'low_date_time': Integer - lower 32 bits
        - 'high_date_time': Integer - upper 32 bits
        - 'filetime': Integer - combined 64-bit FILETIME value
        - 'timestamp': Optional datetime object (if conversion succeeds)

    Raises:
        ValueError: If the data format is invalid

    Example:
        >>> result = parse_opcode_334_filetime(' 3577643008 30828055)')
        >>> result['low_date_time']
        3577643008
    """
    # Remove closing paren and split into tokens
    content = data.strip().rstrip(')')
    tokens = content.split()

    if len(tokens) != 2:
        raise ValueError(f"Invalid FileTime format: expected 2 values (low high), got {len(tokens)}")

    try:
        low_date_time = int(tokens[0])
        high_date_time = int(tokens[1])
    except ValueError:
        raise ValueError(f"Invalid FileTime format: could not parse integer values from: {tokens}")

    # Combine into 64-bit FILETIME value
    filetime = (high_date_time << 32) | low_date_time

    # Try to convert to Python datetime
    # FILETIME is 100-nanosecond intervals since Jan 1, 1601
    # Unix epoch is Jan 1, 1970
    # Difference: 11644473600 seconds
    timestamp = None
    try:
        # Convert FILETIME to seconds since 1601
        seconds_since_1601 = filetime / 10000000.0
        # Convert to Unix timestamp (seconds since 1970)
        unix_timestamp = seconds_since_1601 - 11644473600
        # Create datetime object
        timestamp = datetime.utcfromtimestamp(unix_timestamp)
    except (ValueError, OSError):
        # Invalid timestamp - leave as None
        pass

    result = {
        'opcode_id': 334,
        'opcode_name': 'FileTime',
        'type': 'metadata',
        'low_date_time': low_date_time,
        'high_date_time': high_date_time,
        'filetime': filetime
    }

    if timestamp:
        result['timestamp'] = timestamp

    return result


# =============================================================================
# OPCODE 365 (WD_EXAO_DRAWING_INFO) - Drawing Info Container
# =============================================================================

def parse_opcode_365_drawing_info(data: str) -> Dict[str, Union[str, int]]:
    """
    Parse DWF Opcode 365 WD_EXAO_DRAWING_INFO - Drawing metadata container.

    This opcode represents the composite Drawing Info object that contains
    various metadata fields. In practice, this is a container object that
    manages the following metadata opcodes:
    - Author (ID 256)
    - Comments (ID 262)
    - Copyright (ID 263)
    - Creator (ID 264)
    - Description (ID 269)
    - Keywords (ID 275)
    - Title (ID 303)
    - Subject (ID 304)
    - Source Filename (ID 286)
    - Units (ID 289)
    - Creation Time (ID 265)
    - Modification Time (ID 280)
    - Source Creation Time (ID 284)
    - Source Modification Time (ID 285)
    - Named View List (ID 281)

    C++ Reference: dwginfo.h/cpp
        The WT_Drawing_Info class is a container that manages all metadata
        and provides a sync() method to serialize changed fields.

    Note: In DWF files, Drawing Info is typically not serialized as a single
    opcode but rather as individual metadata opcodes. This function serves
    as a placeholder/documentation for the concept.

    Args:
        data: String content (typically empty or minimal)

    Returns:
        Dictionary containing:
        - 'opcode_id': 365
        - 'opcode_name': 'DrawingInfo'
        - 'type': 'metadata'
        - 'note': Explanation that this is a container concept

    Example:
        >>> result = parse_opcode_365_drawing_info(')')
        >>> result['opcode_name']
        'DrawingInfo'
    """
    return {
        'opcode_id': 365,
        'opcode_name': 'DrawingInfo',
        'type': 'metadata',
        'note': 'Drawing Info is a composite container object. Individual metadata fields ' +
                'are serialized as separate opcodes (Author, Title, Units, etc.)'
    }


# =============================================================================
# UNIFIED PARSER - Dispatcher for All Metadata Opcodes
# =============================================================================

def parse_extended_ascii_metadata(opcode_name: str, data: str) -> Dict:
    """
    Unified parser dispatcher for Extended ASCII metadata opcodes.

    Routes opcode parsing to the appropriate handler based on opcode name.

    Args:
        opcode_name: Name of the Extended ASCII opcode (e.g., 'SourceFilename', 'PlotInfo')
        data: String content after opcode name up to closing ')'

    Returns:
        Parsed opcode data dictionary from the appropriate handler

    Raises:
        ValueError: If opcode_name is not recognized or parsing fails

    Supported Opcodes:
        - 'SourceFilename' -> parse_opcode_286_source_filename
        - 'PlotInfo' -> parse_opcode_282_plot_info
        - 'Units' -> parse_opcode_289_units
        - 'InkedArea' -> parse_opcode_316_inked_area
        - 'Time' -> parse_opcode_334_filetime

    Example:
        >>> result = parse_extended_ascii_metadata('SourceFilename', ' "test.dwg")')
        >>> result['filename']
        'test.dwg'
    """
    handlers = {
        'SourceFilename': parse_opcode_286_source_filename,
        'PlotInfo': parse_opcode_282_plot_info,
        'Units': parse_opcode_289_units,
        'InkedArea': parse_opcode_316_inked_area,
        'Time': parse_opcode_334_filetime,
    }

    if opcode_name not in handlers:
        raise ValueError(f"Unsupported Extended ASCII metadata opcode: {opcode_name}")

    return handlers[opcode_name](data)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def filetime_to_datetime(low: int, high: int) -> Optional[datetime]:
    """
    Convert Windows FILETIME (low/high 32-bit parts) to Python datetime.

    Args:
        low: Lower 32 bits of FILETIME
        high: Upper 32 bits of FILETIME

    Returns:
        datetime object in UTC, or None if conversion fails

    Example:
        >>> dt = filetime_to_datetime(3577643008, 30828055)
        >>> dt.year
        2019
    """
    try:
        filetime = (high << 32) | low
        seconds_since_1601 = filetime / 10000000.0
        unix_timestamp = seconds_since_1601 - 11644473600
        return datetime.utcfromtimestamp(unix_timestamp)
    except (ValueError, OSError):
        return None


def datetime_to_filetime(dt: datetime) -> Tuple[int, int]:
    """
    Convert Python datetime to Windows FILETIME (low/high 32-bit parts).

    Args:
        dt: datetime object (assumed UTC)

    Returns:
        Tuple of (low_date_time, high_date_time)

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2019, 1, 1, 12, 0, 0)
        >>> low, high = datetime_to_filetime(dt)
        >>> low > 0 and high > 0
        True
    """
    import calendar
    unix_timestamp = calendar.timegm(dt.timetuple())
    seconds_since_1601 = unix_timestamp + 11644473600
    filetime = int(seconds_since_1601 * 10000000)
    low = filetime & 0xFFFFFFFF
    high = (filetime >> 32) & 0xFFFFFFFF
    return (low, high)


# =============================================================================
# TEST SUITE
# =============================================================================

def run_tests():
    """
    Comprehensive test suite for all metadata opcode parsers.
    Tests cover normal cases, edge cases, and error conditions.
    """
    print("=" * 80)
    print("AGENT 17 METADATA OPCODES TEST SUITE")
    print("=" * 80)

    # Test 1: WD_EXAO_SOURCE_FILENAME (ID 286)
    print("\n[TEST 1] Opcode 286 - SourceFilename (quoted)")
    try:
        result = parse_opcode_286_source_filename(' "C:\\Drawings\\Floor_Plan.dwg")')
        assert result['opcode_id'] == 286
        assert result['filename'] == "C:\\Drawings\\Floor_Plan.dwg"
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n[TEST 2] Opcode 286 - SourceFilename (simple)")
    try:
        result = parse_opcode_286_source_filename(' "test.dwg")')
        assert result['filename'] == "test.dwg"
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    # Test 3: WD_EXAO_DEFINE_PLOT_INFO (ID 282)
    print("\n[TEST 3] Opcode 282 - PlotInfo (standard letter size)")
    try:
        result = parse_opcode_282_plot_info(
            ' show 0 in 11.0 8.5 0.5 0.5 10.5 8.0 1.0 0.0 0.0 1.0 0.0 0.0)'
        )
        assert result['opcode_id'] == 282
        assert result['show'] == True
        assert result['rotation'] == 0.0
        assert result['units'] == 'in'
        assert result['paper_width'] == 11.0
        assert result['paper_height'] == 8.5
        assert result['lower_left'] == (0.5, 0.5)
        assert result['upper_right'] == (10.5, 8.0)
        assert len(result['transform_matrix']) == 6
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n[TEST 4] Opcode 282 - PlotInfo (A4 metric, rotated)")
    try:
        result = parse_opcode_282_plot_info(
            ' hide 90 mm 297.0 210.0 10.0 10.0 287.0 200.0 0.5 0.0 0.0 0.5 0.0 0.0)'
        )
        assert result['show'] == False
        assert result['rotation'] == 90.0
        assert result['units'] == 'mm'
        assert result['paper_width'] == 297.0
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    # Test 5: WD_EXAO_DEFINE_UNITS (ID 289)
    print("\n[TEST 5] Opcode 289 - Units (meters)")
    try:
        result = parse_opcode_289_units(' "meters" 1.0 0.0 0.0 1.0 0.0 0.0)')
        assert result['opcode_id'] == 289
        assert result['units'] == 'meters'
        assert result['transform_matrix'] == [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n[TEST 6] Opcode 289 - Units (inches with scale)")
    try:
        result = parse_opcode_289_units(' "inches" 2.54 0.0 0.0 2.54 100.0 200.0)')
        assert result['units'] == 'inches'
        assert result['transform_matrix'][0] == 2.54  # Scale factor
        assert result['transform_matrix'][4] == 100.0  # Translation X
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    # Test 7: WD_EXAO_SET_INKED_AREA (ID 316)
    print("\n[TEST 7] Opcode 316 - InkedArea (rectangle)")
    try:
        result = parse_opcode_316_inked_area(' (0,0) (8500,0) (8500,11000) (0,11000))')
        assert result['opcode_id'] == 316
        assert len(result['bounds']) == 4
        assert result['bounds'][0] == (0, 0)
        assert result['bounds'][2] == (8500, 11000)
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n[TEST 8] Opcode 316 - InkedArea (negative coordinates)")
    try:
        result = parse_opcode_316_inked_area(' (-100,-100) (100,-100) (100,100) (-100,100))')
        assert result['bounds'][0] == (-100, -100)
        assert result['bounds'][2] == (100, 100)
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    # Test 9: WD_EXAO_FILETIME (ID 334)
    print("\n[TEST 9] Opcode 334 - FileTime (standard)")
    try:
        result = parse_opcode_334_filetime(' 3577643008 30828055)')
        assert result['opcode_id'] == 334
        assert result['low_date_time'] == 3577643008
        assert result['high_date_time'] == 30828055
        assert result['filetime'] > 0
        print(f"  ✓ PASS: {result}")
        if 'timestamp' in result:
            print(f"    Timestamp: {result['timestamp']}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n[TEST 10] Opcode 334 - FileTime to datetime conversion")
    try:
        # Test helper function
        dt = filetime_to_datetime(3577643008, 30828055)
        assert dt is not None
        assert dt.year >= 2000
        print(f"  ✓ PASS: Converted to {dt}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    # Test 11: Unified dispatcher
    print("\n[TEST 11] Unified dispatcher - SourceFilename")
    try:
        result = parse_extended_ascii_metadata('SourceFilename', ' "test.dwg")')
        assert result['opcode_id'] == 286
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n[TEST 12] Unified dispatcher - Units")
    try:
        result = parse_extended_ascii_metadata('Units', ' "feet" 0.3048 0.0 0.0 0.3048 0.0 0.0)')
        assert result['opcode_id'] == 289
        assert result['units'] == 'feet'
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    # Test 13: Error handling - invalid format
    print("\n[TEST 13] Error handling - invalid PlotInfo")
    try:
        result = parse_opcode_282_plot_info(' invalid data)')
        print(f"  ✗ FAIL: Should have raised ValueError")
    except ValueError as e:
        print(f"  ✓ PASS: Correctly raised ValueError: {e}")

    # Test 14: Error handling - wrong number of points
    print("\n[TEST 14] Error handling - InkedArea with 3 points")
    try:
        result = parse_opcode_316_inked_area(' (0,0) (100,0) (100,100))')
        print(f"  ✗ FAIL: Should have raised ValueError")
    except ValueError as e:
        print(f"  ✓ PASS: Correctly raised ValueError: {e}")

    # Test 15: Drawing Info placeholder
    print("\n[TEST 15] Opcode 365 - DrawingInfo (placeholder)")
    try:
        result = parse_opcode_365_drawing_info(')')
        assert result['opcode_id'] == 365
        assert 'note' in result
        print(f"  ✓ PASS: {result}")
    except Exception as e:
        print(f"  ✗ FAIL: {e}")

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print(__doc__)
    run_tests()
