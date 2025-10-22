#!/usr/bin/env python3
"""
Test script to verify DWF/DWFX format detection and parsing.

Tests the new preprocessing layer added to dwf_parser_v1.py.
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file, open_dwf_or_dwfx

def test_format_detection():
    """Test format detection for all 3 test files."""
    print("=" * 70)
    print("TEST 1: Format Detection")
    print("=" * 70)

    test_files = ["3.dwf", "1.dwfx", "2.dwfx"]

    for file_path in test_files:
        if not Path(file_path).exists():
            print(f"\n❌ {file_path}: File not found (skipping)")
            continue

        try:
            streams, format_type = open_dwf_or_dwfx(file_path)
            print(f"\n✓ {file_path}:")
            print(f"  Format: {format_type}")
            print(f"  W2D streams found: {len(streams)}")

            if streams:
                total_size = sum(len(s.getvalue()) for s in streams)
                print(f"  Total W2D data: {total_size / (1024*1024):.2f} MB")
        except Exception as e:
            print(f"\n❌ {file_path}: {e}")

def test_parsing():
    """Test parsing with the classic DWF file (should work)."""
    print("\n" + "=" * 70)
    print("TEST 2: Parsing 3.dwf (Classic DWF)")
    print("=" * 70)

    if not Path("3.dwf").exists():
        print("\n❌ 3.dwf not found (skipping)")
        return

    try:
        opcodes = parse_dwf_file("3.dwf")
        print(f"\n✓ Successfully parsed 3.dwf")
        print(f"  Total opcodes: {len(opcodes)}")

        # Count by type
        from collections import Counter
        type_counts = Counter(op.get('type', 'NO TYPE') for op in opcodes)
        print(f"\n  Top 5 opcode types:")
        for opcode_type, count in type_counts.most_common(5):
            print(f"    {opcode_type}: {count}")

    except Exception as e:
        print(f"\n❌ Failed to parse 3.dwf: {e}")

def test_xps_only_dwfx():
    """Test XPS-only DWFX file (should fail gracefully)."""
    print("\n" + "=" * 70)
    print("TEST 3: Parsing 1.dwfx (XPS-only DWFX)")
    print("=" * 70)

    if not Path("1.dwfx").exists():
        print("\n❌ 1.dwfx not found (skipping)")
        return

    try:
        opcodes = parse_dwf_file("1.dwfx")
        print(f"\n❌ UNEXPECTED: 1.dwfx parsed successfully (should have failed)")
        print(f"  Opcodes: {len(opcodes)}")
    except NotImplementedError as e:
        print(f"\n✓ Correctly raised NotImplementedError:")
        print(f"  {str(e)[:200]}...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

def main():
    print("Testing DWF/DWFX Format Detection and Parsing")
    print("=" * 70)

    test_format_detection()
    test_parsing()
    test_xps_only_dwfx()

    print("\n" + "=" * 70)
    print("All tests complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
