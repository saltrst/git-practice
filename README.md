# DWF to PDF Converter

A Python-based converter that transforms DWF (Design Web Format) and DWFX files into PDF documents. This project parses the binary W2D graphics streams from CAD files and renders them using ReportLab.

## Current Status

**Version:** 1.0.0
**Completion:** ~68% (Core functionality working)
**Last Updated:** October 2025

### What Works
- Classic DWF (.dwf) files with W2D streams
- DWF 6.0+ (.dwf) ZIP-packaged files
- DWFX (.dwfx) files containing W2D streams
- 47+ opcode handlers implemented (covers most common geometry)
- Command-line interface for direct conversion
- Python library for programmatic use
- Auto-scaling to fit drawings on PDF pages

### Known Limitations
- DWFX files with XPS-only content (no W2D streams) are not supported
- Some advanced rendering features may not be implemented
- Unicode/Hebrew text support implemented but needs further testing in PDFs

### Test Files Included
- **3.dwf** (9.8 MB): Classic DWF with W2D stream - **Works** ✓
- **1.dwfx** (5.2 MB): XPS-only DWFX - **Not Supported** ✗
- **2.dwfx** (9.4 MB): XPS-only DWFX - **Not Supported** ✗

## Quick Start

### Download and Setup

1. **Download as ZIP from GitHub**
   ```bash
   # If you downloaded as ZIP, extract it:
   unzip git-practice-main.zip
   cd git-practice-main
   ```

2. **Install Python Dependencies**
   ```bash
   pip install reportlab
   ```

3. **You're ready to convert!**
   ```bash
   python dwf2pdf.py 3.dwf
   ```

That's it! No complex setup required.

## CLI Usage

### Basic Conversion

```bash
# Convert DWF to PDF (auto-generates output name)
python dwf2pdf.py input.dwf

# Specify output filename
python dwf2pdf.py input.dwf output.pdf

# Convert DWFX file (with W2D streams)
python dwf2pdf.py design.dwfx design.pdf
```

### Advanced Options

```bash
# Use specific page size
python dwf2pdf.py drawing.dwf --page-size letter
python dwf2pdf.py drawing.dwf --page-size a4
python dwf2pdf.py drawing.dwf --page-size tabloid
python dwf2pdf.py drawing.dwf --page-size a3

# Auto-fit drawing to page (default)
python dwf2pdf.py drawing.dwf --page-size auto

# Apply custom scale factor
python dwf2pdf.py drawing.dwf --scale 0.05

# Verbose mode for debugging
python dwf2pdf.py drawing.dwf -v

# Show help
python dwf2pdf.py --help

# Show version
python dwf2pdf.py --version
```

### Testing with Included Files

```bash
# This should work - Classic DWF with W2D stream
python dwf2pdf.py 3.dwf

# These will fail gracefully - XPS-only DWFX files
python dwf2pdf.py 1.dwfx  # Shows unsupported format message
python dwf2pdf.py 2.dwfx  # Shows unsupported format message
```

### Verbose Output Example

```bash
python dwf2pdf.py 3.dwf -v
```

Output:
```
📄 Input:  3.dwf (9.78 MB)
📄 Output: 3.pdf
⚙️  Page size: auto

🔍 Parsing DWF/DWFX file...
✓ Parsed 50234 opcodes
  Top opcode types:
    polyline: 12453
    set_color: 8932
    line: 7821

🔧 Auto page size: 16.5" × 10.8"

🎨 Rendering PDF...
✅ Success! Created 3.pdf (3.27 MB)
```

## Library Usage

You can also use this as a Python library in your own scripts:

### Basic Example

```python
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf

# Parse DWF file
opcodes = parse_dwf_file("input.dwf")
print(f"Parsed {len(opcodes)} opcodes")

# Render to PDF
render_dwf_to_pdf(opcodes, "output.pdf", pagesize=(11*72, 17*72), scale=0.1)
print("PDF created successfully")
```

### Advanced Example with Custom Processing

```python
import sys
from pathlib import Path

project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf
from reportlab.lib.pagesizes import letter, A4

# Parse DWF file
opcodes = parse_dwf_file("drawing.dwf")

# Filter or modify opcodes
filtered_opcodes = [op for op in opcodes if op.get('type') != 'text']

# Calculate bounding box
all_coords = []
for op in opcodes:
    if 'vertices' in op:
        all_coords.extend(op['vertices'])
    if 'start' in op and 'end' in op:
        all_coords.extend([op['start'], op['end']])

if all_coords:
    min_x = min(c[0] for c in all_coords)
    max_x = max(c[0] for c in all_coords)
    min_y = min(c[1] for c in all_coords)
    max_y = max(c[1] for c in all_coords)
    print(f"Drawing bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")

# Render with custom settings
render_dwf_to_pdf(
    filtered_opcodes,
    "output.pdf",
    pagesize=letter,
    scale=0.15
)
```

