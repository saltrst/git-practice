"""
DWF Parser Version 1 - Complete Orchestrator

This module provides a complete DWF file parser that imports all 44 agent modules
and dispatches opcodes to the correct handler functions.

The parser supports three types of opcodes:
1. Single-byte opcodes (0x00-0xFF): Direct byte values
2. Extended ASCII opcodes: Start with '(' followed by opcode name
3. Extended Binary opcodes: Start with '{' followed by size and opcode ID

Architecture:
- Reads DWF file byte by byte
- Detects opcode type from first byte
- Dispatches to appropriate handler function
- Returns list of parsed opcode dictionaries

Author: Agent A1 (DWF Orchestrator Builder)
Date: 2025-10-22
"""

import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import struct
import zipfile
from io import BytesIO
from typing import Dict, List, Any, BinaryIO, Optional, Tuple

# Import all 44 agent modules
# Agent 1-3: Basic geometry opcodes
from agents.agent_outputs import agent_01_opcode_0x6C
from agents.agent_outputs import agent_02_opcodes_0x70_0x63
from agents.agent_outputs import agent_03_opcode_0x72

# Agent 4: ASCII geometry
from agents.agent_outputs import agent_04_ascii_geometry

# Agent 5: Binary geometry (16-bit)
from agents.agent_outputs import agent_05_binary_geometry_16bit

# Agent 6: Attributes (color/fill)
from agents.agent_outputs import agent_06_attributes_color_fill

# Agent 7: Attributes (line/visibility)
from agents.agent_outputs import agent_07_attributes_line_visibility

# Agent 8: Text and font
from agents.agent_outputs import agent_08_text_font

# Agent 9: Bezier curves
from agents.agent_outputs import agent_09_bezier_curves

# Agent 10: Gouraud shading
from agents.agent_outputs import agent_10_gouraud_shading

# Agent 11: Macros and markers
from agents.agent_outputs import agent_11_macros_markers

# Agent 12: Object nodes
from agents.agent_outputs import agent_12_object_nodes

# Agent 14: File structure
from agents.agent_outputs import agent_14_file_structure

# Agent 15-17: Metadata
from agents.agent_outputs import agent_15_metadata_1
from agents.agent_outputs import agent_16_metadata_2
from agents.agent_outputs import agent_17_metadata_3

# Agent 18: Attributes (color/layer)
from agents.agent_outputs import agent_18_attributes_color_layer

# Agent 19: Attributes (line style)
from agents.agent_outputs import agent_19_attributes_line_style

# Agent 20: Attributes (fill/merge)
from agents.agent_outputs import agent_20_attributes_fill_merge

# Agent 21: Transparency optimization
from agents.agent_outputs import agent_21_transparency_optimization

# Agent 22: Text and font (extended)
from agents.agent_outputs import agent_22_text_font

# Agent 23: Text formatting
from agents.agent_outputs import agent_23_text_formatting

# Agent 24: Geometry (extended)
from agents.agent_outputs import agent_24_geometry

# Agent 25: Images and URLs
from agents.agent_outputs import agent_25_images_urls

# Agent 26: Structure and GUID
from agents.agent_outputs import agent_26_structure_guid

# Agent 27: Security
from agents.agent_outputs import agent_27_security

# Agent 28-29: Binary images
from agents.agent_outputs import agent_28_binary_images_1
from agents.agent_outputs import agent_29_binary_images_2

# Agent 30: Binary color compression
from agents.agent_outputs import agent_30_binary_color_compression

# Agent 31-32: Binary structure
from agents.agent_outputs import agent_31_binary_structure_1
from agents.agent_outputs import agent_32_binary_structure_2

# Agent 33: Binary advanced
from agents.agent_outputs import agent_33_binary_advanced

# Agent 34: Coordinate transforms
from agents.agent_outputs import agent_34_coordinate_transforms

# Agent 35: Line patterns
from agents.agent_outputs import agent_35_line_patterns

# Agent 36: Color extensions
from agents.agent_outputs import agent_36_color_extensions

# Agent 37: Rendering attributes
from agents.agent_outputs import agent_37_rendering_attributes

# Agent 38: Drawing primitives
from agents.agent_outputs import agent_38_drawing_primitives

# Agent 39: Markers and symbols
from agents.agent_outputs import agent_39_markers_symbols

