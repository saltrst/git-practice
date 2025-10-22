#!/usr/bin/env python3
"""
Agent 7 - Test 1: Unit Test for transform_point Function

Tests the transform_point function from pdf_renderer_v1.py
with various coordinate inputs and scale factors.
"""

import sys
from pathlib import Path

# Add project path
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.pdf_renderer_v1 import transform_point


def test_transform_point():
    """Unit test for transform_point function."""

    print("=" * 70)
    print("AGENT 7 - TEST 1: transform_point() Unit Tests")
    print("=" * 70)

    # Test parameters
    page_height = 792  # Standard letter size in points (11 inches * 72 pts/inch)

    # Define test cases: (x, y, scale, expected_x, expected_y)
    test_cases = [
        # Test Case 1: Origin with different scales
        {
            'name': 'Origin (0,0) with scale 0.01',
            'x': 0, 'y': 0, 'scale': 0.01,
            'expected_x': 0.0, 'expected_y': 0.0
        },
        {
            'name': 'Origin (0,0) with scale 0.1',
            'x': 0, 'y': 0, 'scale': 0.1,
            'expected_x': 0.0, 'expected_y': 0.0
        },
        {
            'name': 'Origin (0,0) with scale 1.0',
            'x': 0, 'y': 0, 'scale': 1.0,
            'expected_x': 0.0, 'expected_y': 0.0
        },

        # Test Case 2: Point (1000, 1000) with different scales
        {
            'name': 'Point (1000, 1000) with scale 0.01',
            'x': 1000, 'y': 1000, 'scale': 0.01,
            'expected_x': 10.0, 'expected_y': 10.0
        },
        {
            'name': 'Point (1000, 1000) with scale 0.1',
            'x': 1000, 'y': 1000, 'scale': 0.1,
            'expected_x': 100.0, 'expected_y': 100.0
        },
        {
            'name': 'Point (1000, 1000) with scale 1.0',
            'x': 1000, 'y': 1000, 'scale': 1.0,
            'expected_x': 1000.0, 'expected_y': 1000.0
        },

        # Test Case 3: Large coordinates (2147296545, 26558) with different scales
        {
            'name': 'Point (2147296545, 26558) with scale 0.01',
            'x': 2147296545, 'y': 26558, 'scale': 0.01,
            'expected_x': 21472965.45, 'expected_y': 265.58
        },
        {
            'name': 'Point (2147296545, 26558) with scale 0.1',
            'x': 2147296545, 'y': 26558, 'scale': 0.1,
            'expected_x': 214729654.5, 'expected_y': 2655.8
        },
        {
            'name': 'Point (2147296545, 26558) with scale 1.0',
            'x': 2147296545, 'y': 26558, 'scale': 1.0,
            'expected_x': 2147296545.0, 'expected_y': 26558.0
        },

        # Test Case 4: Negative coordinates
        {
            'name': 'Point (-500, -300) with scale 0.1',
            'x': -500, 'y': -300, 'scale': 0.1,
            'expected_x': -50.0, 'expected_y': -30.0
        },

        # Test Case 5: Mixed sign coordinates
        {
            'name': 'Point (1000, -500) with scale 0.1',
            'x': 1000, 'y': -500, 'scale': 0.1,
            'expected_x': 100.0, 'expected_y': -50.0
        },
    ]

    # Run tests
    passed = 0
    failed = 0

    print(f"\nRunning {len(test_cases)} test cases...\n")

    for i, test in enumerate(test_cases, 1):
        x, y = test['x'], test['y']
        scale = test['scale']
        expected_x, expected_y = test['expected_x'], test['expected_y']

        # Call transform_point
        result_x, result_y = transform_point(x, y, page_height, scale)

        # Check results
        tolerance = 0.001  # Allow small floating point differences
        x_match = abs(result_x - expected_x) < tolerance
        y_match = abs(result_y - expected_y) < tolerance

        if x_match and y_match:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1

        print(f"Test {i}: {test['name']}")
        print(f"  Input:    ({x}, {y}) with scale={scale}")
        print(f"  Expected: ({expected_x}, {expected_y})")
        print(f"  Got:      ({result_x}, {result_y})")
        print(f"  Status:   {status}")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests:  {len(test_cases)}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failed}")
    print()

    # Analysis
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()
    print("The transform_point function implements a simple linear scaling:")
    print("  pdf_x = dwf_x * scale")
    print("  pdf_y = dwf_y * scale")
    print()
    print("Key observations:")
    print("1. No Y-axis flipping - both DWF and PDF use bottom-left origin with Y-up")
    print("2. No origin offset applied - the transform is pure scaling")
    print("3. The page_height parameter is PASSED but NOT USED in the function")
    print("4. Scale factor directly controls DWF units → PDF points conversion")
    print()
    print("Coordinate system:")
    print("  DWF: Bottom-left origin, Y-axis up")
    print("  PDF: Bottom-left origin, Y-axis up")
    print("  → No axis flipping needed, systems are aligned")
    print()

    if scale == 0.1:
        print("With scale=0.1 (default):")
        print("  1000 DWF units = 100 PDF points = 1.39 inches")
        print("  10000 DWF units = 1000 PDF points = 13.89 inches")

    print()
    print(f"Test result: {'ALL TESTS PASSED' if failed == 0 else f'{failed} TESTS FAILED'}")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = test_transform_point()
    sys.exit(0 if success else 1)
