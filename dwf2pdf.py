#!/usr/bin/env python3
"""
DWF to PDF Converter - Command Line Interface

Converts DWF/DWFX files to PDF format using the integrated parser and renderer.

Usage:
    python dwf2pdf.py input.dwf output.pdf
    python dwf2pdf.py input.dwfx output.pdf
    python dwf2pdf.py input.dwf                 # Creates input.pdf

Supported Formats:
    - Classic DWF (.dwf)
    - DWF 6.0+ (.dwf)
    - DWFX with W2D streams (.dwfx)

Author: DWF-to-PDF Converter Team
"""

import sys
import argparse
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert DWF/DWFX files to PDF format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s drawing.dwf output.pdf
  %(prog)s design.dwfx design.pdf
  %(prog)s file.dwf                    # Creates file.pdf

Supported Formats:
  ✓ Classic DWF (.dwf) - Pre-6.0 format
  ✓ DWF 6.0+ (.dwf) - ZIP with W2D streams
  ✓ DWFX (.dwfx) - With W2D streams
  ✗ DWFX (.dwfx) - XPS-only (no W2D)

For XPS-only DWFX files, use Autodesk DWG TrueView to convert to DWF format.
        """
    )

    parser.add_argument(
        'input',
        help='Input DWF or DWFX file path'
    )

    parser.add_argument(
        'output',
        nargs='?',
        help='Output PDF file path (optional, defaults to input name with .pdf extension)'
    )

    parser.add_argument(
        '--page-size',
        choices=['letter', 'a4', 'tabloid', 'a3', 'auto'],
        default='auto',
        help='PDF page size (default: auto - fits content)'
    )

    parser.add_argument(
        '--scale',
        type=float,
        help='Custom scale factor (overrides auto-scaling)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed processing information'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='DWF to PDF Converter 1.0.0'
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.pdf')

    # Check if output already exists
    if output_path.exists():
        response = input(f"⚠️  Output file {output_path} already exists. Overwrite? [y/N] ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            return 0

    # Convert
    try:
        if args.verbose:
            print(f"📄 Input:  {input_path} ({input_path.stat().st_size / (1024*1024):.2f} MB)")
            print(f"📄 Output: {output_path}")
            print(f"⚙️  Page size: {args.page_size}")
            if args.scale:
                print(f"⚙️  Scale: {args.scale}")
            print()

        # Parse DWF/DWFX file
        if args.verbose:
            print("🔍 Parsing DWF/DWFX file...")

        opcodes = parse_dwf_file(str(input_path))

        if args.verbose:
            print(f"✓ Parsed {len(opcodes)} opcodes")

            # Show opcode distribution
            from collections import Counter
            type_counts = Counter(op.get('type', 'NO TYPE') for op in opcodes)
            print(f"  Top opcode types:")
            for opcode_type, count in type_counts.most_common(3):
                print(f"    {opcode_type}: {count}")
            print()

        # Determine page size
        page_sizes = {
            'letter': (8.5 * 72, 11 * 72),
            'a4': (595, 842),
            'tabloid': (11 * 72, 17 * 72),
            'a3': (842, 1191),
            'auto': None  # Will be calculated
        }

        pagesize = page_sizes.get(args.page_size)

        # Calculate auto page size if needed
        if args.page_size == 'auto':
            # Calculate bounding box from opcodes
            all_coords = []
            for op in opcodes:
                if 'vertices' in op:
                    all_coords.extend(op['vertices'])
                elif 'points' in op:
                    all_coords.extend(op['points'])
                elif 'start' in op and 'end' in op:
                    all_coords.extend([op['start'], op['end']])
                elif 'point1' in op and 'point2' in op:
                    all_coords.extend([op['point1'], op['point2']])

            if all_coords:
                min_x = min(c[0] for c in all_coords)
                max_x = max(c[0] for c in all_coords)
                min_y = min(c[1] for c in all_coords)
                max_y = max(c[1] for c in all_coords)

                # Use scale to determine page size
                if args.scale:
                    width = (max_x - min_x) * args.scale
                    height = (max_y - min_y) * args.scale
                else:
                    # Default scale for auto
                    width = (max_x - min_x) * 0.1
                    height = (max_y - min_y) * 0.1

                pagesize = (width + 72, height + 72)  # Add 1 inch margins

                if args.verbose:
                    print(f"🔧 Auto page size: {width/72:.2f}\" × {height/72:.2f}\"")
            else:
                pagesize = page_sizes['letter']
                if args.verbose:
                    print("⚠️  No coordinates found, using letter size")

        # Render to PDF
        if args.verbose:
            print("🎨 Rendering PDF...")

        scale = args.scale if args.scale else 0.1
        success = render_dwf_to_pdf(opcodes, str(output_path), pagesize=pagesize, scale=scale)

        if success:
            output_size = output_path.stat().st_size / (1024*1024)
            print(f"✅ Success! Created {output_path} ({output_size:.2f} MB)")
            return 0
        else:
            print(f"❌ Error: Failed to render PDF", file=sys.stderr)
            return 1

    except NotImplementedError as e:
        print(f"❌ Unsupported format:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
