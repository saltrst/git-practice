#!/usr/bin/env python3
"""
Agent 8: Extract and Analyze DWF/DWFX Files

DWFX files are ZIP archives containing W2D streams.
This script extracts the W2D data and performs proper bounding box analysis.
"""

import sys
from pathlib import Path
from collections import Counter
import zipfile
import tempfile
import shutil

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root / "integration"))

from dwf_parser_v1 import parse_dwf_file


def extract_w2d_from_dwfx(dwfx_path, output_dir):
    """
    Extract W2D files from a DWFX/DWF ZIP archive.

    Args:
        dwfx_path: Path to DWFX/DWF file
        output_dir: Directory to extract W2D files to

    Returns:
        List of extracted W2D file paths
    """
    print(f"\nExtracting W2D files from {dwfx_path.name}...")

    w2d_files = []

    try:
        with zipfile.ZipFile(dwfx_path, 'r') as zf:
            # List all files
            all_files = zf.namelist()
            print(f"  Found {len(all_files)} files in archive")

            # Find W2D files
            for filename in all_files:
                if filename.lower().endswith('.w2d') or filename.lower().endswith('.dwf'):
                    print(f"  📄 Found W2D stream: {filename}")

                    # Extract to output directory
                    extract_path = output_dir / f"{dwfx_path.stem}_{Path(filename).name}"
                    with zf.open(filename) as source:
                        with open(extract_path, 'wb') as target:
                            target.write(source.read())

                    w2d_files.append(extract_path)
                    print(f"     → Extracted to: {extract_path.name}")

            if not w2d_files:
                print("  ⚠️  No W2D files found, trying to extract all files...")
                # Extract everything and look for files with drawing data
                for filename in all_files:
                    if not filename.endswith('/'):
                        extract_path = output_dir / f"{dwfx_path.stem}_{Path(filename).name.replace('/', '_')}"
                        with zf.open(filename) as source:
                            content = source.read()
                            # Check if it looks like a W2D file (starts with specific bytes)
                            if content.startswith(b'(DWF V') or content.startswith(b'(W2D V'):
                                print(f"  📄 Found potential W2D: {filename}")
                                with open(extract_path, 'wb') as target:
                                    target.write(content)
                                w2d_files.append(extract_path)

        if w2d_files:
            print(f"  ✓ Extracted {len(w2d_files)} W2D file(s)")
        else:
            print(f"  ✗ No W2D files found in archive")

    except zipfile.BadZipFile:
        print(f"  ✗ Not a valid ZIP archive")

        # Check if it's a raw W2D file
        with open(dwfx_path, 'rb') as f:
            header = f.read(20)
            if header.startswith(b'(DWF V') or header.startswith(b'(W2D V'):
                print(f"  → This appears to be a raw W2D/DWF file")
                # Copy to output directory
                extract_path = output_dir / dwfx_path.name
                shutil.copy(dwfx_path, extract_path)
                w2d_files.append(extract_path)
                print(f"  ✓ Copied to: {extract_path.name}")

    except Exception as e:
        print(f"  ✗ Error extracting: {e}")

    return w2d_files


