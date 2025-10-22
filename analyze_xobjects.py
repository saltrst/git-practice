#!/usr/bin/env python3
"""
Agent 10: Deep XObject Analysis
Analyzes XObjects within PDFs to extract actual drawing operations
"""

import PyPDF2
from pathlib import Path

def analyze_xobjects(pdf_path):
    """Analyze XObjects in detail"""
    print(f"\n{'='*80}")
    print(f"DEEP XOBJECT ANALYSIS: {pdf_path}")
    print(f"{'='*80}\n")

    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)

            for page_num, page in enumerate(reader.pages):
                print(f"Page {page_num + 1}:")
                print("-" * 80)

                if '/Resources' in page:
                    resources = page['/Resources']
                    if hasattr(resources, 'get_object'):
                        resources = resources.get_object()

                    if '/XObject' in resources:
                        xobjects = resources['/XObject']
                        if hasattr(xobjects, 'get_object'):
                            xobjects = xobjects.get_object()

                        print(f"Found {len(xobjects)} XObjects\n")

                        total_ops = {
                            'm': 0, 'l': 0, 'c': 0, 're': 0,
                            'S': 0, 's': 0, 'f': 0, 'F': 0, 'B': 0,
                            'w': 0, 'RG': 0, 'rg': 0, 'q': 0, 'Q': 0, 'cm': 0
                        }

                        for xobj_name in xobjects:
                            xobj = xobjects[xobj_name]
                            if hasattr(xobj, 'get_object'):
                                xobj = xobj.get_object()

                            print(f"  XObject: {xobj_name}")

                            # Check subtype
                            if '/Subtype' in xobj:
                                subtype = xobj['/Subtype']
                                print(f"    Subtype: {subtype}")

                            # Get dimensions if available
                            if '/BBox' in xobj:
                                bbox = xobj['/BBox']
                                print(f"    BBox: {bbox}")

                            # Try to extract stream data
                            if hasattr(xobj, 'get_data'):
                                try:
                                    data = xobj.get_data()
                                    print(f"    Stream size: {len(data)} bytes")

                                    # Analyze operations
                                    ops = analyze_operations(data)
                                    
                                    # Show significant operations
                                    if ops['m'] > 0:
                                        print(f"      moveto (m): {ops['m']}")
                                        total_ops['m'] += ops['m']
                                    if ops['l'] > 0:
                                        print(f"      lineto (l): {ops['l']}")
                                        total_ops['l'] += ops['l']
                                    if ops['c'] > 0:
                                        print(f"      curveto (c): {ops['c']}")
                                        total_ops['c'] += ops['c']
                                    if ops['re'] > 0:
                                        print(f"      rectangle (re): {ops['re']}")
                                        total_ops['re'] += ops['re']
                                    if ops['S'] > 0:
                                        print(f"      stroke (S): {ops['S']}")
                                        total_ops['S'] += ops['S']
                                    if ops['f'] > 0:
                                        print(f"      fill (f): {ops['f']}")
                                        total_ops['f'] += ops['f']
                                    if ops['RG'] > 0:
                                        print(f"      stroke color (RG): {ops['RG']}")
                                        total_ops['RG'] += ops['RG']
                                    if ops['w'] > 0:
                                        print(f"      line width (w): {ops['w']}")
                                        total_ops['w'] += ops['w']

                                except Exception as e:
                                    print(f"    Error extracting data: {e}")

                            print()

                        # Page totals
                        print(f"\nPage {page_num + 1} TOTALS:")
                        total_path_ops = total_ops['m'] + total_ops['l'] + total_ops['c'] + total_ops['re']
                        total_paint_ops = total_ops['S'] + total_ops['s'] + total_ops['f'] + total_ops['F'] + total_ops['B']
                        print(f"  Total path operations: {total_path_ops}")
                        print(f"  Total paint operations: {total_paint_ops}")
                        print(f"  Total color operations: {total_ops['RG'] + total_ops['rg']}")
                        print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def analyze_operations(data):
    """Count PDF operations in data stream"""
    try:
        content_str = data.decode('latin-1', errors='ignore')
    except:
        return {}

    # More comprehensive pattern matching
    operations = {
        'm': 0, 'l': 0, 'c': 0, 're': 0,
        'S': 0, 's': 0, 'f': 0, 'F': 0, 'B': 0,
        'w': 0, 'RG': 0, 'rg': 0, 'q': 0, 'Q': 0, 'cm': 0
    }

    # Count operations with various delimiters
    for op in operations.keys():
        # Look for operation followed by newline, space, or end of line
        import re
        pattern = r'\s' + re.escape(op) + r'(?:\s|$)'
        operations[op] = len(re.findall(pattern, content_str))

    return operations

def main():
    pdf_files = [
        '/home/user/git-practice/1.pdf',
        '/home/user/git-practice/2.pdf',
        '/home/user/git-practice/3.pdf'
    ]

    for pdf_file in pdf_files:
        if Path(pdf_file).exists():
            analyze_xobjects(pdf_file)
        else:
            print(f"WARNING: {pdf_file} not found!")

if __name__ == '__main__':
    main()
