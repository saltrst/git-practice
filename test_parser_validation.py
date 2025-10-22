#!/usr/bin/env python3
"""
Parser Validation Test Script
Agent 6 - Parser Output Validation

This script validates dwf_parser_v1.py by:
1. Parsing all test files (1.dwfx, 2.dwfx, 3.dwf)
2. Collecting opcode distribution statistics
3. Exporting sample opcodes to JSON
4. Checking for parser errors and warnings
5. Validating coordinate extraction and relative flags
"""

import sys
import json
import zipfile
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any

# Add project path
project_root = Path(__file__).parent / "dwf-to-pdf-project" / "integration"
sys.path.insert(0, str(project_root.parent))

from integration.dwf_parser_v1 import parse_dwf_file, parse_dwf_stream


def extract_w2d_from_dwfx(dwfx_path: str) -> bytes:
    """Extract W2D stream from DWFX file."""
    print(f"  Extracting W2D from {Path(dwfx_path).name}...")
    with zipfile.ZipFile(dwfx_path, 'r') as zf:
        # Look for .w2d files in the archive
        w2d_files = [f for f in zf.namelist() if f.endswith('.w2d')]
        if not w2d_files:
            raise ValueError(f"No .w2d file found in {dwfx_path}")

        print(f"  Found W2D file: {w2d_files[0]}")
        return zf.read(w2d_files[0])


def parse_file_with_extraction(file_path: str) -> List[Dict[str, Any]]:
    """Parse a file, extracting W2D from DWFX if needed."""
    file_path_obj = Path(file_path)

    if file_path_obj.suffix.lower() == '.dwfx':
        # Extract W2D from DWFX
        w2d_data = extract_w2d_from_dwfx(file_path)
        from io import BytesIO
        return parse_dwf_stream(BytesIO(w2d_data))
    else:
        # Parse DWF directly
        return parse_dwf_file(file_path)


