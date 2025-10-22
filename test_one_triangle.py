#!/usr/bin/env python3
"""
Test rendering a single triangle from actual parsed data.
"""

import sys
from pathlib import Path
import json

project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf

# Parse the file
print("Parsing drawing.w2d...")
opcodes = parse_dwf_file("drawing.w2d")

# Find first polytriangle_16r
print("\nLooking for first polytriangle_16r opcode...")
for i, op in enumerate(opcodes):
    if op.get('type') == 'polytriangle_16r':
        print(f"\nFound at index {i}:")
        print(json.dumps(op, indent=2, default=str)[:500])

        # Create test with just this one triangle (with normalized field name)
        test_op = op.copy()
        test_op['vertices'] = test_op.get('points', [])

        print(f"\nTest opcode (normalized):")
        print(json.dumps(test_op, indent=2, default=str)[:500])

        # Render just this one
        print("\nRendering single triangle to test_one_triangle.pdf...")
        render_dwf_to_pdf([test_op], "test_one_triangle.pdf", pagesize=(11*72, 8.5*72))

        size = Path("test_one_triangle.pdf").stat().st_size
        print(f"Output size: {size} bytes ({size/1024:.2f} KB)")

        break