# Agent 40: Clipping and masking
from agents.agent_outputs import agent_40_clipping_masking

# Agent 41: Text attributes
from agents.agent_outputs import agent_41_text_attributes

# Agent 42: State management
from agents.agent_outputs import agent_42_state_management

# Agent 43: Stream control
from agents.agent_outputs import agent_43_stream_control

# Agent 44: Extended binary final
from agents.agent_outputs import agent_44_extended_binary_final


# =============================================================================
# SINGLE-BYTE OPCODE DISPATCH TABLE (0x00-0xFF)
# =============================================================================

OPCODE_HANDLERS = {
    # Stream control (Agent 43)
    0x00: (agent_43_stream_control, 'parse_opcode_0x00_nop'),
    0x01: (agent_43_stream_control, 'parse_opcode_0x01_stream_version'),
    0xFF: (agent_43_stream_control, 'parse_opcode_0xff_end_of_stream'),

    # Bezier curves (Agent 9)
    0x02: (agent_09_bezier_curves, 'opcode_0x02_bezier_16r'),
    0x42: (agent_09_bezier_curves, 'opcode_0x42_bezier_32r'),
    0x62: (agent_09_bezier_curves, 'opcode_0x62_bezier_32'),
    0x0B: (agent_09_bezier_curves, 'opcode_0x0B_draw_contour_set_16r'),
    0x6B: (agent_09_bezier_curves, 'opcode_0x6B_draw_contour_set_32r'),

    # Color and fill (Agent 6)
    0x03: (agent_06_attributes_color_fill, 'opcode_0x03_set_color_rgba'),
    0x43: (agent_06_attributes_color_fill, 'opcode_0x43_set_color_indexed'),
    0x46: (agent_06_attributes_color_fill, 'opcode_0x46_set_fill_on'),
    0x66: (agent_06_attributes_color_fill, 'opcode_0x66_set_fill_off'),
    0x56: (agent_06_attributes_color_fill, 'opcode_0x56_set_visibility_on'),

    # Binary images (Agent 28)
    0x04: (agent_28_binary_images_1, 'opcode_0x0004_draw_image_indexed'),
    0x05: (agent_28_binary_images_1, 'opcode_0x0005_draw_image_mapped'),
    0x08: (agent_28_binary_images_1, 'opcode_0x0008_draw_image_jpeg'),

    # Text and font (Agent 8)
    0x06: (agent_08_text_font, 'opcode_0x06_set_font'),
    0x18: (agent_08_text_font, 'opcode_0x18_draw_text_complex'),
    0x4F: (agent_08_text_font, 'opcode_0x4F_set_origin_32'),
    0x65: (agent_08_text_font, 'opcode_0x65_draw_ellipse_32r'),
    0x78: (agent_08_text_font, 'opcode_0x78_draw_text_basic'),

    # Gouraud shading (Agent 10)
    0x07: (agent_10_gouraud_shading, 'opcode_0x07_draw_gouraud_polytriangle_16r'),
    0x11: (agent_10_gouraud_shading, 'opcode_0x11_draw_gouraud_polyline_16r'),
    0x67: (agent_10_gouraud_shading, 'opcode_0x67_draw_gouraud_polytriangle_32r'),
    0x71: (agent_10_gouraud_shading, 'opcode_0x71_draw_gouraud_polyline_32r'),
    0x92: (agent_10_gouraud_shading, 'opcode_0x92_draw_circular_arc_32r'),

    # Binary geometry 16-bit (Agent 5)
    0x0C: (agent_05_binary_geometry_16bit, 'opcode_0x0C_draw_line_16r'),
    0x10: (agent_05_binary_geometry_16bit, 'opcode_0x10_draw_polyline_polygon_16r'),
    0x12: (agent_05_binary_geometry_16bit, 'opcode_0x12_draw_circle_16r'),
    0x14: (agent_05_binary_geometry_16bit, 'opcode_0x14_draw_polytriangle_16r'),
    0x74: (agent_05_binary_geometry_16bit, 'opcode_0x74_draw_polytriangle_32r'),

    # Object nodes (Agent 12)
    0x0E: (agent_12_object_nodes, 'parse_opcode_0x0E_object_node_auto'),
    0x4E: (agent_12_object_nodes, 'parse_opcode_0x4E_object_node_32'),
    0x6E: (agent_12_object_nodes, 'parse_opcode_0x6E_object_node_16'),

    # Line and visibility attributes (Agent 7)
    0x17: (agent_07_attributes_line_visibility, 'parse_opcode_0x17_line_weight'),
    0x53: (agent_07_attributes_line_visibility, 'parse_opcode_0x53_macro_scale_ascii'),
    0x73: (agent_07_attributes_line_visibility, 'parse_opcode_0x73_macro_scale_binary'),
    0x76: (agent_07_attributes_line_visibility, 'parse_opcode_0x76_visibility_off'),
    0xCC: (agent_07_attributes_line_visibility, 'parse_opcode_0xCC_line_pattern'),

    # Color extensions (Agent 36)
    0x23: (agent_36_color_extensions, 'parse_opcode_0x23_color_rgb32'),
    0x83: (agent_36_color_extensions, 'parse_opcode_0x83_color_map_index'),
    0xA3: (agent_36_color_extensions, 'parse_opcode_0xA3_background_color'),

    # Rendering attributes (Agent 37)
    0x41: (agent_37_rendering_attributes, 'parse_opcode_0x41_anti_alias'),
    0x48: (agent_37_rendering_attributes, 'parse_opcode_0x48_halftone'),
    0x68: (agent_37_rendering_attributes, 'parse_opcode_0x68_highlight'),

    # Clipping and masking (Agent 40)
    0x44: (agent_40_clipping_masking, 'parse_opcode_0x44_set_clip_region'),
    0x64: (agent_40_clipping_masking, 'parse_opcode_0x64_clear_clip_region'),
    0x84: (agent_40_clipping_masking, 'parse_opcode_0x84_set_mask'),

    # ASCII geometry (Agent 4)
    0x45: (agent_04_ascii_geometry, 'parse_opcode_0x45_ascii_ellipse'),
    0x4C: (agent_04_ascii_geometry, 'parse_opcode_0x4C_ascii_line'),
    0x50: (agent_04_ascii_geometry, 'parse_opcode_0x50_ascii_polyline_polygon'),
    0x52: (agent_04_ascii_geometry, 'parse_opcode_0x52_ascii_circle'),
    0x54: (agent_04_ascii_geometry, 'parse_opcode_0x54_ascii_polytriangle'),

    # Macros and markers (Agent 11)
    0x47: (agent_11_macros_markers, 'parse_opcode_0x47_set_macro_index'),
    0x4D: (agent_11_macros_markers, 'parse_opcode_0x4d_draw_macro_ascii'),
    0x6D: (agent_11_macros_markers, 'parse_opcode_0x6d_draw_macro_32r'),
    0x8D: (agent_11_macros_markers, 'parse_opcode_0x8d_draw_macro_16r'),
    0xAC: (agent_11_macros_markers, 'parse_opcode_0xac_set_layer'),

    # Markers and symbols (Agent 39)
    0x4B: (agent_39_markers_symbols, 'parse_opcode_0x4b_set_marker_symbol'),
    0x8B: (agent_39_markers_symbols, 'parse_opcode_0x8b_draw_marker'),

    # Drawing primitives (Agent 38)
    0x51: (agent_38_drawing_primitives, 'parse_opcode_0x51_quad_ascii'),
    0x91: (agent_38_drawing_primitives, 'parse_opcode_0x91_wedge'),

    # Coordinate transforms (Agent 34)
    0x55: (agent_34_coordinate_transforms, 'parse_opcode_0x55_units_ascii'),
    0x6F: (agent_34_coordinate_transforms, 'parse_opcode_0x6F_origin_16r'),
    0x75: (agent_34_coordinate_transforms, 'parse_opcode_0x75_units_binary'),

    # Line patterns (Agent 35)
    0x57: (agent_35_line_patterns, 'parse_opcode_0x57_pen_width_ascii'),

    # Text attributes (Agent 41)
    0x58: (agent_41_text_attributes, 'parse_opcode_0x58_set_text_rotation'),
    0x98: (agent_41_text_attributes, 'parse_opcode_0x98_set_text_scale'),

    # State management (Agent 42)
    0x5A: (agent_42_state_management, 'parse_opcode_0x5a_save_state'),
    0x7A: (agent_42_state_management, 'parse_opcode_0x7a_restore_state'),
    0x9A: (agent_42_state_management, 'parse_opcode_0x9a_reset_state'),

    # Basic geometry (Agents 1-3)
    0x63: (agent_02_opcodes_0x70_0x63, 'parse_opcode_0x63_color'),
    0x6C: (agent_01_opcode_0x6C, 'opcode_0x6C_binary_line'),
    0x70: (agent_02_opcodes_0x70_0x63, 'parse_opcode_0x70_polygon'),
    0x72: (agent_03_opcode_0x72, 'opcode_0x72_binary_rectangle'),
}