def analyze_opcode_distribution(opcodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze opcode distribution and categorize by type."""
    distribution = Counter()
    errors = []
    warnings = []
    unknown_opcodes = []
    geometry_opcodes = []

    for i, opcode in enumerate(opcodes):
        opcode_type = opcode.get('type', 'unknown')
        distribution[opcode_type] += 1

        # Collect errors
        if opcode_type == 'error':
            errors.append({
                'index': i,
                'opcode_hex': opcode.get('opcode_hex', 'N/A'),
                'error': opcode.get('error', 'Unknown error'),
                'error_type': opcode.get('error_type', 'Unknown')
            })

        # Collect unknown opcodes
        if opcode_type.startswith('unknown'):
            unknown_opcodes.append({
                'index': i,
                'type': opcode_type,
                'opcode_hex': opcode.get('opcode_hex', 'N/A'),
                'error': opcode.get('error', 'N/A')
            })

        # Collect geometry opcodes for sampling
        geometry_types = ['polytriangle', 'polyline', 'line', 'polygon', 'circle',
                         'ellipse', 'bezier', 'rectangle', 'contour']
        if any(geom in opcode_type.lower() for geom in geometry_types):
            geometry_opcodes.append({
                'index': i,
                'opcode': opcode
            })

    return {
        'distribution': dict(distribution),
        'total_opcodes': len(opcodes),
        'errors': errors,
        'warnings': warnings,
        'unknown_opcodes': unknown_opcodes,
        'geometry_opcodes': geometry_opcodes
    }


def validate_coordinates(opcode: Dict[str, Any]) -> Dict[str, Any]:
    """Validate coordinate extraction from an opcode."""
    validation = {
        'has_coordinates': False,
        'coordinate_fields': [],
        'relative_flags': {},
        'coordinate_ranges': {}
    }

    # Check for common coordinate fields
    coord_fields = ['vertices', 'points', 'start', 'end', 'center', 'corners']

    for field in coord_fields:
        if field in opcode:
            validation['has_coordinates'] = True
            validation['coordinate_fields'].append(field)

            # Extract coordinate values
            coords = opcode[field]
            if isinstance(coords, (list, tuple)):
                if coords:
                    # Flatten to get all numeric values
                    flat_coords = []
                    for item in coords:
                        if isinstance(item, (tuple, list)):
                            flat_coords.extend(item)
                        elif isinstance(item, (int, float)):
                            flat_coords.append(item)

                    if flat_coords:
                        validation['coordinate_ranges'][field] = {
                            'min': min(flat_coords),
                            'max': max(flat_coords),
                            'count': len(flat_coords)
                        }

    # Check for relative coordinate flags
    relative_fields = ['is_relative', 'relative', 'relative_coords']
    for field in relative_fields:
        if field in opcode:
            validation['relative_flags'][field] = opcode[field]

    return validation


def export_sample_opcodes(opcodes: List[Dict[str, Any]], output_file: str, max_count: int = 10):
    """Export first N opcodes to JSON file."""
    sample = opcodes[:max_count]

    # Make JSON serializable
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, bytes):
            return f"<bytes: {len(obj)} bytes>"
        else:
            return obj

    sample_serializable = make_serializable(sample)

    with open(output_file, 'w') as f:
        json.dump(sample_serializable, f, indent=2)

    print(f"  Exported {len(sample)} opcodes to {output_file}")


def run_validation_tests():
    """Run all validation tests on parser."""
    print("=" * 80)
    print("PARSER VALIDATION TEST SUITE - Agent 6")
    print("=" * 80)
    print()

    # Define test files - using W2D and DWF files that parser can handle
    # DWFX files are Microsoft OOXML and require different parsing approach
    test_files = [
        "/home/user/git-practice/3.dwf",
        "/home/user/git-practice/drawing.w2d"
    ]

    results = {}

    # TEST 1: Parse all files and collect statistics
    print("TEST 1: Parse all files and compare opcode distributions")
    print("-" * 80)

    for file_path in test_files:
        file_name = Path(file_path).name
        print(f"\nParsing {file_name}...")

        try:
            opcodes = parse_file_with_extraction(file_path)
            analysis = analyze_opcode_distribution(opcodes)

            results[file_name] = {
                'opcodes': opcodes,
                'analysis': analysis
            }

            print(f"  Total opcodes: {analysis['total_opcodes']}")
            print(f"  Unique opcode types: {len(analysis['distribution'])}")
            print(f"  Errors: {len(analysis['errors'])}")
            print(f"  Unknown opcodes: {len(analysis['unknown_opcodes'])}")
            print(f"  Geometry opcodes: {len(analysis['geometry_opcodes'])}")

        except Exception as e:
            print(f"  ERROR: Failed to parse {file_name}: {e}")
            results[file_name] = {
                'error': str(e),
                'error_type': type(e).__name__
            }

    print()
    print("=" * 80)

    # TEST 2: Validate coordinate extraction from all files
    print("\nTEST 2: Validate coordinate extraction from all parsed files")
    print("-" * 80)

    for file_name, result in results.items():
        if 'opcodes' not in result:
            continue

        opcodes = result['opcodes']
        geometry_opcodes = result['analysis']['geometry_opcodes']

        print(f"\n{file_name}:")
        print(f"  Found {len(geometry_opcodes)} geometry opcodes")

        # Find polytriangle opcodes
        print("\n  Validating first 10 polytriangle opcodes...")

        polytriangle_count = 0
        polytriangle_samples = []

        for geom in geometry_opcodes[:100]:  # Check first 100 geometry opcodes
            opcode = geom['opcode']
            if 'polytriangle' in opcode.get('type', '').lower():
                validation = validate_coordinates(opcode)
                polytriangle_samples.append({
                    'index': geom['index'],
                    'opcode': opcode,
                    'validation': validation
                })
                polytriangle_count += 1

                if polytriangle_count <= 3:  # Print first 3
                    print(f"\n    Polytriangle #{polytriangle_count} (index {geom['index']}):")
                    print(f"      Type: {opcode.get('type')}")
                    print(f"      Has coordinates: {validation['has_coordinates']}")
                    print(f"      Coordinate fields: {validation['coordinate_fields']}")
                    print(f"      Relative flags: {validation['relative_flags']}")
                    if validation['coordinate_ranges']:
                        for field, ranges in validation['coordinate_ranges'].items():
                            print(f"      {field} range: {ranges['min']} to {ranges['max']} ({ranges['count']} values)")

                if polytriangle_count >= 10:
                    break

        # Export polytriangle samples to JSON
        if polytriangle_samples:
            safe_filename = file_name.replace('.', '_')
            export_sample_opcodes(
                [s['opcode'] for s in polytriangle_samples],
                f"/home/user/git-practice/polytriangle_samples_{safe_filename}.json",
                max_count=10
            )
        else:
            print(f"    No polytriangle opcodes found in {file_name}")

    print()
    print("=" * 80)

    # TEST 3: Test parser error handling
    print("\nTEST 3: Test parser error handling")
    print("-" * 80)

    for file_name, result in results.items():
        if 'analysis' in result:
            analysis = result['analysis']
            print(f"\n{file_name}:")
            print(f"  Total errors: {len(analysis['errors'])}")
            print(f"  Unknown opcodes: {len(analysis['unknown_opcodes'])}")

            if analysis['errors']:
                print(f"\n  First 5 errors:")
                for i, error in enumerate(analysis['errors'][:5], 1):
                    print(f"    {i}. Opcode {error['opcode_hex']} at index {error['index']}")
                    print(f"       {error['error_type']}: {error['error']}")

            if analysis['unknown_opcodes']:
                print(f"\n  First 5 unknown opcodes:")
                for i, unknown in enumerate(analysis['unknown_opcodes'][:5], 1):
                    print(f"    {i}. {unknown['type']} ({unknown['opcode_hex']}) at index {unknown['index']}")

    print()
    print("=" * 80)

    # Export full distribution comparison
    print("\nExporting distribution comparison table...")
    comparison = {}

    for file_name, result in results.items():
        if 'analysis' in result:
            comparison[file_name] = result['analysis']['distribution']

    with open("/home/user/git-practice/opcode_distribution_comparison.json", 'w') as f:
        json.dump(comparison, f, indent=2, sort_keys=True)

    print("  Saved to opcode_distribution_comparison.json")

    # Export first 10 geometry opcodes from each file
    for file_name, result in results.items():
        if 'analysis' in result and result['analysis']['geometry_opcodes']:
            geom_opcodes = result['analysis']['geometry_opcodes'][:10]
            output_file = f"/home/user/git-practice/geometry_samples_{file_name.replace('.', '_')}.json"
            export_sample_opcodes(
                [g['opcode'] for g in geom_opcodes],
                output_file,
                max_count=10
            )

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

    return results


if __name__ == '__main__':
    results = run_validation_tests()

    print("\nSUMMARY:")
    print("-" * 80)
    for file_name, result in results.items():
        if 'analysis' in result:
            analysis = result['analysis']
            print(f"\n{file_name}:")
            print(f"  Total opcodes: {analysis['total_opcodes']}")
            print(f"  Geometry opcodes: {len(analysis['geometry_opcodes'])}")
            print(f"  Errors: {len(analysis['errors'])}")
            print(f"  Unknown: {len(analysis['unknown_opcodes'])}")

            # Count specific geometry types
            dist = analysis['distribution']
            print(f"\n  Key geometry opcode counts:")
            for key in sorted(dist.keys()):
                if any(geom in key.lower() for geom in ['polytriangle', 'polyline', 'line', 'polygon']):
                    print(f"    {key}: {dist[key]}")
