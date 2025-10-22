#!/usr/bin/env python3
"""
Detailed analysis of reference PDFs - specifically checking page-by-page variations
"""

import PyPDF2
import json

def analyze_all_pages(pdf_path):
    """Analyze every page in a PDF"""
    print(f"\nDetailed page-by-page analysis for: {pdf_path}")
    print("=" * 80)

    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)

        print(f"Total pages: {len(reader.pages)}\n")

        for i, page in enumerate(reader.pages):
            mediabox = page.mediabox
            width = float(mediabox.width)
            height = float(mediabox.height)

            print(f"Page {i+1}:")
            print(f"  Size: {width:.2f} x {height:.2f} points")
            print(f"  Size: {width/72:.2f} x {height/72:.2f} inches")
            print(f"  Aspect: {width/height:.4f}")

            # Check for rotation
            if '/Rotate' in page:
                print(f"  Rotation: {page['/Rotate']}")

            # Check if page has annotations
            if '/Annots' in page:
                print(f"  Has annotations: Yes")

            print()

def check_standard_page_sizes():
    """Compare against standard page sizes"""
    print("\nSTANDARD PAGE SIZES FOR REFERENCE:")
    print("=" * 80)

    standards = {
        "Letter": (612, 792),  # 8.5 x 11 inches
        "Legal": (612, 1008),   # 8.5 x 14 inches
        "Tabloid": (792, 1224), # 11 x 17 inches
        "A4": (595, 842),       # 210 x 297 mm
        "A3": (842, 1191),      # 297 x 420 mm
        "A2": (1191, 1684),     # 420 x 594 mm
        "A1": (1684, 2384),     # 594 x 841 mm
        "A0": (2384, 3370),     # 841 x 1189 mm
        "ARCH A": (648, 864),   # 9 x 12 inches
        "ARCH B": (864, 1296),  # 12 x 18 inches
        "ARCH C": (1296, 1728), # 18 x 24 inches
        "ARCH D": (1728, 2592), # 24 x 36 inches
        "ARCH E": (2592, 3456), # 36 x 48 inches
    }

    for name, (w, h) in standards.items():
        print(f"{name:12} {w:6.0f} x {h:6.0f} pt  |  {w/72:5.2f} x {h/72:5.2f} in")

    return standards

def compare_to_standards(pdf_sizes, standards):
    """Compare PDF sizes to standard sizes"""
    print("\n\nCOMPARISON TO STANDARD SIZES:")
    print("=" * 80)

    for pdf_name, pages in pdf_sizes.items():
        print(f"\n{pdf_name}:")
        for page_num, (width, height) in pages.items():
            print(f"  Page {page_num}: {width:.2f} x {height:.2f} pt")

            # Try both orientations
            best_match = None
            min_diff = float('inf')

            for std_name, (std_w, std_h) in standards.items():
                # Check portrait orientation
                diff1 = abs(width - std_w) + abs(height - std_h)
                # Check landscape orientation
                diff2 = abs(width - std_h) + abs(height - std_w)

                if diff1 < min_diff:
                    min_diff = diff1
                    best_match = (std_name, "portrait", diff1)

                if diff2 < min_diff:
                    min_diff = diff2
                    best_match = (std_name, "landscape", diff2)

            if best_match and best_match[2] < 50:  # Within 50 points
                print(f"    Closest match: {best_match[0]} ({best_match[1]}), diff: {best_match[2]:.1f} pt")
            else:
                print(f"    Custom size (no standard match)")

def main():
    pdf_files = [
        "/home/user/git-practice/1.pdf",
        "/home/user/git-practice/2.pdf",
        "/home/user/git-practice/3.pdf"
    ]

    # Detailed analysis of each PDF
    pdf_sizes = {}

    for pdf_file in pdf_files:
        analyze_all_pages(pdf_file)

        # Store sizes for comparison
        with open(pdf_file, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pdf_name = pdf_file.split('/')[-1]
            pdf_sizes[pdf_name] = {}

            for i, page in enumerate(reader.pages):
                mediabox = page.mediabox
                pdf_sizes[pdf_name][i+1] = (float(mediabox.width), float(mediabox.height))

    # Show standard sizes
    standards = check_standard_page_sizes()

    # Compare
    compare_to_standards(pdf_sizes, standards)

if __name__ == "__main__":
    main()