# =============================================================================
# EXTENDED ASCII OPCODE HANDLERS (Start with '(')
# =============================================================================

# Extended ASCII opcodes are identified by name after opening '('
# Format: (OpcodeName ...data...)
EXTENDED_ASCII_HANDLERS = {
    # Metadata (Agent 15)
    'Author': (agent_15_metadata_1, 'parse_opcode_author'),
    'Comments': (agent_15_metadata_1, 'parse_opcode_comments'),
    'Copyright': (agent_15_metadata_1, 'parse_opcode_copyright'),
    'Creator': (agent_15_metadata_1, 'parse_opcode_creator'),
    'CreationTime': (agent_15_metadata_1, 'parse_opcode_creation_time'),
    'ModificationTime': (agent_15_metadata_1, 'parse_opcode_modification_time'),

    # Metadata (Agent 16)
    'Title': (agent_16_metadata_2, 'parse_opcode_title'),
    'Subject': (agent_16_metadata_2, 'parse_opcode_subject'),
    'Keywords': (agent_16_metadata_2, 'parse_opcode_keywords'),

    # Metadata (Agent 17)
    'SourceFilename': (agent_17_metadata_3, 'parse_opcode_286_source_filename'),
    'PlotInfo': (agent_17_metadata_3, 'parse_opcode_282_plot_info'),
    'Units': (agent_17_metadata_3, 'parse_opcode_289_define_units'),
    'InkedArea': (agent_17_metadata_3, 'parse_opcode_316_set_inked_area'),
    'Time': (agent_17_metadata_3, 'parse_opcode_334_filetime'),

    # Extended geometry (Agent 24)
    'Circle': (agent_24_geometry, 'handle_circle'),
    'Ellipse': (agent_24_geometry, 'handle_ellipse'),
    'Contour': (agent_24_geometry, 'handle_contour'),
    'GouraudPolytriangle': (agent_24_geometry, 'handle_gouraud_polytriangle'),
    'GouraudPolyline': (agent_24_geometry, 'handle_gouraud_polyline'),
    'Bezier': (agent_24_geometry, 'handle_bezier'),

    # Images and URLs (Agent 25)
    'DrawImage': (agent_25_images_urls, 'handle_draw_image'),
    'DrawPNGGroup4Image': (agent_25_images_urls, 'handle_draw_png_group4_image'),
    'Embed': (agent_25_images_urls, 'handle_define_embed'),
    'URL': (agent_25_images_urls, 'handle_set_url'),
    'AttributeURL': (agent_25_images_urls, 'handle_attribute_url'),

    # Structure and GUID (Agent 26)
    'GUID': (agent_26_structure_guid, 'handle_guid_ascii'),
    'GUIDList': (agent_26_structure_guid, 'handle_guid_list_ascii'),
    'BlockRef': (agent_26_structure_guid, 'handle_blockref_ascii'),
    'Directory': (agent_26_structure_guid, 'handle_directory_ascii'),
    'UserData': (agent_26_structure_guid, 'handle_userdata_ascii'),
    'ObjectNode': (agent_26_structure_guid, 'handle_object_node_ascii'),
}


