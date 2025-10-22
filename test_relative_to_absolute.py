#!/usr/bin/env python3
"""
Agent 7 - Test 2: Relative-to-Absolute Coordinate Conversion Test

Tests the normalize_and_absolute_coords function from convert_final.py
to verify correct handling of relative coordinate opcodes and set_origin.
"""

import sys
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))

from convert_final import normalize_and_absolute_coords


def test_relative_to_absolute():
    """Test relative-to-absolute coordinate conversion logic."""

    print("=" * 70)
    print("AGENT 7 - TEST 2: Relative-to-Absolute Coordinate Conversion")
    print("=" * 70)

    # Test Case 1: Simple relative polyline from origin
    print("\n" + "=" * 70)
    print("TEST CASE 1: Relative polyline from origin (0,0)")
    print("=" * 70)

    test1_opcodes = [
        {
            'type': 'polyline_polygon',
            'relative': True,
            'points': [
                [100, 50],   # Delta: +100, +50 → Absolute: (100, 50)
                [50, 100],   # Delta: +50, +100 → Absolute: (150, 150)
                [-50, 50],   # Delta: -50, +50 → Absolute: (100, 200)
            ]
        }
    ]

    result1 = normalize_and_absolute_coords(test1_opcodes)

    print("\nInput (relative):")
    print(f"  Points: {test1_opcodes[0]['points']}")

    print("\nExpected (absolute):")
    expected1 = [[100, 50], [150, 150], [100, 200]]
    print(f"  Points: {expected1}")

    print("\nActual (absolute):")
    actual1 = result1[0]['points']
    print(f"  Points: {actual1}")

    match1 = actual1 == expected1
    print(f"\nResult: {'✓ PASS' if match1 else '✗ FAIL'}")

    # Test Case 2: set_origin followed by relative polyline
    print("\n" + "=" * 70)
    print("TEST CASE 2: set_origin followed by relative polyline")
    print("=" * 70)

    test2_opcodes = [
        {
            'type': 'set_origin',
            'origin': [500, 300]
        },
        {
            'type': 'polyline_polygon',
            'relative': True,
            'points': [
                [100, 0],    # Delta: +100, 0 → Absolute: (600, 300)
                [0, 100],    # Delta: 0, +100 → Absolute: (600, 400)
                [-100, 0],   # Delta: -100, 0 → Absolute: (500, 400)
            ]
        }
    ]

    result2 = normalize_and_absolute_coords(test2_opcodes)

    print("\nInput:")
    print(f"  set_origin: {test2_opcodes[0]['origin']}")
    print(f"  Relative points: {test2_opcodes[1]['points']}")

    print("\nExpected (absolute):")
    expected2 = [[600, 300], [600, 400], [500, 400]]
    print(f"  Points: {expected2}")

    print("\nActual (absolute):")
    actual2 = result2[1]['points']
    print(f"  Points: {actual2}")

    match2 = actual2 == expected2
    print(f"\nResult: {'✓ PASS' if match2 else '✗ FAIL'}")

    # Test Case 3: Multiple relative polylines (chaining)
    print("\n" + "=" * 70)
    print("TEST CASE 3: Multiple relative polylines (chaining)")
    print("=" * 70)

    test3_opcodes = [
        {
            'type': 'polyline_polygon',
            'relative': True,
            'points': [[100, 100]]  # (0,0) → (100, 100)
        },
        {
            'type': 'polyline_polygon',
            'relative': True,
            'points': [[50, 50]]    # (100,100) → (150, 150)
        },
        {
            'type': 'polyline_polygon',
            'relative': True,
            'points': [[-50, 100]]  # (150,150) → (100, 250)
        }
    ]

    result3 = normalize_and_absolute_coords(test3_opcodes)

    print("\nInput (3 relative polylines):")
    print(f"  Polyline 1 relative: {test3_opcodes[0]['points']}")
    print(f"  Polyline 2 relative: {test3_opcodes[1]['points']}")
    print(f"  Polyline 3 relative: {test3_opcodes[2]['points']}")

    print("\nExpected (absolute):")
    print(f"  Polyline 1: [[100, 100]]")
    print(f"  Polyline 2: [[150, 150]]")
    print(f"  Polyline 3: [[100, 250]]")

    print("\nActual (absolute):")
    actual3_1 = result3[0]['points']
    actual3_2 = result3[1]['points']
    actual3_3 = result3[2]['points']
    print(f"  Polyline 1: {actual3_1}")
    print(f"  Polyline 2: {actual3_2}")
    print(f"  Polyline 3: {actual3_3}")

    match3 = (actual3_1 == [[100, 100]] and
              actual3_2 == [[150, 150]] and
              actual3_3 == [[100, 250]])
    print(f"\nResult: {'✓ PASS' if match3 else '✗ FAIL'}")

    # Test Case 4: Relative line (point1, point2)
    print("\n" + "=" * 70)
    print("TEST CASE 4: Relative line with point1/point2")
    print("=" * 70)

    test4_opcodes = [
        {
            'type': 'set_origin',
            'origin': [200, 200]
        },
        {
            'type': 'line',
            'relative': True,
            'point1': [50, 0],   # From origin → (250, 200)
            'point2': [0, 100]   # From point1 → (250, 300)
        }
    ]

    result4 = normalize_and_absolute_coords(test4_opcodes)

    print("\nInput:")
    print(f"  set_origin: {test4_opcodes[0]['origin']}")
    print(f"  Relative point1: {test4_opcodes[1]['point1']}")
    print(f"  Relative point2: {test4_opcodes[1]['point2']}")

    print("\nExpected (absolute):")
    expected4_p1 = [250, 200]
    expected4_p2 = [250, 300]
    print(f"  point1: {expected4_p1}")
    print(f"  point2: {expected4_p2}")

    print("\nActual (absolute):")
    actual4_p1 = result4[1]['point1']
    actual4_p2 = result4[1]['point2']
    print(f"  point1: {actual4_p1}")
    print(f"  point2: {actual4_p2}")

    match4 = (actual4_p1 == expected4_p1 and actual4_p2 == expected4_p2)
    print(f"\nResult: {'✓ PASS' if match4 else '✗ FAIL'}")

    # Test Case 5: Field normalization (points→vertices, point1→start, point2→end)
    print("\n" + "=" * 70)
    print("TEST CASE 5: Field name normalization")
    print("=" * 70)

    test5_opcodes = [
        {
            'type': 'polyline_polygon',
            'relative': False,
            'points': [[100, 100], [200, 200]]
        },
        {
            'type': 'line',
            'relative': False,
            'point1': [50, 50],
            'point2': [150, 150]
        }
    ]

    result5 = normalize_and_absolute_coords(test5_opcodes)

    print("\nChecking field normalization:")
    has_vertices = 'vertices' in result5[0]
    has_start = 'start' in result5[1]
    has_end = 'end' in result5[1]

    print(f"  Polyline has 'vertices' field: {has_vertices}")
    print(f"  Line has 'start' field: {has_start}")
    print(f"  Line has 'end' field: {has_end}")

    if has_vertices:
        print(f"  vertices value: {result5[0]['vertices']}")
    if has_start:
        print(f"  start value: {result5[1]['start']}")
    if has_end:
        print(f"  end value: {result5[1]['end']}")

    match5 = has_vertices and has_start and has_end
    print(f"\nResult: {'✓ PASS' if match5 else '✗ FAIL'}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_tests = [match1, match2, match3, match4, match5]
    passed = sum(all_tests)
    total = len(all_tests)

    print(f"Total tests:  {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {total - passed}")

    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()
    print("The normalize_and_absolute_coords function:")
    print()
    print("1. RELATIVE COORDINATE HANDLING:")
    print("   - Maintains current_origin state (starts at [0,0])")
    print("   - For relative opcodes, accumulates deltas from current_origin")
    print("   - Updates current_origin to last point for chaining")
    print()
    print("2. SET_ORIGIN HANDLING:")
    print("   - set_origin opcode updates the current_origin reference point")
    print("   - Subsequent relative coordinates are based on this new origin")
    print()
    print("3. FIELD NORMALIZATION:")
    print("   - Converts 'points' → 'vertices' for renderer compatibility")
    print("   - Converts 'point1' → 'start' and 'point2' → 'end'")
    print()
    print("4. COORDINATE ACCUMULATION:")
    print("   - Relative coordinates are deltas, not absolute positions")
    print("   - Each delta is added to previous position")
    print("   - This creates a path that chains together")
    print()

    if passed == total:
        print("✓ ALL TESTS PASSED - Relative-to-absolute conversion working correctly")
    else:
        print(f"✗ {total - passed} TESTS FAILED - Issues found in conversion logic")

    print("=" * 70)

    return passed == total


if __name__ == '__main__':
    success = test_relative_to_absolute()
    sys.exit(0 if success else 1)
