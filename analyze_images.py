#!/usr/bin/env python3
"""
Agent 10: Image Analysis
Analyzes image properties in reference PDFs
"""

import PyPDF2
from pathlib import Path

def analyze_images(pdf_path):
    """Analyze image properties"""
    print(f"\n{'='*80}")
    print(f"IMAGE ANALYSIS: {pdf_path}")
    print(f"{'='*80}\n")

    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)

            total_images = 0
            total_image_size = 0

            for page_num, page in enumerate(reader.pages):
                print(f"Page {page_num + 1}:")

                if '/Resources' in page:
                    resources = page['/Resources']
                    if hasattr(resources, 'get_object'):
                        resources = resources.get_object()

                    if '/XObject' in resources:
                        xobjects = resources['/XObject']
                        if hasattr(xobjects, 'get_object'):
                            xobjects = xobjects.get_object()

                        for xobj_name in xobjects:
                            xobj = xobjects[xobj_name]
                            if hasattr(xobj, 'get_object'):
                                xobj = xobj.get_object()

                            if '/Subtype' in xobj and xobj['/Subtype'] == '/Image':
                                total_images += 1
                                
                                print(f"  {xobj_name}:")
                                
                                # Get image dimensions
                                if '/Width' in xobj:
                                    width = xobj['/Width']
                                    print(f"    Width: {width}")
                                
                                if '/Height' in xobj:
                                    height = xobj['/Height']
                                    print(f"    Height: {height}")
                                
                                # Get color space
                                if '/ColorSpace' in xobj:
                                    cs = xobj['/ColorSpace']
                                    print(f"    ColorSpace: {cs}")
                                
                                # Get bits per component
                                if '/BitsPerComponent' in xobj:
                                    bpc = xobj['/BitsPerComponent']
                                    print(f"    BitsPerComponent: {bpc}")
                                
                                # Get filter (compression)
                                if '/Filter' in xobj:
                                    filter_type = xobj['/Filter']
                                    print(f"    Filter: {filter_type}")
                                
                                # Get stream length
                                if hasattr(xobj, 'get_data'):
                                    try:
                                        data = xobj.get_data()
                                        size = len(data)
                                        total_image_size += size
                                        print(f"    Uncompressed size: {size:,} bytes ({size/(1024*1024):.2f} MB)")
                                    except Exception as e:
                                        print(f"    Error getting data: {e}")
                                
                                print()

                print()

            print(f"SUMMARY:")
            print(f"  Total images: {total_images}")
            print(f"  Total uncompressed image data: {total_image_size:,} bytes ({total_image_size/(1024*1024):.2f} MB)")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    pdf_files = [
        '/home/user/git-practice/1.pdf',
        '/home/user/git-practice/2.pdf',
        '/home/user/git-practice/3.pdf'
    ]

    for pdf_file in pdf_files:
        if Path(pdf_file).exists():
            analyze_images(pdf_file)

if __name__ == '__main__':
    main()