# =============================================================================
# EXTENDED BINARY OPCODE HANDLERS (Start with '{')
# =============================================================================

# Extended Binary opcodes are identified by 16-bit opcode ID after size field
# Format: { + size(4 bytes LE) + opcode(2 bytes LE) + data + }
EXTENDED_BINARY_HANDLERS = {
    # Binary images (Agent 28)
    0x0006: (agent_28_binary_images_1, 'opcode_0x0006_draw_image_rgb'),
    0x0007: (agent_28_binary_images_1, 'opcode_0x0007_draw_image_rgba'),
    0x0008: (agent_28_binary_images_1, 'opcode_0x0008_draw_image_jpeg'),
    0x000C: (agent_28_binary_images_1, 'opcode_0x000C_draw_image_png'),

    # Binary images (Agent 29)
    0x0009: (agent_29_binary_images_2, 'handle_bitonal_mapped'),
    0x000A: (agent_29_binary_images_2, 'handle_group3x_mapped'),
    0x000B: (agent_29_binary_images_2, 'handle_group4'),
    0x000D: (agent_29_binary_images_2, 'handle_group4x_mapped'),

    # Binary structure (Agent 31)
    0x0010: (agent_31_binary_structure_1, 'handle_graphics_hdr'),
    0x0011: (agent_31_binary_structure_1, 'handle_overlay_hdr'),
    0x0012: (agent_31_binary_structure_1, 'handle_redline_hdr'),

    # Binary structure (Agent 32)
    0x0020: (agent_32_binary_structure_2, 'handle_user_block'),
    0x0021: (agent_32_binary_structure_2, 'handle_null_block'),
    0x0022: (agent_32_binary_structure_2, 'handle_global_sheet_block'),

    # Security (Agent 44)
    0x0027: (agent_44_extended_binary_final, 'parse_extended_binary_header'),
}