### Error Handling

```python
try:
    opcodes = parse_dwf_file("file.dwfx")
    render_dwf_to_pdf(opcodes, "output.pdf")
except NotImplementedError as e:
    print(f"Unsupported format: {e}")
except FileNotFoundError:
    print("Input file not found")
except Exception as e:
    print(f"Error: {e}")
```

## Project Structure

```
git-practice/
├── README.md                          # This file
├── dwf2pdf.py                         # Command-line interface (NEW)
├── .gitignore                         # Git ignore rules
│
├── Test Files (Included)
├── 3.dwf                              # Working test file (9.8 MB)
├── 1.dwfx                             # XPS-only (not supported)
├── 2.dwfx                             # XPS-only (not supported)
│
├── dwf-to-pdf-project/                # Core library
│   ├── README.md                      # Project documentation
│   ├── integration/                   # Main conversion modules
│   │   ├── dwf_parser_v1.py          # DWF/DWFX parser (WORKING)
│   │   ├── pdf_renderer_v1.py        # PDF renderer (WORKING)
│   │   └── test_integration.py       # Integration tests
│   ├── agents/                        # Opcode handlers
│   │   ├── agent_outputs/            # 71 opcode handler modules
│   │   └── agent_tasks/              # Agent task specifications
│   ├── spec/                          # Format specifications
│   └── verification/                  # Test and validation files
│
├── Debug/Test Scripts (For Development)
├── convert_working.py                 # Working conversion script
├── convert_auto_scale.py              # Auto-scaling version
├── convert_scaled.py                  # Pre-scaled version
├── debug_origins.py                   # Debug set_origin opcodes
├── test_dwfx_support.py               # DWFX format tests
│
└── Analysis Reports (From 10-Agent Testing)
    ├── ORCHESTRATION_SYNTHESIS_REPORT.md
    ├── SYSTEM_RECONCILIATION_REPORT.md
    ├── agent1_format_analysis.md
    ├── agent2_scale_results.md
    ├── agent3_raster_analysis.py
    └── [35+ additional analysis files]
```

## Directory Details

### Core Components

**`dwf-to-pdf-project/integration/`**
- `dwf_parser_v1.py` (31KB): Main parser handling DWF/DWFX format detection and W2D stream extraction
- `pdf_renderer_v1.py` (32KB): ReportLab-based PDF renderer with coordinate transformation
- Both modules are production-ready with comprehensive error handling

**`dwf-to-pdf-project/agents/agent_outputs/`**
- 71 individual opcode handler modules (one per opcode family)
- Each module has its own tests and documentation
- Handles geometry, text, colors, fills, beziers, Gouraud shading, etc.

**`dwf-to-pdf-project/spec/`**
- Opcode reference documentation
- Format specifications extracted from DWF Toolkit C++ source

### Test and Debug Files

**Working Conversion Scripts:**
- `convert_working.py`: Basic working version with relative→absolute coordinate conversion
- `convert_auto_scale.py`: Auto-calculates optimal scale factor
- `convert_scaled.py`: Pre-scales coordinates before rendering

**Debug Scripts:**
- `debug_origins.py`: Examines set_origin opcode behavior
- `debug_coords.py`: Analyzes coordinate systems
- `test_dwfx_support.py`: Tests DWFX format detection

### Analysis Artifacts

The repository includes extensive analysis from 10-agent parallel testing:
- Scale factor analysis and optimization
- Coordinate transformation verification
- Opcode distribution analysis
- Bounding box calculations
- Reference PDF comparisons
- Raster image extraction tests

## Dependencies

**Required:**
- Python 3.7+
- reportlab (PDF generation)

**Install:**
```bash
pip install reportlab
```

No other dependencies required for basic usage!

## Troubleshooting

### "Input file not found"
Make sure the DWF/DWFX file path is correct:
```bash
ls -la *.dwf *.dwfx
python dwf2pdf.py 3.dwf
```

### "Unsupported format: XPS-only DWFX"
This DWFX file contains only XPS content (no W2D streams).

**Workaround:** Use Autodesk DWG TrueView (free) to convert DWFX to DWF format:
1. Download from autodesk.com
2. Open DWFX file
3. Save As → DWF format
4. Convert the new DWF file

### Empty or small PDF output
This usually means coordinate scaling is incorrect:
```bash
# Try different scale factors
python dwf2pdf.py input.dwf --scale 0.01
python dwf2pdf.py input.dwf --scale 0.05
python dwf2pdf.py input.dwf --scale 0.1
python dwf2pdf.py input.dwf --scale 0.5
```

