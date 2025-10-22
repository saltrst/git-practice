#!/usr/bin/env python3
"""
Agent 8: Diagnostic - Opcode Distribution Analysis

Analyzes what opcodes are present in the test files to understand
why geometry extraction is finding so few objects.
"""

import sys
from pathlib import Path
from collections import Counter

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root / "integration"))

from dwf_parser_v1 import parse_dwf_file


def analyze_opcodes(file_path):
    """Analyze opcode distribution in a DWF file."""
    print(f"\n{'='*70}")
    print(f"Analyzing: {file_path.name}")
    print(f"{'='*70}")

    # Parse file
    print(f"Parsing...")
    opcodes = parse_dwf_file(str(file_path))
    print(f"✓ Parsed {len(opcodes)} opcodes")

    # Count by type
    type_counter = Counter()
    geometry_opcodes = []
    unknown_count = 0

    geometry_types = [
        'line', 'line_16r', 'circle', 'circle_16r', 'ellipse', 'draw_ellipse',
        'polyline_polygon', 'polyline_polygon_16r', 'polytriangle',
        'polytriangle_16r', 'polytriangle_32r', 'quad', 'quad_32r',
        'bezier', 'contour', 'gouraud_polytriangle', 'gouraud_polyline',
        'draw_text_basic', 'draw_text_complex'
    ]

    for op in opcodes:
        opcode_type = op.get('type', 'NO_TYPE')
        type_counter[opcode_type] += 1

        if opcode_type in geometry_types:
            geometry_opcodes.append(op)

        if 'unknown' in opcode_type.lower():
            unknown_count += 1

    print(f"\nOpcode Type Distribution (Top 20):")
    print("-" * 70)
    for opcode_type, count in type_counter.most_common(20):
        is_geometry = "📐" if opcode_type in geometry_types else "  "
        print(f"{is_geometry} {opcode_type:40s} : {count:5d}")

    print(f"\nSummary:")
    print(f"  Total opcodes: {len(opcodes)}")
    print(f"  Unique types: {len(type_counter)}")
    print(f"  Geometry opcodes: {len(geometry_opcodes)}")
    print(f"  Unknown opcodes: {unknown_count}")

    # Show sample geometry opcodes
    if geometry_opcodes:
        print(f"\nSample Geometry Opcodes (first 3):")
        print("-" * 70)
        for i, op in enumerate(geometry_opcodes[:3]):
            print(f"\n{i+1}. Type: {op.get('type', 'NO_TYPE')}")
            # Show all fields except raw data
            for key, value in op.items():
                if key not in ['type', 'raw_data', 'data'] and not key.startswith('_'):
                    print(f"   {key}: {value}")

    return {
        'file': file_path.name,
        'total_opcodes': len(opcodes),
        'unique_types': len(type_counter),
        'geometry_count': len(geometry_opcodes),
        'unknown_count': unknown_count,
        'type_distribution': type_counter,
        'geometry_opcodes': geometry_opcodes
    }


def main():
    """Main diagnostic entry point."""
    print("="*70)
    print("AGENT 8: OPCODE DIAGNOSTIC ANALYSIS")
    print("="*70)

    # Test files
    base_dir = Path(__file__).parent
    test_files = [
        base_dir / "1.dwfx",
        base_dir / "2.dwfx",
        base_dir / "3.dwf",
    ]

    results = []
    for file_path in test_files:
        if file_path.exists():
            result = analyze_opcodes(file_path)
            results.append(result)
        else:
            print(f"\n✗ File not found: {file_path}")

    # Overall summary
    print(f"\n{'='*70}")
    print("OVERALL SUMMARY")
    print("="*70)

    for result in results:
        geo_pct = (result['geometry_count'] / result['total_opcodes'] * 100) if result['total_opcodes'] > 0 else 0
        print(f"\n{result['file']}:")
        print(f"  Total: {result['total_opcodes']} opcodes")
        print(f"  Geometry: {result['geometry_count']} ({geo_pct:.1f}%)")
        print(f"  Unknown: {result['unknown_count']}")

    # Check if parser is working properly
    total_geo = sum(r['geometry_count'] for r in results)
    if total_geo < 10:
        print(f"\n⚠️  WARNING: Very low geometry count ({total_geo} total)")
        print("   Possible causes:")
        print("   1. Files are compressed/encrypted")
        print("   2. Parser doesn't recognize the opcode format")
        print("   3. Geometry is in Extended Binary/ASCII format")
        print("   4. Files contain mostly metadata/structure opcodes")


if __name__ == "__main__":
    main()