# =============================================================================
# MAIN PARSER FUNCTIONS
# =============================================================================

def open_dwf_or_dwfx(file_path: str) -> Tuple[List[BinaryIO], str]:
    """
    Opens DWF or DWFX file and returns W2D streams if available.

    This preprocessing layer handles three file format variants:
    1. Classic DWF (pre-6.0): Direct W2D opcode stream
    2. DWF 6.0+ / DWFX with W2D: ZIP container with W2D binary streams
    3. DWFX with XPS: ZIP container with XML FixedPage graphics (not supported)

    Args:
        file_path: Path to DWF or DWFX file

    Returns:
        Tuple of (list of W2D binary streams, format_type)

        format_type values:
        - "classic_dwf": Pre-6.0 DWF with direct opcode stream
        - "dwf_w2d": DWF 6.0+ ZIP container with W2D streams
        - "dwfx_w2d": DWFX ZIP container with W2D streams
        - "dwfx_xps": DWFX with XPS FixedPage graphics (no W2D)

    Raises:
        ValueError: If file format is invalid or unrecognized

    Example:
        >>> streams, fmt = open_dwf_or_dwfx("drawing.dwf")
        >>> fmt
        'classic_dwf'
        >>> streams, fmt = open_dwf_or_dwfx("drawing.dwfx")
        >>> fmt
        'dwfx_w2d'
    """
    try:
        # Try to open as ZIP container (DWF 6.0+ or DWFX)
        with zipfile.ZipFile(file_path, 'r') as zf:
            filelist = zf.namelist()

            # Look for W2D streams (typically in sections/ directory)
            w2d_files = [f for f in filelist if f.endswith('.w2d')]

            if w2d_files:
                # Success: Found W2D streams in ZIP container
                w2d_streams = []
                for w2d_file in w2d_files:
                    w2d_streams.append(BytesIO(zf.read(w2d_file)))

                # Determine if DWF 6.0+ or DWFX based on manifest structure
                # DWFX contains XPS FixedPage files even when W2D is present
                if any('FixedPage' in f for f in filelist):
                    return w2d_streams, "dwfx_w2d"
                else:
                    return w2d_streams, "dwf_w2d"

            # No W2D files found - check if XPS-based DWFX
            elif any('FixedPage' in f for f in filelist):
                # XPS-based DWFX (no W2D streams available)
                return [], "dwfx_xps"

            else:
                # ZIP container but no recognizable DWF/DWFX content
                raise ValueError(
                    f"ZIP container found but no recognizable DWF/DWFX content. "
                    f"Expected .w2d files or FixedPage files."
                )

    except zipfile.BadZipFile:
        # Not a ZIP file - try classic DWF format (pre-6.0)
        with open(file_path, 'rb') as f:
            content = f.read()

            # Verify DWF header: "(DWF V"
            if content.startswith(b'(DWF V'):
                return [BytesIO(content)], "classic_dwf"
            else:
                raise ValueError(
                    f"Not a valid DWF file. Expected '(DWF V' header at start of file, "
                    f"but found: {content[:12]!r}"
                )