def analyze_w2d_geometry(w2d_path):
    """
    Analyze geometry in a W2D file and calculate bounding box.

    Returns:
        dict with bounding box and statistics
    """
    print(f"\n  Parsing {w2d_path.name}...")

    try:
        opcodes = parse_dwf_file(str(w2d_path))
        print(f"  ✓ Parsed {len(opcodes)} opcodes")
    except Exception as e:
        print(f"  ✗ Error parsing: {e}")
        return None

    # Count opcodes by type
    type_counter = Counter()
    geometry_count = 0
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    point_count = 0

    geometry_types = [
        'line', 'line_16r', 'circle', 'circle_16r', 'ellipse', 'draw_ellipse',
        'polyline_polygon', 'polyline_polygon_16r', 'polytriangle',
        'polytriangle_16r', 'polytriangle_32r', 'quad', 'quad_32r',
        'bezier', 'contour', 'gouraud_polytriangle', 'gouraud_polyline'
    ]

    # Track origin for relative coordinates
    current_origin = [0, 0]

    for op in opcodes:
        opcode_type = op.get('type', 'NO_TYPE')
        type_counter[opcode_type] += 1

        # Update origin tracking
        if opcode_type == 'set_origin':
            origin = op.get('origin', [0, 0])
            current_origin = list(origin)

        # Extract geometry coordinates
        if opcode_type not in geometry_types:
            continue

        geometry_count += 1

        # Process relative coordinates
        is_relative = op.get('relative', False)

        # Lines
        if opcode_type in ['line', 'line_16r']:
            start = op.get('start', op.get('point1', None))
            end = op.get('end', op.get('point2', None))

            if start and end:
                if is_relative:
                    # Convert to absolute
                    abs_start = [current_origin[0] + start[0], current_origin[1] + start[1]]
                    abs_end = [abs_start[0] + end[0], abs_start[1] + end[1]]
                    current_origin = abs_end.copy()
                    start, end = abs_start, abs_end

                min_x = min(min_x, start[0], end[0])
                max_x = max(max_x, start[0], end[0])
                min_y = min(min_y, start[1], end[1])
                max_y = max(max_y, start[1], end[1])
                point_count += 2

        # Circles
        elif opcode_type in ['circle', 'circle_16r']:
            center = op.get('center', None)
            radius = op.get('radius', 0)

            if center:
                if is_relative:
                    center = [current_origin[0] + center[0], current_origin[1] + center[1]]
                    current_origin = center.copy()

                min_x = min(min_x, center[0] - radius)
                max_x = max(max_x, center[0] + radius)
                min_y = min(min_y, center[1] - radius)
                max_y = max(max_y, center[1] + radius)
                point_count += 1

        # Polygons/polylines/triangles
        elif opcode_type in ['polyline_polygon', 'polyline_polygon_16r', 'polytriangle',
                            'polytriangle_16r', 'polytriangle_32r', 'quad', 'quad_32r']:
            vertices = op.get('vertices', op.get('points', []))

            if is_relative and vertices:
                # Convert relative points to absolute
                abs_vertices = []
                current_pos = current_origin.copy()
                for delta in vertices:
                    current_pos[0] += delta[0]
                    current_pos[1] += delta[1]
                    abs_vertices.append(current_pos.copy())
                vertices = abs_vertices
                if abs_vertices:
                    current_origin = abs_vertices[-1].copy()

            for v in vertices:
                if len(v) >= 2:
                    min_x = min(min_x, v[0])
                    max_x = max(max_x, v[0])
                    min_y = min(min_y, v[1])
                    max_y = max(max_y, v[1])
                    point_count += 1

    # Calculate bounding box
    if point_count > 0:
        bbox = {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'width': max_x - min_x,
            'height': max_y - min_y,
            'aspect_ratio': (max_x - min_x) / (max_y - min_y) if (max_y - min_y) != 0 else 0,
            'point_count': point_count,
            'geometry_count': geometry_count
        }

        print(f"  ✓ Bounding box: [{min_x:.0f}, {max_x:.0f}] × [{min_y:.0f}, {max_y:.0f}]")
        print(f"    Size: {bbox['width']:.0f} × {bbox['height']:.0f} DWF units")
        print(f"    Aspect ratio: {bbox['aspect_ratio']:.4f}")
        print(f"    Geometry: {geometry_count} objects, {point_count} points")
    else:
        print(f"  ✗ No geometry found")
        bbox = None

    # Show opcode distribution
    print(f"\n  Top opcodes:")
    for opcode_type, count in type_counter.most_common(10):
        is_geo = "📐" if opcode_type in geometry_types else "  "
        print(f"  {is_geo} {opcode_type:30s} : {count}")

    return {
        'w2d_file': w2d_path.name,
        'total_opcodes': len(opcodes),
        'geometry_count': geometry_count,
        'bbox': bbox,
        'type_distribution': type_counter
    }


def main():
    """Main extraction and analysis entry point."""
    print("="*70)
    print("AGENT 8: EXTRACT AND ANALYZE DWF/DWFX FILES")
    print("="*70)

    base_dir = Path(__file__).parent

    # Test files
    test_files = [
        base_dir / "1.dwfx",
        base_dir / "2.dwfx",
        base_dir / "3.dwf",
    ]

    # Create temporary extraction directory
    extract_dir = base_dir / "dwf_extracted"
    extract_dir.mkdir(exist_ok=True)
    print(f"\nExtraction directory: {extract_dir}")

    all_results = {}

    # Extract and analyze each file
    for dwfx_path in test_files:
        if not dwfx_path.exists():
            print(f"\n✗ File not found: {dwfx_path}")
            continue

        print(f"\n{'='*70}")
        print(f"Processing: {dwfx_path.name}")
        print(f"{'='*70}")

        # Extract W2D files
        w2d_files = extract_w2d_from_dwfx(dwfx_path, extract_dir)

        if not w2d_files:
            print(f"✗ No W2D files extracted from {dwfx_path.name}")
            continue

        # Analyze each W2D file
        file_results = []
        for w2d_path in w2d_files:
            result = analyze_w2d_geometry(w2d_path)
            if result:
                file_results.append(result)

        all_results[dwfx_path.name] = {
            'source_file': dwfx_path.name,
            'w2d_files': w2d_files,
            'results': file_results
        }

    # Summary
    print(f"\n{'='*70}")
    print("EXTRACTION AND ANALYSIS SUMMARY")
    print("="*70)

    for source_name, data in all_results.items():
        print(f"\n{source_name}:")
        print(f"  Extracted: {len(data['w2d_files'])} W2D file(s)")

        total_geometry = 0
        for result in data['results']:
            total_geometry += result.get('geometry_count', 0)
            if result.get('bbox'):
                bbox = result['bbox']
                print(f"  └─ {result['w2d_file']}: {bbox['geometry_count']} geometry objects")
                print(f"     BBox: {bbox['width']:.0f} × {bbox['height']:.0f} (AR: {bbox['aspect_ratio']:.4f})")

        if total_geometry == 0:
            print(f"  ⚠️  No geometry found")

    print(f"\n✓ Extracted files saved to: {extract_dir}")


if __name__ == "__main__":
    main()
