# Agent 8: Bounding Box Analysis Report

**Mission:** Calculate and compare expected vs actual bounding boxes for all test files.

## Executive Summary

This analysis examines bounding boxes from parsed DWF/DWFX geometry and compares them to reference PDF page sizes.

### Key Findings

✗ **Aspect ratios DON'T MATCH** - Significant geometry/PDF proportion differences

## Test Files Analyzed

| File | Type | Size | Reference PDF | Size |
|------|------|------|---------------|------|
| 1.dwfx | DWFX | 5.0 MB | 1.pdf | 3.1 MB |
| 2.dwfx | DWFX | 8.9 MB | 2.pdf | 5.0 MB |
| 3.dwf | DWF | 9.3 MB | 3.pdf | 3.1 MB |

**Format Types:**
- **DWFX**: XPS (XML Paper Specification) format - ZIP archive containing XML with SVG-like paths
- **DWF**: W2D binary stream format - ZIP archive containing compressed W2D opcodes

## Test 1: Calculated Bounding Boxes from Geometry

Extracted all geometry coordinates and calculated min/max X/Y ranges.

| File | Min X | Max X | Min Y | Max Y | Width | Height | Aspect Ratio | Points |
|------|-------|-------|-------|-------|-------|--------|--------------|--------|
| 3.dwf | -2147711877.00 | -2147574846.00 | 13402.00 | 30843.00 | 137031.00 | 17441.00 | 7.8568 | 3878 |

## Test 2: Reference PDF Page Sizes

Extracted MediaBox dimensions from reference PDFs.

| PDF File | Width (pts) | Height (pts) | Width (in) | Height (in) | Aspect Ratio | Pages |
|----------|-------------|--------------|------------|-------------|--------------|-------|
| 1.pdf | 6945.00 | 1871.00 | 96.46 | 25.99 | 3.7119 | 1 |
| 2.pdf | 1782.90 | 2547.00 | 24.76 | 35.38 | 0.7000 | 4 |
| 3.pdf | 800.00 | 600.00 | 11.11 | 8.33 | 1.3333 | 1 |

## Test 3: Aspect Ratio Comparison

Comparing (geometry_width / geometry_height) vs (pdf_width / pdf_height)

| File | Geometry AR | PDF AR | Difference | % Diff | Match? |
|------|-------------|--------|------------|--------|--------|
| 3.dwf | 7.8568 | 1.3333 | 6.5235 | 489.26% | ✗ No |

## Analysis and Findings

### Concrete Claim: Aspect Ratios

**CLAIM: Aspect ratios DON'T MATCH perfectly between geometry and PDFs.**

**Evidence:**
- 3.dwf: 489.3% difference (Geometry: 7.8568, PDF: 1.3333)

**Possible Causes:**
1. PDF page sizes don't match content aspect ratio
2. Content has margins/padding in PDF
3. Non-uniform scaling applied during conversion
4. Viewport/clipping applied to geometry

**Conclusion:** Geometry bounding box should be used as authoritative size. Apply uniform scaling to maintain proportions.

## Per-File Detailed Analysis

### 1.dwfx

**Format:** DWFX  
**Size:** 5.0 MB → 3.1 MB PDF

**PDF Page Size:**
- Dimensions: 6945.00 × 1871.00 points (96.46 × 25.99 inches)
- Aspect ratio: 3.7119
- Pages: 1

### 2.dwfx

**Format:** DWFX  
**Size:** 8.9 MB → 5.0 MB PDF

**PDF Page Size:**
- Dimensions: 1782.90 × 2547.00 points (24.76 × 35.38 inches)
- Aspect ratio: 0.7000
- Pages: 4

### 3.dwf

**Format:** DWF  
**Size:** 9.3 MB → 3.1 MB PDF

**Geometry Bounding Box:**
- Dimensions: 137031.00 × 17441.00 units
- Range: X=[-2147711877, -2147574846], Y=[13402, 30843]
- Aspect ratio: 7.8568
- Data points: 3878

**PDF Page Size:**
- Dimensions: 800.00 × 600.00 points (11.11 × 8.33 inches)
- Aspect ratio: 1.3333
- Pages: 1

**Scale Analysis:**
- Scale X: 0.005838
- Scale Y: 0.034402
- Recommended uniform scale: 0.005838
- Aspect match: False

## Recommendations

### Page Sizing Strategy

Since aspect ratios don't match perfectly:

1. **Use geometry bounding box as authoritative**
2. **Apply uniform scaling** (min of X/Y scale factors)
3. **Center content on page with margins**
4. **Consider adding viewport/clip region support**

```python
# Recommended approach
bbox_aspect = bbox_width / bbox_height
page_aspect = page_width / page_height

if bbox_aspect > page_aspect:
    # Wider than page, fit to width
    scale = page_width / bbox_width
else:
    # Taller than page, fit to height
    scale = page_height / bbox_height
```

## Methodology

### Coordinate Extraction

**DWFX Files (XPS Format):**
- Extracted from FixedPage.fpage XML files
- Parsed SVG-style Path Data attributes
- Coordinates already in absolute format (points)

**DWF Files (W2D Format):**
- Extracted W2D streams from ZIP archive
- Parsed binary opcodes (lines, polylines, triangles)
- Converted relative coordinates to absolute
- Tracked origin state throughout parsing

**Bounding Box Calculation:**
- Accumulated all geometry coordinates
- Calculated min/max for X and Y
- BBox = [min_x, max_x] × [min_y, max_y]
- Aspect ratio = width / height

### PDF Analysis

- Used PyPDF2 to extract MediaBox
- Measured in points (1 pt = 1/72 inch)
- First page dimensions used for comparison

---

*Analysis by agent8_final_analysis.py*