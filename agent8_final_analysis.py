#!/usr/bin/env python3
"""
Agent 8: Final Comprehensive Bounding Box Analysis

Analyzes all three test files using the appropriate extraction method:
- 1.dwfx, 2.dwfx: Extract from XPS FixedPage.fpage files
- 3.dwf: Extract from W2D streams

Compares with reference PDFs and generates final report.
"""

import sys
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import re

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root / "integration"))

from dwf_parser_v1 import parse_dwf_file


def extract_pdf_page_size(pdf_path):
    """Extract page size from PDF."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            page = reader.pages[0]
            box = page.mediabox
            width = float(box.width)
            height = float(box.height)
            return {
                'width': width,
                'height': height,
                'aspect_ratio': width / height if height != 0 else 0,
                'page_count': len(reader.pages)
            }
    except Exception as e:
        print(f"  Warning: Could not extract PDF size: {e}")
    return None


def analyze_xps_fixedpage(dwfx_path):
    """
    Extract bounding box from XPS FixedPage files in DWFX.

    Returns geometry bounding box and page sizes.
    """
    print(f"\n{'='*70}")
    print(f"Analyzing XPS content in: {dwfx_path.name}")
    print(f"{'='*70}")

    pages = []
    all_coords = []

    try:
        with zipfile.ZipFile(dwfx_path, 'r') as zf:
            # Find all FixedPage.fpage files
            fpage_files = [f for f in zf.namelist() if f.endswith('FixedPage.fpage')]
            print(f"Found {len(fpage_files)} FixedPage files")

            for fpage_file in fpage_files:
                print(f"\n  Analyzing: {Path(fpage_file).name}")

                # Read and parse XML
                content = zf.read(fpage_file).decode('utf-8')

                # Extract FixedPage dimensions using regex (faster than full XML parse)
                page_match = re.search(r'<FixedPage[^>]*Height="([0-9.]+)"[^>]*Width="([0-9.]+)"', content)
                if page_match:
                    height = float(page_match.group(1))
                    width = float(page_match.group(2))
                    pages.append({
                        'width': width,
                        'height': height,
                        'aspect_ratio': width / height if height != 0 else 0
                    })
                    print(f"    Page size: {width:.2f} × {height:.2f} points")

                # Extract all coordinates from Path Data attributes
                # Pattern: M x,y L x,y h number v number
                path_coords = re.findall(r'[MLHVmv]\s*(-?[0-9.]+)[,\s]+(-?[0-9.]+)', content)
                coords_h = re.findall(r'[Hh]\s*(-?[0-9.]+)', content)
                coords_v = re.findall(r'[Vv]\s*(-?[0-9.]+)', content)

                # Add XY coordinates
                for x, y in path_coords:
                    all_coords.append((float(x), float(y)))

                # Add horizontal/vertical coordinates (would need current position, approximate)
                for x in coords_h:
                    if all_coords:
                        all_coords.append((float(x), all_coords[-1][1]))

                for y in coords_v:
                    if all_coords:
                        all_coords.append((all_coords[-1][0], float(y)))

        # Calculate bounding box from all coordinates
        if all_coords:
            min_x = min(x for x, y in all_coords)
            max_x = max(x for x, y in all_coords)
            min_y = min(y for x, y in all_coords)
            max_y = max(y for x, y in all_coords)

            bbox = {
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y,
                'width': max_x - min_x,
                'height': max_y - min_y,
                'aspect_ratio': (max_x - min_x) / (max_y - min_y) if (max_y - min_y) != 0 else 0,
                'point_count': len(all_coords)
            }

            print(f"\n  ✓ Geometry bounding box:")
            print(f"    X: [{min_x:.2f}, {max_x:.2f}] = {bbox['width']:.2f} units")
            print(f"    Y: [{min_y:.2f}, {max_y:.2f}] = {bbox['height']:.2f} units")
            print(f"    Aspect ratio: {bbox['aspect_ratio']:.4f}")
            print(f"    Points extracted: {len(all_coords)}")
        else:
            bbox = None
            print(f"\n  ✗ No geometry coordinates found")

        # Average page size
        if pages:
            avg_width = sum(p['width'] for p in pages) / len(pages)
            avg_height = sum(p['height'] for p in pages) / len(pages)
            page_info = {
                'width': avg_width,
                'height': avg_height,
                'aspect_ratio': avg_width / avg_height if avg_height != 0 else 0,
                'page_count': len(pages)
            }
            print(f"\n  ✓ Average page size: {avg_width:.2f} × {avg_height:.2f} points")
        else:
            page_info = None

        return {
            'type': 'XPS',
            'bbox': bbox,
            'page_info': page_info,
            'pages': pages
        }

    except Exception as e:
        print(f"  ✗ Error analyzing XPS: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_w2d_dwf(dwf_path):
    """Analyze W2D stream from DWF file."""
    print(f"\n{'='*70}")
    print(f"Analyzing W2D stream in: {dwf_path.name}")
    print(f"{'='*70}")

    try:
        # Extract W2D file from ZIP
        with zipfile.ZipFile(dwf_path, 'r') as zf:
            w2d_files = [f for f in zf.namelist() if f.lower().endswith('.w2d')]

            if not w2d_files:
                print("  ✗ No W2D files found")
                return None

            print(f"  Found W2D file: {w2d_files[0]}")

            # Extract and parse
            w2d_data = zf.read(w2d_files[0])

            # Write to temp file for parsing
            temp_path = Path("/tmp/temp_w2d.w2d")
            temp_path.write_bytes(w2d_data)

            # Parse W2D
            opcodes = parse_dwf_file(str(temp_path))
            print(f"  ✓ Parsed {len(opcodes)} opcodes")

            # Calculate bounding box
            min_x = float('inf')
            max_x = float('-inf')
            min_y = float('inf')
            max_y = float('-inf')
            point_count = 0
            geometry_count = 0
            current_origin = [0, 0]

            for op in opcodes:
                opcode_type = op.get('type', '')

                # Update origin
                if opcode_type == 'set_origin':
                    origin = op.get('origin', [0, 0])
                    current_origin = list(origin)

                is_relative = op.get('relative', False)

                # Process geometry
                if opcode_type in ['polytriangle_16r', 'polyline_polygon_16r', 'line_16r']:
                    geometry_count += 1

                    # Get vertices/points
                    vertices = op.get('vertices', op.get('points', []))

                    if is_relative and vertices:
                        # Convert relative to absolute
                        abs_vertices = []
                        current_pos = current_origin.copy()
                        for delta in vertices:
                            if len(delta) >= 2:
                                current_pos[0] += delta[0]
                                current_pos[1] += delta[1]
                                abs_vertices.append(current_pos.copy())
                        vertices = abs_vertices
                        if abs_vertices:
                            current_origin = abs_vertices[-1].copy()

                    # Update bounding box
                    for v in vertices:
                        if len(v) >= 2:
                            # Handle signed 16-bit wraparound
                            x, y = v[0], v[1]

                            # If coordinates look like they wrapped around (near 2^31)
                            if x > 2000000000:  # Close to INT32_MAX
                                x = x - 2**32
                            if y > 2000000000:
                                y = y - 2**32

                            min_x = min(min_x, x)
                            max_x = max(max_x, x)
                            min_y = min(min_y, y)
                            max_y = max(max_y, y)
                            point_count += 1

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

                print(f"\n  ✓ Geometry bounding box:")
                print(f"    X: [{min_x:.2f}, {max_x:.2f}] = {bbox['width']:.2f} DWF units")
                print(f"    Y: [{min_y:.2f}, {max_y:.2f}] = {bbox['height']:.2f} DWF units")
                print(f"    Aspect ratio: {bbox['aspect_ratio']:.4f}")
                print(f"    Geometry: {geometry_count} objects, {point_count} points")
            else:
                bbox = None
                print(f"\n  ✗ No geometry found")

            return {
                'type': 'W2D',
                'bbox': bbox,
                'opcode_count': len(opcodes)
            }

    except Exception as e:
        print(f"  ✗ Error analyzing W2D: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_final_report(results, output_path):
    """Generate comprehensive final report."""
    lines = [
        "# Agent 8: Bounding Box Analysis Report",
        "",
        "**Mission:** Calculate and compare expected vs actual bounding boxes for all test files.",
        "",
        "## Executive Summary",
        "",
        "This analysis examines bounding boxes from parsed DWF/DWFX geometry and compares them to reference PDF page sizes.",
        "",
        "### Key Findings",
        ""
    ]

    # Determine overall conclusion
    all_match = all(r.get('aspect_match') == True for r in results if r)
    close_match = any(r.get('aspect_match') == 'close' for r in results if r)

    if all_match:
        lines.append("✓ **All aspect ratios MATCH** - Geometry and PDF proportions are consistent")
    elif close_match:
        lines.append("⚠ **Aspect ratios are CLOSE** - Minor discrepancies detected")
    else:
        lines.append("✗ **Aspect ratios DON'T MATCH** - Significant geometry/PDF proportion differences")

    lines.extend([
        "",
        "## Test Files Analyzed",
        "",
        "| File | Type | Size | Reference PDF | Size |",
        "|------|------|------|---------------|------|"
    ])

    for r in results:
        if r:
            lines.append(
                f"| {r['dwf_name']} | {r['format_type']} | {r['dwf_size_mb']:.1f} MB | "
                f"{r['pdf_name']} | {r['pdf_size_mb']:.1f} MB |"
            )

    lines.extend([
        "",
        "**Format Types:**",
        "- **DWFX**: XPS (XML Paper Specification) format - ZIP archive containing XML with SVG-like paths",
        "- **DWF**: W2D binary stream format - ZIP archive containing compressed W2D opcodes",
        ""
    ])

    # Test 1: Bounding Boxes
    lines.extend([
        "## Test 1: Calculated Bounding Boxes from Geometry",
        "",
        "Extracted all geometry coordinates and calculated min/max X/Y ranges.",
        "",
        "| File | Min X | Max X | Min Y | Max Y | Width | Height | Aspect Ratio | Points |",
        "|------|-------|-------|-------|-------|-------|--------|--------------|--------|"
    ])

    for r in results:
        if r and r.get('bbox'):
            bbox = r['bbox']
            lines.append(
                f"| {r['dwf_name']} | {bbox['min_x']:.2f} | {bbox['max_x']:.2f} | "
                f"{bbox['min_y']:.2f} | {bbox['max_y']:.2f} | "
                f"{bbox['width']:.2f} | {bbox['height']:.2f} | "
                f"{bbox['aspect_ratio']:.4f} | {bbox.get('point_count', '?')} |"
            )

    lines.append("")

    # Test 2: PDF Page Sizes
    lines.extend([
        "## Test 2: Reference PDF Page Sizes",
        "",
        "Extracted MediaBox dimensions from reference PDFs.",
        "",
        "| PDF File | Width (pts) | Height (pts) | Width (in) | Height (in) | Aspect Ratio | Pages |",
        "|----------|-------------|--------------|------------|-------------|--------------|-------|"
    ])

    for r in results:
        if r and r.get('pdf_info'):
            pdf = r['pdf_info']
            w_in = pdf['width'] / 72
            h_in = pdf['height'] / 72
            lines.append(
                f"| {r['pdf_name']} | {pdf['width']:.2f} | {pdf['height']:.2f} | "
                f"{w_in:.2f} | {h_in:.2f} | {pdf['aspect_ratio']:.4f} | {pdf['page_count']} |"
            )

    lines.append("")

    # Test 3: Aspect Ratio Comparison
    lines.extend([
        "## Test 3: Aspect Ratio Comparison",
        "",
        "Comparing (geometry_width / geometry_height) vs (pdf_width / pdf_height)",
        "",
        "| File | Geometry AR | PDF AR | Difference | % Diff | Match? |",
        "|------|-------------|--------|------------|--------|--------|"
    ])

    for r in results:
        if r and r.get('bbox') and r.get('pdf_info'):
            geo_ar = r['bbox']['aspect_ratio']
            pdf_ar = r['pdf_info']['aspect_ratio']
            diff = abs(geo_ar - pdf_ar)
            pct = (diff / pdf_ar * 100) if pdf_ar != 0 else 0

            if r.get('aspect_match') == True:
                match = "✓ Yes"
            elif r.get('aspect_match') == 'close':
                match = "⚠ Close"
            else:
                match = "✗ No"

            lines.append(
                f"| {r['dwf_name']} | {geo_ar:.4f} | {pdf_ar:.4f} | "
                f"{diff:.4f} | {pct:.2f}% | {match} |"
            )

    lines.append("")

    # Analysis section
    lines.extend([
        "## Analysis and Findings",
        "",
        "### Concrete Claim: Aspect Ratios"
    ])

    if all_match:
        lines.extend([
            "",
            "**CLAIM: Aspect ratios MATCH between parsed geometry and reference PDFs.**",
            "",
            "**Evidence:**",
            "- All files show aspect ratio differences < 1%",
            "- Geometry proportions are preserved in PDF conversion",
            "- No significant stretching or squashing detected",
            "",
            "**Conclusion:** The reference PDFs maintain correct drawing proportions. "
            "Uniform scaling can be applied for conversion."
        ])
    else:
        lines.extend([
            "",
            "**CLAIM: Aspect ratios DON'T MATCH perfectly between geometry and PDFs.**",
            "",
            "**Evidence:**"
        ])

        for r in results:
            if r and r.get('bbox') and r.get('pdf_info'):
                geo_ar = r['bbox']['aspect_ratio']
                pdf_ar = r['pdf_info']['aspect_ratio']
                pct = abs(geo_ar - pdf_ar) / pdf_ar * 100 if pdf_ar != 0 else 0
                lines.append(f"- {r['dwf_name']}: {pct:.1f}% difference (Geometry: {geo_ar:.4f}, PDF: {pdf_ar:.4f})")

        lines.extend([
            "",
            "**Possible Causes:**",
            "1. PDF page sizes don't match content aspect ratio",
            "2. Content has margins/padding in PDF",
            "3. Non-uniform scaling applied during conversion",
            "4. Viewport/clipping applied to geometry",
            "",
            "**Conclusion:** Geometry bounding box should be used as authoritative size. "
            "Apply uniform scaling to maintain proportions."
        ])

    # Per-file details
    lines.extend([
        "",
        "## Per-File Detailed Analysis",
        ""
    ])

    for r in results:
        if not r:
            continue

        lines.extend([
            f"### {r['dwf_name']}",
            "",
            f"**Format:** {r['format_type']}  ",
            f"**Size:** {r['dwf_size_mb']:.1f} MB → {r['pdf_size_mb']:.1f} MB PDF",
            ""
        ])

        if r.get('bbox'):
            bbox = r['bbox']
            lines.extend([
                "**Geometry Bounding Box:**",
                f"- Dimensions: {bbox['width']:.2f} × {bbox['height']:.2f} units",
                f"- Range: X=[{bbox['min_x']:.0f}, {bbox['max_x']:.0f}], Y=[{bbox['min_y']:.0f}, {bbox['max_y']:.0f}]",
                f"- Aspect ratio: {bbox['aspect_ratio']:.4f}",
                f"- Data points: {bbox.get('point_count', '?')}",
                ""
            ])

        if r.get('pdf_info'):
            pdf = r['pdf_info']
            lines.extend([
                "**PDF Page Size:**",
                f"- Dimensions: {pdf['width']:.2f} × {pdf['height']:.2f} points ({pdf['width']/72:.2f} × {pdf['height']/72:.2f} inches)",
                f"- Aspect ratio: {pdf['aspect_ratio']:.4f}",
                f"- Pages: {pdf['page_count']}",
                ""
            ])

        if r.get('bbox') and r.get('pdf_info'):
            bbox = r['bbox']
            pdf = r['pdf_info']
            scale_x = pdf['width'] / bbox['width'] if bbox['width'] != 0 else 0
            scale_y = pdf['height'] / bbox['height'] if bbox['height'] != 0 else 0
            uniform_scale = min(scale_x, scale_y)

            lines.extend([
                "**Scale Analysis:**",
                f"- Scale X: {scale_x:.6f}",
                f"- Scale Y: {scale_y:.6f}",
                f"- Recommended uniform scale: {uniform_scale:.6f}",
                f"- Aspect match: {r.get('aspect_match', '?')}",
                ""
            ])

    # Recommendations
    lines.extend([
        "## Recommendations",
        "",
        "### Page Sizing Strategy",
        ""
    ])

    if all_match:
        lines.extend([
            "Since aspect ratios match, use **uniform scaling** with automatic page sizing:",
            "",
            "```python",
            "# Calculate scale to fit content with margins",
            "MARGIN = 72  # 1 inch",
            "scale_x = (page_width - 2*MARGIN) / bbox_width",
            "scale_y = (page_height - 2*MARGIN) / bbox_height",
            "scale = min(scale_x, scale_y)  # Uniform scaling",
            "",
            "# Or auto-size page to content:",
            "page_width = bbox_width * scale + 2*MARGIN",
            "page_height = bbox_height * scale + 2*MARGIN",
            "```"
        ])
    else:
        lines.extend([
            "Since aspect ratios don't match perfectly:",
            "",
            "1. **Use geometry bounding box as authoritative**",
            "2. **Apply uniform scaling** (min of X/Y scale factors)",
            "3. **Center content on page with margins**",
            "4. **Consider adding viewport/clip region support**",
            "",
            "```python",
            "# Recommended approach",
            "bbox_aspect = bbox_width / bbox_height",
            "page_aspect = page_width / page_height",
            "",
            "if bbox_aspect > page_aspect:",
            "    # Wider than page, fit to width",
            "    scale = page_width / bbox_width",
            "else:",
            "    # Taller than page, fit to height",
            "    scale = page_height / bbox_height",
            "```"
        ])

    # Methodology
    lines.extend([
        "",
        "## Methodology",
        "",
        "### Coordinate Extraction",
        "",
        "**DWFX Files (XPS Format):**",
        "- Extracted from FixedPage.fpage XML files",
        "- Parsed SVG-style Path Data attributes",
        "- Coordinates already in absolute format (points)",
        "",
        "**DWF Files (W2D Format):**",
        "- Extracted W2D streams from ZIP archive",
        "- Parsed binary opcodes (lines, polylines, triangles)",
        "- Converted relative coordinates to absolute",
        "- Tracked origin state throughout parsing",
        "",
        "**Bounding Box Calculation:**",
        "- Accumulated all geometry coordinates",
        "- Calculated min/max for X and Y",
        "- BBox = [min_x, max_x] × [min_y, max_y]",
        "- Aspect ratio = width / height",
        "",
        "### PDF Analysis",
        "",
        "- Used PyPDF2 to extract MediaBox",
        "- Measured in points (1 pt = 1/72 inch)",
        "- First page dimensions used for comparison",
        "",
        "---",
        "",
        f"*Analysis by {Path(__file__).name}*"
    ])

    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"\n✓ Final report written to: {output_path}")


def main():
    """Main analysis entry point."""
    print("="*70)
    print("AGENT 8: FINAL COMPREHENSIVE BOUNDING BOX ANALYSIS")
    print("="*70)

    base_dir = Path(__file__).parent

    # Test files
    test_cases = [
        {
            'dwf': base_dir / "1.dwfx",
            'pdf': base_dir / "1.pdf",
            'format': 'DWFX'
        },
        {
            'dwf': base_dir / "2.dwfx",
            'pdf': base_dir / "2.pdf",
            'format': 'DWFX'
        },
        {
            'dwf': base_dir / "3.dwf",
            'pdf': base_dir / "3.pdf",
            'format': 'DWF'
        }
    ]

    results = []

    for case in test_cases:
        dwf_path = case['dwf']
        pdf_path = case['pdf']

        if not dwf_path.exists() or not pdf_path.exists():
            print(f"\n✗ Missing file: {dwf_path} or {pdf_path}")
            continue

        print(f"\n{'='*70}")
        print(f"Analyzing: {dwf_path.name} → {pdf_path.name}")
        print(f"{'='*70}")

        # Analyze DWF/DWFX
        if case['format'] == 'DWFX':
            dwf_result = analyze_xps_fixedpage(dwf_path)
        else:
            dwf_result = analyze_w2d_dwf(dwf_path)

        # Analyze PDF
        print(f"\nExtracting PDF page size from {pdf_path.name}...")
        pdf_info = extract_pdf_page_size(str(pdf_path))
        if pdf_info:
            print(f"  ✓ PDF: {pdf_info['width']:.2f} × {pdf_info['height']:.2f} pts (AR: {pdf_info['aspect_ratio']:.4f})")

        # Compare aspect ratios
        aspect_match = None
        if dwf_result and dwf_result.get('bbox') and pdf_info:
            geo_ar = dwf_result['bbox']['aspect_ratio']
            pdf_ar = pdf_info['aspect_ratio']
            diff_pct = abs(geo_ar - pdf_ar) / pdf_ar * 100 if pdf_ar != 0 else 0

            if diff_pct < 1:
                aspect_match = True
                print(f"\n  ✓ Aspect ratios MATCH ({diff_pct:.2f}% difference)")
            elif diff_pct < 5:
                aspect_match = 'close'
                print(f"\n  ⚠ Aspect ratios CLOSE ({diff_pct:.2f}% difference)")
            else:
                aspect_match = False
                print(f"\n  ✗ Aspect ratios DON'T MATCH ({diff_pct:.2f}% difference)")

        # Compile results
        result = {
            'dwf_name': dwf_path.name,
            'pdf_name': pdf_path.name,
            'format_type': case['format'],
            'dwf_size_mb': dwf_path.stat().st_size / (1024*1024),
            'pdf_size_mb': pdf_path.stat().st_size / (1024*1024),
            'bbox': dwf_result.get('bbox') if dwf_result else None,
            'pdf_info': pdf_info,
            'aspect_match': aspect_match
        }
        results.append(result)

    # Generate final report
    output_path = base_dir / "agent8_bounding_box_analysis.md"
    print(f"\n{'='*70}")
    print("Generating Final Report")
    print(f"{'='*70}")

    generate_final_report(results, output_path)

    # Summary
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nFinal Report: {output_path}\n")

    for r in results:
        if r['aspect_match'] == True:
            print(f"  ✓ {r['dwf_name']}: Aspect ratios MATCH")
        elif r['aspect_match'] == 'close':
            print(f"  ⚠ {r['dwf_name']}: Aspect ratios CLOSE")
        elif r['aspect_match'] == False:
            print(f"  ✗ {r['dwf_name']}: Aspect ratios DON'T MATCH")
        else:
            print(f"  ? {r['dwf_name']}: Analysis incomplete")

    print()


if __name__ == "__main__":
    main()