### Missing geometry in PDF
Enable verbose mode to see what opcodes were parsed:
```bash
python dwf2pdf.py input.dwf -v
```

Check the opcode counts - if you see many opcodes parsed but small PDF:
1. Scale factor may be wrong
2. Coordinates may need translation
3. Some opcodes may not be implemented

### Import errors
Make sure you're running from the repository root:
```bash
cd /path/to/git-practice
python dwf2pdf.py 3.dwf
```

The script automatically adds `dwf-to-pdf-project/` to the Python path.

## Architecture Overview

### Conversion Pipeline

```
DWF/DWFX File
    ↓
[Format Detection]
    ↓
[ZIP Extraction] (if DWF 6.0+ or DWFX)
    ↓
[W2D Stream Identification]
    ↓
[Binary Opcode Parser]
    ↓
[Opcode Dispatcher] → 71 Handler Modules
    ↓
[Parsed Opcode List]
    ↓
[Coordinate Transformation]
    ↓
[ReportLab PDF Renderer]
    ↓
PDF Output
```

### Key Technical Details

**Format Support:**
- Classic DWF: Direct binary W2D stream
- DWF 6.0+: ZIP container with W2D in `*.w2d` files
- DWFX: ZIP container (XPS) with optional W2D streams

**Coordinate System:**
- DWF uses 31-bit signed integers
- Relative coordinates are deltas from current position
- `set_origin` opcodes provide absolute positions
- Transformed to PDF coordinate space with scaling

**Opcode Parsing:**
- Single-byte opcodes (0x00-0xFF)
- Extended ASCII opcodes (parenthesized)
- Binary vs ASCII format detection
- 47+ handler families implemented

**PDF Rendering:**
- ReportLab canvas API
- Coordinate flip (DWF Y-up → PDF Y-down)
- Auto-scaling to fit page
- Margin preservation

## Development History

This project was developed through AI-assisted parallel agent translation:

**Phase 0:** System discovery and format analysis
**Phase 1:** Proof of concept (4 opcodes in 15 minutes)
**Phase 2:** 10-agent parallel translation (43 opcodes)
**Phase 3:** Integration and testing
**Phase 4:** DWFX support and format detection
**Current:** CLI tool and documentation

See `dwf-to-pdf-project/README.md` for detailed agent coordination details.

## Testing

### Quick Test
```bash
# Should produce a valid PDF
python dwf2pdf.py 3.dwf
```

### Verbose Test
```bash
# See detailed parsing and rendering info
python dwf2pdf.py 3.dwf -v
```

### Library Test
```bash
cd dwf-to-pdf-project/integration
python test_integration.py
```

### Expected Results

**3.dwf → 3.pdf:**
- Input: 9.78 MB DWF file
- Output: ~3 MB PDF
- Contains: Architectural/engineering drawing with geometry
- Opcodes: ~50,000 (mostly polylines, lines, colors)

**1.dwfx / 2.dwfx:**
- Should fail gracefully with message:
  ```
  ❌ Unsupported format:
  DWFX file contains only XPS content (no W2D streams)
  Use Autodesk DWG TrueView to convert to DWF format
  ```

## Future Enhancements

- Support for XPS-only DWFX files (requires XPS parser)
- Implement remaining 150+ opcodes for full format coverage
- Add raster image support (embedded PNG/TIFF)
- Multi-page PDF support for multi-sheet DWF files
- GUI interface for batch conversions
- Progress bars for large files
- PDF compression options

## References

- [DWF Toolkit 7.7 Source](https://github.com/kveretennicov/dwf-toolkit) - C++ reference implementation
- [Paul Bourke WHIP Specification](https://paulbourke.net/dataformats/whip/) - W2D format spec
- [DWF Format Documentation](https://docs.fileformat.com/cad/dwf/) - Overview
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf) - PDF generation

## Contributing

This is an experimental project demonstrating AI-assisted code translation techniques. The codebase was generated through parallel agent coordination using structured prompts and verification protocols.

## License

This proof of concept demonstrates mechanical translation techniques.
DWF Toolkit is licensed by Autodesk (see dwf-toolkit-source/LICENSE).

---

**Need Help?**

1. Check the Troubleshooting section above
2. Run with `-v` flag for detailed output
3. Review the analysis reports in the repository
4. Check `dwf-to-pdf-project/README.md` for technical details

**Quick Links:**
- CLI Tool: `dwf2pdf.py`
- Parser: `dwf-to-pdf-project/integration/dwf_parser_v1.py`
- Renderer: `dwf-to-pdf-project/integration/pdf_renderer_v1.py`
- Tests: `dwf-to-pdf-project/integration/test_integration.py`