def parse_dwf_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a DWF or DWFX file and return a list of parsed opcodes.

    This function automatically detects and handles multiple DWF format variants:
    - Classic DWF (pre-6.0): Direct W2D opcode stream
    - DWF 6.0+: ZIP container with W2D streams
    - DWFX with W2D: ZIP container with W2D streams + XPS manifest

    For each W2D stream found, the parser reads byte by byte, detects opcode types,
    and dispatches each opcode to the appropriate handler function from the 44 agents.

    Args:
        file_path: Path to the DWF or DWFX file to parse

    Returns:
        List of dictionaries containing parsed opcode data from all W2D streams

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
        NotImplementedError: If file is XPS-based DWFX without W2D streams

    Supported Formats:
        ✓ Classic DWF (.dwf) - Pre-6.0 format with direct opcode stream
        ✓ DWF 6.0+ (.dwf) - ZIP container with W2D binary streams
        ✓ DWFX (.dwfx) - With W2D streams (hybrid W2D + XPS format)
        ✗ DWFX (.dwfx) - XPS-only format without W2D (raises NotImplementedError)

    Example:
        >>> opcodes = parse_dwf_file("drawing.dwf")
        >>> len(opcodes)
        983
        >>> opcodes[0]['type']
        'polytriangle_16r'

        >>> opcodes = parse_dwf_file("drawing.dwfx")  # With W2D streams
        >>> len(opcodes)
        1523

        >>> opcodes = parse_dwf_file("xps_only.dwfx")  # XPS-only
        NotImplementedError: File uses XPS FixedPage format...
    """
    # Use preprocessing layer to detect format and extract W2D streams
    streams, format_type = open_dwf_or_dwfx(file_path)

    # Handle XPS-only DWFX files (no W2D streams available)
    if format_type == "dwfx_xps":
        raise NotImplementedError(
            f"\nFile '{file_path}' is XPS-based DWFX format without W2D streams.\n\n"
            f"This format uses XML FixedPage graphics instead of binary W2D opcodes.\n"
            f"Current parser only supports W2D-based formats:\n"
            f"  ✓ Classic DWF (pre-6.0)\n"
            f"  ✓ DWF 6.0+ (ZIP with W2D)\n"
            f"  ✓ DWFX with W2D streams (hybrid format)\n\n"
            f"Options to convert this file:\n"
            f"  1. Use Autodesk DWG TrueView to convert DWFX → DWF\n"
            f"  2. Export from source application as W2D-based DWFX or DWF\n"
            f"  3. Extract raster images from FixedPage XML (lossy conversion)\n"
        )

    # Parse all W2D streams using existing parser (works for all W2D-based formats)
    all_opcodes = []
    for stream in streams:
        opcodes = parse_dwf_stream(stream)
        all_opcodes.extend(opcodes)

    return all_opcodes


def parse_dwf_stream(stream: BinaryIO) -> List[Dict[str, Any]]:
    """
    Parse a DWF stream and return a list of parsed opcodes.

    This function reads a binary stream byte by byte, detects opcode types,
    and dispatches each opcode to the appropriate handler function.

    Supported opcode types:
    1. Single-byte opcodes (0x00-0xFF): Direct byte values
    2. Extended ASCII opcodes: Start with '(' followed by opcode name
    3. Extended Binary opcodes: Start with '{' followed by size and opcode ID

    Args:
        stream: Binary stream to parse (file-like object with read() method)

    Returns:
        List of dictionaries containing parsed opcode data

    Raises:
        ValueError: If an unknown opcode is encountered

    Example:
        >>> from io import BytesIO
        >>> data = b'\\x6C' + struct.pack('<llll', 0, 100, 200, 300)
        >>> stream = BytesIO(data)
        >>> opcodes = parse_dwf_stream(stream)
        >>> opcodes[0]['type']
        'line'
    """
    opcodes = []

    while True:
        # Read next opcode byte
        opcode_byte = stream.read(1)

        # Check for end of stream
        if not opcode_byte:
            break

        opcode_value = opcode_byte[0]

        try:
            # Detect opcode type and dispatch
            if opcode_value == ord('('):
                # Extended ASCII opcode
                result = parse_extended_ascii_opcode(stream)
            elif opcode_value == ord('{'):
                # Extended Binary opcode
                result = parse_extended_binary_opcode(stream)
            elif opcode_value in OPCODE_HANDLERS:
                # Single-byte opcode
                module, func_name = OPCODE_HANDLERS[opcode_value]
                handler_func = getattr(module, func_name)
                result = handler_func(stream)

                # Add opcode metadata
                if isinstance(result, dict):
                    result['opcode_byte'] = opcode_value
                    result['opcode_hex'] = f'0x{opcode_value:02X}'
            else:
                # Unknown opcode
                result = {
                    'type': 'unknown',
                    'opcode_byte': opcode_value,
                    'opcode_hex': f'0x{opcode_value:02X}',
                    'error': f'Unknown opcode: 0x{opcode_value:02X}'
                }

            opcodes.append(result)

            # Check for end-of-stream marker
            if opcode_value == 0xFF:
                break

        except Exception as e:
            # Error handling - capture error but continue parsing
            opcodes.append({
                'type': 'error',
                'opcode_byte': opcode_value,
                'opcode_hex': f'0x{opcode_value:02X}',
                'error': str(e),
                'error_type': type(e).__name__
            })

    return opcodes


def parse_extended_ascii_opcode(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse an Extended ASCII opcode from stream.

    Format: (OpcodeName ...data...)
    The opening '(' has already been read by the caller.

    Args:
        stream: Binary stream positioned after opening '('

    Returns:
        Dictionary containing parsed opcode data

    Raises:
        ValueError: If the format is invalid
    """
    # Read until we find the opcode name (first word after '(')
    buffer = []
    opcode_name = []
    in_name = False
    paren_depth = 1

    # Read characters to build the complete extended ASCII opcode
    while paren_depth > 0:
        char_byte = stream.read(1)
        if not char_byte:
            raise ValueError("Unexpected end of stream in Extended ASCII opcode")

        char = char_byte.decode('ascii', errors='ignore')
        buffer.append(char)

        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif not in_name and char.isalpha():
            # Start of opcode name
            in_name = True
            opcode_name.append(char)
        elif in_name and (char.isalnum() or char in '_'):
            # Continue opcode name
            opcode_name.append(char)
        elif in_name and (char.isspace() or char == ')'):
            # End of opcode name
            in_name = False

    # Convert to string
    opcode_name_str = ''.join(opcode_name)
    data_str = ''.join(buffer)

    # Look up handler
    if opcode_name_str in EXTENDED_ASCII_HANDLERS:
        module, func_name = EXTENDED_ASCII_HANDLERS[opcode_name_str]
        handler_func = getattr(module, func_name)

        # Call handler with data after opcode name
        result = handler_func(data_str)
        result['format'] = 'extended_ascii'
        return result
    else:
        return {
            'type': 'unknown_extended_ascii',
            'opcode_name': opcode_name_str,
            'data': data_str,
            'format': 'extended_ascii',
            'error': f'Unknown Extended ASCII opcode: {opcode_name_str}'
        }


