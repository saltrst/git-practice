#!/usr/bin/env python3
"""
DWF to PDF Converter - Test Script

Converts 3.dwf to output.pdf using A1 parser + B1 renderer.
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf

def main():
    # Use the extracted W2D file
    input_file = "drawing.w2d"
    output_file = "output.pdf"

    print(f"Converting {input_file} to {output_file}...")
    print(f"Input size: {Path(input_file).stat().st_size / (1024*1024):.2f} MB")

    try:
        # Step 1: Parse DWF file
        print("\n[1/2] Parsing DWF file...")
        opcodes = parse_dwf_file(input_file)
        print(f"✓ Parsed {len(opcodes)} opcodes")

        # Debug: Show first 10 opcodes
        print("\nFirst 10 opcodes:")
        for i, op in enumerate(opcodes[:10]):
            opcode_type = op.get('type', 'NO TYPE')
            print(f"  {i+1}. Type: {opcode_type} | Keys: {list(op.keys())[:8]}")
            if opcode_type in ['unknown_extended_ascii', 'NO TYPE', 'error']:
                print(f"       Details: {dict(list(op.items())[:6])}")

        # Count opcode types
        from collections import Counter
        type_counts = Counter(op.get('type', 'NO TYPE') for op in opcodes)
        print(f"\nOpcode type distribution (top 10):")
        for opcode_type, count in type_counts.most_common(10):
            print(f"  {opcode_type}: {count}")

        # Show example of polytriangle_16r
        print("\nExample polytriangle_16r opcode:")
        for op in opcodes:
            if op.get('type') == 'polytriangle_16r':
                import json
                print(json.dumps(op, indent=2, default=str)[:500])
                break

        # Step 2: Render to PDF
        print("\n[2/2] Rendering to PDF...")
        render_dwf_to_pdf(opcodes, output_file, pagesize=(11*72, 8.5*72))
        print(f"✓ Created {output_file}")
        print(f"Output size: {Path(output_file).stat().st_size / (1024*1024):.2f} MB")

        print("\n✅ Conversion complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
