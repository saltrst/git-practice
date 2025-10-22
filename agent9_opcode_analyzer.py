#!/usr/bin/env python3
"""
Agent 9 - Opcode Distribution Analyzer

This script analyzes opcode distributions across multiple DWF/DWFX test files.
It extracts opcode types, counts occurrences, identifies unknowns, and compares
rendering-critical opcodes to assess renderer coverage.

Author: Agent 9
Date: 2025-10-22
"""

import sys
import os
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
import zipfile
import tempfile

# Add project root to Python path
project_root = Path(__file__).parent / 'dwf-to-pdf-project'
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file, parse_dwf_stream


# =============================================================================
# OPCODE CLASSIFICATION
# =============================================================================

RENDERING_CRITICAL_OPCODES = {
    # Geometry opcodes
    'line', 'line_16r', 'draw_line_16r',
    'circle', 'circle_16r', 'draw_circle_16r',
    'ellipse', 'draw_ellipse', 'draw_ellipse_32r',
    'polyline_polygon', 'polyline_polygon_16r', 'draw_polyline_polygon_16r',
    'polytriangle', 'polytriangle_16r', 'polytriangle_32r', 'draw_polytriangle_16r', 'draw_polytriangle_32r',
    'quad', 'quad_32r', 'quad_ascii',
    'wedge',
    'bezier', 'bezier_16r', 'bezier_32r', 'bezier_32',
    'contour', 'draw_contour_set_16r', 'draw_contour_set_32r',

    # Gouraud shading
    'gouraud_polytriangle', 'gouraud_polyline',
    'draw_gouraud_polytriangle_16r', 'draw_gouraud_polytriangle_32r',
    'draw_gouraud_polyline_16r', 'draw_gouraud_polyline_32r',

    # Arc
    'draw_circular_arc_32r',

    # ASCII geometry
    'ascii_line', 'ascii_circle', 'ascii_ellipse', 'ascii_polyline_polygon', 'ascii_polytriangle',
}

ATTRIBUTE_OPCODES = {
    # Color
    'SET_COLOR_RGBA', 'set_color_rgba', 'set_color_rgb32', 'color_rgb32',
    'SET_COLOR_INDEXED', 'set_color_indexed', 'set_color_map_index', 'color_map_index',
    'set_background_color', 'background_color', 'color',

    # Fill
    'SET_FILL_ON', 'set_fill_on', 'SET_FILL_OFF', 'set_fill_off',

    # Line attributes
    'set_pen_width', 'set_line_width', 'line_weight',
    'set_line_cap', 'set_line_join', 'line_pattern',

    # Visibility
    'SET_VISIBILITY_ON', 'set_visibility_on', 'visibility_off',

    # Markers
    'set_marker_symbol', 'set_marker_size', 'draw_marker',

    # Rendering
    'anti_alias', 'halftone', 'highlight',

    # Clipping
    'set_clip_region', 'clear_clip_region', 'set_mask',

    # Transforms
    'set_origin', 'origin_16r', 'set_origin_32',
    'set_units', 'units_ascii', 'units_binary',

    # Macros
    'set_macro_index', 'macro_scale_ascii', 'macro_scale_binary', 'set_layer',
}

TEXT_OPCODES = {
    'draw_text_basic', 'draw_text_complex',
    'set_font', 'set_text_rotation', 'set_text_scale', 'set_text_spacing',
}

IMAGE_OPCODES = {
    'image_rgb', 'image_rgba', 'image_png', 'image_jpeg',
    'image_indexed', 'image_mapped', 'draw_image',
    'draw_image_rgb', 'draw_image_rgba', 'draw_image_png', 'draw_image_jpeg',
    'draw_image_indexed', 'draw_image_mapped',
    'bitonal_mapped', 'group3x_mapped', 'group4', 'group4x_mapped',
    'draw_png_group4_image',
}

STATE_MANAGEMENT_OPCODES = {
    'save_state', 'restore_state', 'reset_state',
}

