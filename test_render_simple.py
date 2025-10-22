#!/usr/bin/env python3
"""
Simple test to verify PDF renderer works with basic geometry.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.pdf_renderer_v1 import render_dwf_to_pdf

# Create simple test opcodes - a triangle and a rectangle
test_opcodes = [
    {
        'type': 'polytriangle',
        'vertices': [[100, 100], [300, 100], [200, 300]],
        'count': 3
    },
    {
        'type': 'polygon',
        'vertices': [[400, 400], [600, 400], [600, 600], [400, 600]],
        'count': 4
    }
]

print("Testing PDF renderer with simple hardcoded geometry...")
print(f"Test opcodes: {len(test_opcodes)}")

output_file = "test_simple.pdf"
render_dwf_to_pdf(test_opcodes, output_file, pagesize=(8.5*72, 11*72))

output_size = Path(output_file).stat().st_size
print(f"Output: {output_file}")
print(f"Size: {output_size} bytes ({output_size/1024:.2f} KB)")

if output_size < 1000:
    print("❌ PDF is suspiciously small - rendering may have failed")
else:
    print("✓ PDF created with reasonable size")
