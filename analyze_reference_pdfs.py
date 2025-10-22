#!/usr/bin/env python3
"""
Agent 10: Reference PDF Content Analysis
Analyzes reference PDFs to understand expected output
"""

import PyPDF2
import sys
import re
from pathlib import Path

def extract_text(pdf_path):
    """Extract all text from PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text.append(f"Page {page_num + 1}:\n{page_text}\n")
            return "\n".join(text) if text else "No text extracted"
    except Exception as e:
        return f"Error extracting text: {e}"

def analyze_pdf_structure(pdf_path):
    """Analyze PDF structure and complexity"""
    results = {}

    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)

            results['num_pages'] = len(reader.pages)
            results['pdf_version'] = reader.pdf_header if hasattr(reader, 'pdf_header') else 'Unknown'

            # Get metadata
            if reader.metadata:
                results['metadata'] = {
                    'author': reader.metadata.get('/Author', 'N/A'),
                    'creator': reader.metadata.get('/Creator', 'N/A'),
                    'producer': reader.metadata.get('/Producer', 'N/A'),
                    'title': reader.metadata.get('/Title', 'N/A'),
                }
            else:
                results['metadata'] = {}

            # Analyze first page in detail
            if len(reader.pages) > 0:
                page = reader.pages[0]

                # Get page dimensions
                if '/MediaBox' in page:
                    media_box = page['/MediaBox']
                    results['page_size'] = {
                        'width': float(media_box[2]) - float(media_box[0]),
                        'height': float(media_box[3]) - float(media_box[1]),
                        'units': 'points (1/72 inch)'
                    }

                # Try to get content stream info
                if '/Contents' in page:
                    contents = page['/Contents']
                    if hasattr(contents, 'get_object'):
                        content_obj = contents.get_object()
                        if hasattr(content_obj, 'get_data'):
                            content_data = content_obj.get_data()
                            results['content_stream_size'] = len(content_data)

                            # Analyze drawing operations
                            results['drawing_operations'] = analyze_drawing_operations(content_data)

                # Count resources
                if '/Resources' in page:
                    resources = page['/Resources']
                    if hasattr(resources, 'get_object'):
                        resources = resources.get_object()

                    results['resources'] = {}
                    if '/Font' in resources:
                        results['resources']['fonts'] = len(resources['/Font'])
                    if '/XObject' in resources:
                        results['resources']['xobjects'] = len(resources['/XObject'])
                    if '/ColorSpace' in resources:
                        results['resources']['colorspaces'] = len(resources['/ColorSpace'])
                    if '/Pattern' in resources:
                        results['resources']['patterns'] = len(resources['/Pattern'])
                    if '/ExtGState' in resources:
                        results['resources']['graphics_states'] = len(resources['/ExtGState'])

    except Exception as e:
        results['error'] = str(e)

    return results

def analyze_drawing_operations(content_data):
    """Analyze PDF content stream for drawing operations"""
    try:
        content_str = content_data.decode('latin-1', errors='ignore')
    except:
        return {'error': 'Could not decode content stream'}

    operations = {
        # Path construction
        'm': content_str.count(' m\n') + content_str.count(' m '),  # moveto
        'l': content_str.count(' l\n') + content_str.count(' l '),  # lineto
        'c': content_str.count(' c\n') + content_str.count(' c '),  # curve
        're': content_str.count(' re\n') + content_str.count(' re '),  # rectangle

        # Path painting
        'S': content_str.count(' S\n') + content_str.count(' S '),  # stroke
        's': content_str.count(' s\n') + content_str.count(' s '),  # close and stroke
        'f': content_str.count(' f\n') + content_str.count(' f '),  # fill
        'F': content_str.count(' F\n') + content_str.count(' F '),  # fill (alt)
        'B': content_str.count(' B\n') + content_str.count(' B '),  # fill and stroke

        # Graphics state
        'w': content_str.count(' w\n') + content_str.count(' w '),  # line width
        'RG': content_str.count(' RG\n') + content_str.count(' RG '),  # stroke color RGB
        'rg': content_str.count(' rg\n') + content_str.count(' rg '),  # fill color RGB
        'q': content_str.count(' q\n') + content_str.count(' q '),  # save state
        'Q': content_str.count(' Q\n') + content_str.count(' Q '),  # restore state
        'cm': content_str.count(' cm\n') + content_str.count(' cm '),  # transform matrix

        # Text operations
        'Tj': content_str.count(' Tj\n') + content_str.count(' Tj '),  # show text
        'TJ': content_str.count(' TJ\n') + content_str.count(' TJ '),  # show text array
        'Td': content_str.count(' Td\n') + content_str.count(' Td '),  # text position
    }

    # Calculate totals
    operations['total_path_ops'] = operations['m'] + operations['l'] + operations['c'] + operations['re']
    operations['total_paint_ops'] = operations['S'] + operations['s'] + operations['f'] + operations['F'] + operations['B']
    operations['total_color_ops'] = operations['RG'] + operations['rg']
    operations['total_text_ops'] = operations['Tj'] + operations['TJ'] + operations['Td']

    return operations

def estimate_content_type(analysis):
    """Estimate what type of content is in the PDF"""
    content_type = []

    if 'drawing_operations' in analysis:
        ops = analysis['drawing_operations']

        # High path/line operations suggest technical drawing
        if ops.get('total_path_ops', 0) > 1000:
            content_type.append('Technical Drawing (High complexity)')
        elif ops.get('total_path_ops', 0) > 100:
            content_type.append('Technical Drawing (Medium complexity)')
        elif ops.get('total_path_ops', 0) > 10:
            content_type.append('Simple Diagram')

        # Text operations
        if ops.get('total_text_ops', 0) > 100:
            content_type.append('Contains significant text')
        elif ops.get('total_text_ops', 0) > 0:
            content_type.append('Contains some text')
        else:
            content_type.append('Minimal or no text')

        # Fill vs stroke ratio
        total_fills = ops.get('f', 0) + ops.get('F', 0) + ops.get('B', 0)
        total_strokes = ops.get('S', 0) + ops.get('s', 0) + ops.get('B', 0)

        if total_fills > total_strokes * 2:
            content_type.append('Predominantly filled shapes')
        elif total_strokes > total_fills * 2:
            content_type.append('Predominantly line drawings')
        else:
            content_type.append('Mix of fills and strokes')

    return content_type if content_type else ['Unknown']

def analyze_file(pdf_path):
    """Complete analysis of a PDF file"""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {pdf_path}")
    print(f"{'='*80}\n")

    # File size
    size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
    print(f"File Size: {size_mb:.2f} MB\n")

    # Structure analysis
    print("PDF STRUCTURE:")
    print("-" * 80)
    structure = analyze_pdf_structure(pdf_path)

    for key, value in structure.items():
        if key == 'drawing_operations':
            print(f"\n{key}:")
            for op_key, op_value in value.items():
                if op_value > 0:  # Only show non-zero operations
                    print(f"  {op_key}: {op_value}")
        elif key == 'page_size':
            print(f"\n{key}:")
            for size_key, size_value in value.items():
                print(f"  {size_key}: {size_value}")
        elif key == 'resources':
            print(f"\n{key}:")
            for res_key, res_value in value.items():
                print(f"  {res_key}: {res_value}")
        elif key == 'metadata':
            if value:
                print(f"\n{key}:")
                for meta_key, meta_value in value.items():
                    print(f"  {meta_key}: {meta_value}")
        else:
            print(f"{key}: {value}")

    # Content type estimation
    print(f"\nCONTENT TYPE ESTIMATION:")
    print("-" * 80)
    content_types = estimate_content_type(structure)
    for ct in content_types:
        print(f"  - {ct}")

    # Text extraction
    print(f"\nTEXT EXTRACTION:")
    print("-" * 80)
    text = extract_text(pdf_path)
    if text and text != "No text extracted":
        # Show first 500 chars
        print(text[:500])
        if len(text) > 500:
            print(f"\n... [Total text length: {len(text)} characters]")
    else:
        print(text)

    return {
        'file_size_mb': size_mb,
        'structure': structure,
        'content_types': content_types,
        'text_length': len(text)
    }

def main():
    pdf_files = [
        '/home/user/git-practice/1.pdf',
        '/home/user/git-practice/2.pdf',
        '/home/user/git-practice/3.pdf'
    ]

    all_results = {}

    for pdf_file in pdf_files:
        if Path(pdf_file).exists():
            all_results[pdf_file] = analyze_file(pdf_file)
        else:
            print(f"WARNING: {pdf_file} not found!")

    # Summary comparison
    print(f"\n\n{'='*80}")
    print("SUMMARY COMPARISON")
    print(f"{'='*80}\n")

    for pdf_file, results in all_results.items():
        print(f"{Path(pdf_file).name}:")
        print(f"  Size: {results['file_size_mb']:.2f} MB")
        print(f"  Pages: {results['structure'].get('num_pages', 'N/A')}")

        if 'drawing_operations' in results['structure']:
            ops = results['structure']['drawing_operations']
            print(f"  Total Path Operations: {ops.get('total_path_ops', 0)}")
            print(f"  Total Paint Operations: {ops.get('total_paint_ops', 0)}")
            print(f"  Total Color Operations: {ops.get('total_color_ops', 0)}")
            print(f"  Total Text Operations: {ops.get('total_text_ops', 0)}")

        print(f"  Content Type: {', '.join(results['content_types'])}")
        print()

if __name__ == '__main__':
    main()