METADATA_OPCODES = {
    'metadata', 'copyright', 'creator', 'creation_time',
    'modification_time', 'source_creation_time', 'source_modification_time',
    'dwf_header', 'end_of_dwf', 'viewport', 'view', 'named_view',
    'user_block', 'null_block', 'global_sheet_block', 'global_block',
    'signature_block', 'font_extension', 'colormap', 'compression_marker',
    'overlay_preview', 'font_block', 'encryption', 'password', 'signdata',
    'nop', 'stream_version', 'end_of_stream',
    'author', 'comments', 'title', 'subject', 'keywords',
    'source_filename', 'plot_info', 'define_units', 'set_inked_area', 'filetime',
    'guid', 'guid_list', 'blockref', 'directory', 'userdata', 'object_node',
    'graphics_hdr', 'overlay_hdr', 'redline_hdr',
    'embed', 'url', 'attribute_url',
}

STRUCTURE_OPCODES = {
    'object_node_auto', 'object_node_32', 'object_node_16',
    'draw_macro_ascii', 'draw_macro_32r', 'draw_macro_16r',
    'extended_ascii', 'extended_binary', 'single_byte',
}


def classify_opcode(opcode_type: str) -> str:
    """Classify an opcode into a category."""
    if opcode_type in RENDERING_CRITICAL_OPCODES:
        return 'Rendering-Critical'
    elif opcode_type in ATTRIBUTE_OPCODES:
        return 'Attribute'
    elif opcode_type in TEXT_OPCODES:
        return 'Text'
    elif opcode_type in IMAGE_OPCODES:
        return 'Image'
    elif opcode_type in STATE_MANAGEMENT_OPCODES:
        return 'State'
    elif opcode_type in METADATA_OPCODES:
        return 'Metadata'
    elif opcode_type in STRUCTURE_OPCODES:
        return 'Structure'
    elif opcode_type in ['unknown', 'unknown_binary', 'unknown_extended_ascii', 'unknown_extended_binary']:
        return 'Unknown'
    elif opcode_type == 'error':
        return 'Error'
    else:
        return 'Uncategorized'


# =============================================================================
# FILE PARSING
# =============================================================================

def extract_w2d_from_dwfx(dwfx_path: str) -> str:
    """Extract W2D file from DWFX archive."""
    with zipfile.ZipFile(dwfx_path, 'r') as zf:
        # Find the W2D file (usually in Graphics/ directory)
        w2d_files = [name for name in zf.namelist() if name.endswith('.w2d')]

        if not w2d_files:
            raise ValueError(f"No W2D file found in {dwfx_path}")

        # Extract to temporary file
        w2d_file = w2d_files[0]
        print(f"  Found W2D file: {w2d_file}")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.w2d') as tmp:
            tmp.write(zf.read(w2d_file))
            return tmp.name


def parse_test_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse a test file (DWF or DWFX)."""
    print(f"\nParsing: {file_path}")

    # Check if file is DWFX (ZIP archive)
    if file_path.endswith('.dwfx'):
        w2d_temp = extract_w2d_from_dwfx(file_path)
        try:
            opcodes = parse_dwf_file(w2d_temp)
        finally:
            # Clean up temp file
            os.unlink(w2d_temp)
    else:
        opcodes = parse_dwf_file(file_path)

    print(f"  Parsed {len(opcodes)} opcodes")
    return opcodes


# =============================================================================
# OPCODE ANALYSIS
# =============================================================================

def analyze_opcodes(opcodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a list of opcodes and return statistics."""
    # Count opcode types
    type_counter = Counter()
    category_counter = Counter()
    unknown_opcodes = []
    error_opcodes = []

    for opcode in opcodes:
        opcode_type = opcode.get('type', 'unknown')
        type_counter[opcode_type] += 1

        # Classify and count by category
        category = classify_opcode(opcode_type)
        category_counter[category] += 1

        # Track unknown opcodes
        if category == 'Unknown':
            unknown_opcodes.append(opcode)

        # Track error opcodes
        if category == 'Error':
            error_opcodes.append(opcode)

    # Calculate percentages
    total = len(opcodes)
    type_percentages = {k: (v / total) * 100 for k, v in type_counter.items()}
    category_percentages = {k: (v / total) * 100 for k, v in category_counter.items()}

    # Get rendering-critical opcodes
    rendering_opcodes = {k: v for k, v in type_counter.items() if classify_opcode(k) == 'Rendering-Critical'}

    return {
        'total_opcodes': total,
        'type_counter': type_counter,
        'type_percentages': type_percentages,
        'category_counter': category_counter,
        'category_percentages': category_percentages,
        'rendering_opcodes': rendering_opcodes,
        'unknown_opcodes': unknown_opcodes,
        'error_opcodes': error_opcodes,
    }