def parse_extended_binary_opcode(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse an Extended Binary opcode from stream.

    Format: { + size(4 bytes LE) + opcode(2 bytes LE) + data + }
    The opening '{' has already been read by the caller.

    Args:
        stream: Binary stream positioned after opening '{'

    Returns:
        Dictionary containing parsed opcode data

    Raises:
        ValueError: If the format is invalid
    """
    # Read size field (4 bytes, little-endian)
    size_bytes = stream.read(4)
    if len(size_bytes) != 4:
        raise ValueError(f"Expected 4 bytes for size field, got {len(size_bytes)}")

    size = struct.unpack('<I', size_bytes)[0]

    # Read opcode ID (2 bytes, little-endian)
    opcode_bytes = stream.read(2)
    if len(opcode_bytes) != 2:
        raise ValueError(f"Expected 2 bytes for opcode ID, got {len(opcode_bytes)}")

    opcode_id = struct.unpack('<H', opcode_bytes)[0]

    # Calculate data size (size - opcode(2) - closing_brace(1))
    data_size = size - 2 - 1

    # Look up handler
    if opcode_id in EXTENDED_BINARY_HANDLERS:
        module, func_name = EXTENDED_BINARY_HANDLERS[opcode_id]
        handler_func = getattr(module, func_name)

        # Some handlers expect the stream, others expect to parse the header themselves
        # For now, we'll pass the stream positioned at the data
        result = handler_func(stream)
        result['format'] = 'extended_binary'
        result['opcode_id'] = opcode_id

        # Read closing brace
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected closing '}}', got {closing!r}")

        return result
    else:
        # Unknown Extended Binary opcode - read and skip data
        data = stream.read(data_size)
        closing = stream.read(1)

        if closing != b'}':
            raise ValueError(f"Expected closing '}}', got {closing!r}")

        return {
            'type': 'unknown_extended_binary',
            'opcode_id': opcode_id,
            'opcode_hex': f'0x{opcode_id:04X}',
            'data_size': data_size,
            'format': 'extended_binary',
            'error': f'Unknown Extended Binary opcode: 0x{opcode_id:04X}'
        }


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_parser():
    """
    Test the DWF parser with sample opcodes.

    This test creates a BytesIO stream with 3 opcodes:
    1. Single-byte line opcode (0x6C)
    2. Single-byte polygon opcode (0x70)
    3. Single-byte color opcode (0x63)
    """
    print("=" * 80)
    print("DWF Parser V1 - Test Suite")
    print("=" * 80)
    print()

    # Test 1: Single-byte line opcode (0x6C)
    print("Test 1: Single-byte line opcode (0x6C)")
    print("-" * 80)
    line_data = b'\x6C' + struct.pack('<llll', 0, 100, 200, 300)
    stream = BytesIO(line_data)
    opcodes = parse_dwf_stream(stream)
    print(f"Parsed {len(opcodes)} opcode(s)")
    print(f"Result: {opcodes[0]}")
    assert opcodes[0]['type'] == 'line'
    assert opcodes[0]['start'] == (0, 100)
    assert opcodes[0]['end'] == (200, 300)
    print("PASS")
    print()

    # Test 2: Single-byte polygon opcode (0x70)
    print("Test 2: Single-byte polygon opcode (0x70)")
    print("-" * 80)
    polygon_data = b'\x70' + struct.pack('<B', 3)  # 3 vertices
    polygon_data += struct.pack('<llllll', 0, 0, 100, 0, 50, 100)
    stream = BytesIO(polygon_data)
    opcodes = parse_dwf_stream(stream)
    print(f"Parsed {len(opcodes)} opcode(s)")
    print(f"Result: {opcodes[0]}")
    assert opcodes[0]['vertex_count'] == 3
    assert len(opcodes[0]['vertices']) == 3
    print("PASS")
    print()

    # Test 3: Single-byte color opcode (0x63)
    print("Test 3: Single-byte color opcode (0x63)")
    print("-" * 80)
    color_data = b'\x63' + struct.pack('<B', 42)
    stream = BytesIO(color_data)
    opcodes = parse_dwf_stream(stream)
    print(f"Parsed {len(opcodes)} opcode(s)")
    print(f"Result: {opcodes[0]}")
    assert opcodes[0]['color_index'] == 42
    print("PASS")
    print()

    # Test 4: Multiple opcodes in sequence
    print("Test 4: Multiple opcodes in sequence")
    print("-" * 80)
    multi_data = b'\x6C' + struct.pack('<llll', 0, 100, 200, 300)  # Line
    multi_data += b'\x63' + struct.pack('<B', 42)  # Color
    multi_data += b'\x70' + struct.pack('<B', 3)  # Polygon with 3 vertices
    multi_data += struct.pack('<llllll', 0, 0, 100, 0, 50, 100)
    stream = BytesIO(multi_data)
    opcodes = parse_dwf_stream(stream)
    print(f"Parsed {len(opcodes)} opcode(s)")
    for i, opcode in enumerate(opcodes):
        print(f"  Opcode {i+1}: {opcode.get('type', 'unknown')} - {opcode.get('opcode_hex', 'N/A')}")
    assert len(opcodes) == 3
    assert opcodes[0]['type'] == 'line'
    assert opcodes[1]['color_index'] == 42
    assert opcodes[2]['vertex_count'] == 3
    print("PASS")
    print()

    print("=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - Total single-byte opcodes supported: {len(OPCODE_HANDLERS)}")
    print(f"  - Total Extended ASCII opcodes supported: {len(EXTENDED_ASCII_HANDLERS)}")
    print(f"  - Total Extended Binary opcodes supported: {len(EXTENDED_BINARY_HANDLERS)}")
    print(f"  - Total opcodes: {len(OPCODE_HANDLERS) + len(EXTENDED_ASCII_HANDLERS) + len(EXTENDED_BINARY_HANDLERS)}")
    print()


if __name__ == '__main__':
    test_parser()