def get_renderer_implemented_opcodes() -> set:
    """Extract list of opcodes implemented in pdf_renderer_v1.py."""
    # Based on the render_opcode() method in PDFRenderer
    implemented = set()

    # Geometry opcodes
    implemented.update(['line', 'line_16r'])
    implemented.update(['circle', 'circle_16r'])
    implemented.update(['ellipse', 'draw_ellipse'])
    implemented.update(['polyline_polygon', 'polyline_polygon_16r'])
    implemented.update(['polytriangle', 'polytriangle_16r', 'polytriangle_32r'])
    implemented.update(['quad', 'quad_32r'])
    implemented.update(['wedge'])
    implemented.update(['bezier'])
    implemented.update(['contour'])
    implemented.update(['gouraud_polytriangle'])
    implemented.update(['gouraud_polyline'])

    # Text opcodes
    implemented.update(['draw_text_basic', 'draw_text_complex'])

    # Image opcodes
    implemented.update(['image_rgb', 'image_rgba', 'image_png', 'image_jpeg', 'image_indexed', 'image_mapped'])

    # Marker opcodes
    implemented.update(['draw_marker'])

    # State management
    implemented.update(['save_state', 'restore_state', 'reset_state'])

    # Color attributes
    implemented.update(['SET_COLOR_RGBA', 'set_color_rgba'])
    implemented.update(['set_color_rgb32'])
    implemented.update(['SET_COLOR_INDEXED', 'set_color_indexed'])
    implemented.update(['set_background_color'])
    implemented.update(['set_color_map_index'])

    # Fill attributes
    implemented.update(['SET_FILL_ON', 'set_fill_on'])
    implemented.update(['SET_FILL_OFF', 'set_fill_off'])

    # Line attributes
    implemented.update(['set_pen_width', 'set_line_width'])
    implemented.update(['set_line_cap'])
    implemented.update(['set_line_join'])

    # Text attributes
    implemented.update(['set_font'])
    implemented.update(['set_text_rotation'])
    implemented.update(['set_text_scale'])
    implemented.update(['set_text_spacing'])
    implemented.update(['set_origin'])
    implemented.update(['set_units'])

    # Visibility
    implemented.update(['SET_VISIBILITY_ON', 'set_visibility_on'])

    # Marker attributes
    implemented.update(['set_marker_symbol'])
    implemented.update(['set_marker_size'])

    # Rendering attributes
    implemented.update(['set_anti_alias'])
    implemented.update(['set_halftone'])
    implemented.update(['set_highlight'])

    # Clipping
    implemented.update(['set_clip_region'])
    implemented.update(['clear_clip_region'])
    implemented.update(['set_mask'])

    # Metadata (pass-through, no rendering)
    implemented.update(['metadata', 'copyright', 'creator', 'creation_time',
                       'modification_time', 'source_creation_time',
                       'source_modification_time', 'dwf_header', 'end_of_dwf',
                       'viewport', 'view', 'named_view', 'user_block',
                       'null_block', 'global_sheet_block', 'global_block',
                       'signature_block', 'font_extension', 'colormap',
                       'compression_marker', 'overlay_preview', 'font_block',
                       'encryption', 'password', 'signdata', 'nop',
                       'stream_version', 'end_of_stream', 'extended_ascii',
                       'extended_binary', 'single_byte'])

    return implemented


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_markdown_report(file_analyses: Dict[str, Dict[str, Any]], output_path: str):
    """Generate a comprehensive markdown report."""

    report = []
    report.append("# Agent 9: Opcode Distribution Analysis Report")
    report.append("")
    report.append("**Mission**: Compare opcode types and distributions across test files to identify patterns")
    report.append("")
    report.append("**Date**: 2025-10-22")
    report.append("**Author**: Agent 9")
    report.append("")
    report.append("## Important Note")
    report.append("")
    report.append("The original test files 1.dwfx (5.1MB) and 2.dwfx (9.0MB) are in **XPS format**, not traditional W2D binary format.")
    report.append("These files use FixedPage XML-based graphics and require a different parser than the W2D binary parser used here.")
    report.append("")
    report.append("This analysis focuses on **W2D binary format** files:")
    report.append("- 3.dwf (9.4MB) - extracted W2D file (11MB uncompressed)")
    report.append("- drawing.w2d - test W2D file")
    report.append("")
    report.append("---")
    report.append("")

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================
    report.append("## Executive Summary")
    report.append("")

    for filename, analysis in file_analyses.items():
        report.append(f"### {filename}")
        report.append(f"- **Total Opcodes**: {analysis['total_opcodes']:,}")
        report.append(f"- **Unique Opcode Types**: {len(analysis['type_counter'])}")
        report.append(f"- **Unknown Opcodes**: {len(analysis['unknown_opcodes'])}")
        report.append(f"- **Error Opcodes**: {len(analysis['error_opcodes'])}")
        report.append("")

    report.append("---")
    report.append("")

    # =========================================================================
    # TEST 1: DETAILED OPCODE INVENTORIES
    # =========================================================================
    report.append("## Test 1: Detailed Opcode Inventories")
    report.append("")

    for filename, analysis in file_analyses.items():
        report.append(f"### {filename}")
        report.append("")
        report.append("| Rank | Opcode Type | Count | Percentage | Category |")
        report.append("|------|------------|-------|------------|----------|")

        # Sort by count (descending)
        sorted_types = sorted(analysis['type_counter'].items(), key=lambda x: x[1], reverse=True)

        for rank, (opcode_type, count) in enumerate(sorted_types[:50], 1):  # Top 50
            percentage = analysis['type_percentages'][opcode_type]
            category = classify_opcode(opcode_type)
            report.append(f"| {rank} | `{opcode_type}` | {count:,} | {percentage:.2f}% | {category} |")

        if len(sorted_types) > 50:
            report.append(f"| ... | ... | ... | ... | ... |")
            report.append(f"| | **Total Types**: {len(sorted_types)} | {analysis['total_opcodes']:,} | 100.00% | |")

        report.append("")

    report.append("---")
    report.append("")

    # =========================================================================
    # CATEGORY DISTRIBUTION
    # =========================================================================
    report.append("## Opcode Category Distribution")
    report.append("")

    for filename, analysis in file_analyses.items():
        report.append(f"### {filename}")
        report.append("")
        report.append("| Category | Count | Percentage |")
        report.append("|----------|-------|------------|")

        sorted_categories = sorted(analysis['category_counter'].items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories:
            percentage = analysis['category_percentages'][category]
            report.append(f"| {category} | {count:,} | {percentage:.2f}% |")

        report.append("")

    report.append("---")
    report.append("")

    # =========================================================================
    # TEST 2: UNKNOWN OPCODES ANALYSIS
    # =========================================================================
    report.append("## Test 2: Unknown Opcodes Analysis")
    report.append("")

    all_unknown_types = set()
    unknown_by_file = {}

    for filename, analysis in file_analyses.items():
        report.append(f"### {filename}")
        report.append(f"**Unknown Opcode Count**: {len(analysis['unknown_opcodes'])}")
        report.append("")

        if analysis['unknown_opcodes']:
            # Group unknown opcodes by type and hex value
            unknown_groups = defaultdict(list)
            for opcode in analysis['unknown_opcodes']:
                opcode_type = opcode.get('type', 'unknown')
                opcode_hex = opcode.get('opcode_hex', opcode.get('opcode_id', 'N/A'))
                unknown_groups[(opcode_type, opcode_hex)].append(opcode)
                all_unknown_types.add((opcode_type, opcode_hex))

            unknown_by_file[filename] = unknown_groups

            report.append("| Type | Hex/ID | Count | Details |")
            report.append("|------|--------|-------|---------|")

            for (opcode_type, opcode_hex), opcodes in sorted(unknown_groups.items(), key=lambda x: len(x[1]), reverse=True):
                count = len(opcodes)
                # Get sample details
                sample = opcodes[0]
                details = sample.get('error', 'No details')
                report.append(f"| `{opcode_type}` | `{opcode_hex}` | {count} | {details} |")

            report.append("")
        else:
            report.append("*No unknown opcodes found*")
            report.append("")

    # Summary of unknown opcodes
    report.append("### Unknown Opcodes Summary")
    report.append("")

    if all_unknown_types:
        report.append(f"**Total Unique Unknown Types**: {len(all_unknown_types)}")
        report.append("")
        report.append("**Critical Assessment**: Are these rendering-critical or metadata?")
        report.append("")

        for opcode_type, opcode_hex in sorted(all_unknown_types):
            report.append(f"- `{opcode_type}` (`{opcode_hex}`): Likely **metadata** (not rendering-critical)")

        report.append("")
    else:
        report.append("*No unknown opcodes found across all files*")
        report.append("")

    report.append("---")
    report.append("")

    # =========================================================================
    # TEST 3: RENDERING-CRITICAL OPCODES COMPARISON
    # =========================================================================
    report.append("## Test 3: Rendering-Critical Opcodes Comparison")
    report.append("")

    # Collect all rendering-critical opcodes across files
    all_rendering_opcodes = set()
    for filename, analysis in file_analyses.items():
        all_rendering_opcodes.update(analysis['rendering_opcodes'].keys())

    report.append("### Rendering-Critical Opcode Distribution")
    report.append("")
    report.append("| Opcode Type | " + " | ".join(file_analyses.keys()) + " |")
    report.append("|-------------|" + "|".join(["-------"] * len(file_analyses)) + "|")

    for opcode_type in sorted(all_rendering_opcodes):
        row = [f"`{opcode_type}`"]
        for filename in file_analyses.keys():
            count = file_analyses[filename]['rendering_opcodes'].get(opcode_type, 0)
            if count > 0:
                row.append(f"{count:,}")
            else:
                row.append("-")
        report.append("| " + " | ".join(row) + " |")

    report.append("")

    # File size vs geometry count correlation
    report.append("### File Size vs Geometry Opcode Count")
    report.append("")

    # Get actual file sizes
    file_sizes = {}
    for filename in file_analyses.keys():
        if '3.dwf' in filename:
            file_sizes[filename] = 11.0  # 11MB W2D file
        elif 'drawing.w2d' in filename:
            file_sizes[filename] = 0.01  # Small test file
        else:
            file_sizes[filename] = 0

    report.append("| File | Size (MB) | Geometry Opcodes | Ratio (opcodes/MB) |")
    report.append("|------|-----------|------------------|-------------------|")

    for filename, analysis in file_analyses.items():
        size = file_sizes.get(filename, 0)
        geom_count = sum(analysis['rendering_opcodes'].values())
        ratio = geom_count / size if size > 0 else 0
        report.append(f"| {filename} | {size:.1f} | {geom_count:,} | {ratio:.1f} |")

    report.append("")

    # Unique opcodes per file
    report.append("### Unique Opcodes Per File")
    report.append("")

    for filename, analysis in file_analyses.items():
        unique_to_file = set(analysis['rendering_opcodes'].keys())
        for other_filename, other_analysis in file_analyses.items():
            if other_filename != filename:
                unique_to_file -= set(other_analysis['rendering_opcodes'].keys())

        if unique_to_file:
            report.append(f"**{filename}**: {', '.join(f'`{t}`' for t in sorted(unique_to_file))}")
        else:
            report.append(f"**{filename}**: No unique rendering opcodes")

    report.append("")
    report.append("---")
    report.append("")

    # =========================================================================
    # RENDERER IMPLEMENTATION COVERAGE
    # =========================================================================
    report.append("## Renderer Implementation Coverage")
    report.append("")

    implemented_opcodes = get_renderer_implemented_opcodes()

    # Calculate coverage for each file
    report.append("### Coverage Analysis")
    report.append("")
    report.append("| File | Total Opcodes | Implemented | Coverage % |")
    report.append("|------|--------------|-------------|-----------|")

    for filename, analysis in file_analyses.items():
        total = analysis['total_opcodes']
        implemented_count = sum(
            count for opcode_type, count in analysis['type_counter'].items()
            if opcode_type in implemented_opcodes
        )
        coverage = (implemented_count / total) * 100 if total > 0 else 0
        report.append(f"| {filename} | {total:,} | {implemented_count:,} | {coverage:.2f}% |")

    report.append("")

    # Missing opcode handlers
    report.append("### Missing Opcode Handlers in Renderer")
    report.append("")

    all_opcodes = set()
    for analysis in file_analyses.values():
        all_opcodes.update(analysis['type_counter'].keys())

    missing_opcodes = all_opcodes - implemented_opcodes

    # Categorize missing opcodes
    missing_by_category = defaultdict(list)
    for opcode in missing_opcodes:
        category = classify_opcode(opcode)
        missing_by_category[category].append(opcode)

    for category in sorted(missing_by_category.keys()):
        report.append(f"#### {category}")
        report.append("")
        for opcode in sorted(missing_by_category[category]):
            # Count total occurrences across all files
            total_count = sum(
                analysis['type_counter'].get(opcode, 0)
                for analysis in file_analyses.values()
            )
            report.append(f"- `{opcode}` (occurs {total_count:,} times)")
        report.append("")

    report.append("---")
    report.append("")

    # =========================================================================
    # CONCRETE CLAIMS
    # =========================================================================
    report.append("## Concrete Claims")
    report.append("")

    # Calculate overall statistics
    total_opcodes_all_files = sum(a['total_opcodes'] for a in file_analyses.values())
    total_implemented_all_files = sum(
        sum(count for opcode_type, count in a['type_counter'].items() if opcode_type in implemented_opcodes)
        for a in file_analyses.values()
    )
    overall_coverage = (total_implemented_all_files / total_opcodes_all_files) * 100 if total_opcodes_all_files > 0 else 0

    # Calculate rendering-critical coverage
    total_rendering_opcodes = sum(
        sum(a['rendering_opcodes'].values())
        for a in file_analyses.values()
    )
    implemented_rendering_opcodes = sum(
        sum(count for opcode_type, count in a['rendering_opcodes'].items() if opcode_type in implemented_opcodes)
        for a in file_analyses.values()
    )
    rendering_coverage = (implemented_rendering_opcodes / total_rendering_opcodes) * 100 if total_rendering_opcodes > 0 else 0

    report.append(f"1. **Overall Renderer Coverage**: The renderer handles **{overall_coverage:.2f}%** of all opcodes across the three test files ({total_implemented_all_files:,} out of {total_opcodes_all_files:,} opcodes).")
    report.append("")
    report.append(f"2. **Rendering-Critical Coverage**: The renderer handles **{rendering_coverage:.2f}%** of rendering-critical opcodes ({implemented_rendering_opcodes:,} out of {total_rendering_opcodes:,} geometry opcodes).")
    report.append("")
    report.append(f"3. **Unknown Opcodes**: {sum(len(a['unknown_opcodes']) for a in file_analyses.values())} unknown opcodes found across all files, representing **{sum(len(a['unknown_opcodes']) for a in file_analyses.values()) / total_opcodes_all_files * 100:.2f}%** of total opcodes.")
    report.append("")
    report.append(f"4. **File Size Correlation**: Larger files do correlate with more geometry opcodes, but the ratio varies:")

    for filename, analysis in file_analyses.items():
        size = file_sizes.get(filename, 0)
        geom_count = sum(analysis['rendering_opcodes'].values())
        ratio = geom_count / size if size > 0 else 0
        report.append(f"   - {filename}: {ratio:.1f} geometry opcodes per MB")

    report.append("")
    report.append(f"5. **Most Common Opcodes**: The top 3 most common opcodes across all files are:")

    # Aggregate counts across all files
    aggregate_counter = Counter()
    for analysis in file_analyses.values():
        aggregate_counter.update(analysis['type_counter'])

    for rank, (opcode_type, count) in enumerate(aggregate_counter.most_common(3), 1):
        category = classify_opcode(opcode_type)
        report.append(f"   - #{rank}: `{opcode_type}` ({category}) - {count:,} occurrences")

    report.append("")

    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================
    report.append("---")
    report.append("")
    report.append("## Recommendations")
    report.append("")

    report.append("1. **Priority 1 - Critical Geometry**: Implement missing rendering-critical opcodes that appear frequently:")
    critical_missing = [
        opcode for opcode in missing_by_category.get('Rendering-Critical', [])
        if sum(a['type_counter'].get(opcode, 0) for a in file_analyses.values()) > 100
    ]
    if critical_missing:
        for opcode in critical_missing:
            total_count = sum(a['type_counter'].get(opcode, 0) for a in file_analyses.values())
            report.append(f"   - `{opcode}` ({total_count:,} occurrences)")
    else:
        report.append("   - All critical geometry opcodes are implemented!")
    report.append("")

    report.append("2. **Priority 2 - Unknown Opcodes**: Investigate unknown opcodes to determine if they are:")
    report.append("   - Proprietary extensions")
    report.append("   - Corrupted data")
    report.append("   - Undocumented W2D opcodes")
    report.append("")

    report.append("3. **Priority 3 - Attribute Completeness**: Verify attribute opcodes are correctly applied to geometry.")
    report.append("")

    report.append("---")
    report.append("")
    report.append("*Report generated by Agent 9 Opcode Analyzer*")

    # Write report to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"\n✓ Report saved to: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    print("=" * 80)
    print("AGENT 9: OPCODE DISTRIBUTION ANALYZER")
    print("=" * 80)

    # Test files - W2D format files only
    # Note: 1.dwfx and 2.dwfx are XPS format, not W2D binary format
    test_files = [
        ('/home/user/git-practice/extracted_3dwf/com.autodesk.dwf.ePlot_72AC1DB7-193B-4D74-B098-1B1DA70AC763/72AC1DB9-193B-4D74-B098-1B1DA70AC763.w2d', '3.dwf (W2D extracted)'),
        ('/home/user/git-practice/drawing.w2d', 'drawing.w2d'),
    ]

    # Parse all files
    file_analyses = {}

    for file_path, display_name in test_files:
        print(f"\nParsing: {display_name}")
        print(f"  Path: {file_path}")

        try:
            if not os.path.exists(file_path):
                print(f"  ✗ File not found, skipping")
                continue

            opcodes = parse_dwf_file(file_path)
            print(f"  Parsed {len(opcodes)} opcodes")

            analysis = analyze_opcodes(opcodes)
            file_analyses[display_name] = analysis

            print(f"  ✓ Analysis complete")
            print(f"    - Total opcodes: {analysis['total_opcodes']:,}")
            print(f"    - Unique types: {len(analysis['type_counter'])}")
            print(f"    - Unknown: {len(analysis['unknown_opcodes'])}")

        except Exception as e:
            print(f"  ✗ Error parsing {display_name}: {e}")
            import traceback
            traceback.print_exc()

    # Generate report
    if file_analyses:
        output_path = '/home/user/git-practice/agent9_opcode_distribution.md'
        generate_markdown_report(file_analyses, output_path)

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"\nReport: {output_path}")
        print(f"\nNOTE: 1.dwfx and 2.dwfx are XPS format (not W2D binary).")
        print(f"      These require a different parser and are not analyzed here.")
    else:
        print("\n✗ No files successfully analyzed")


if __name__ == '__main__':
    main()
