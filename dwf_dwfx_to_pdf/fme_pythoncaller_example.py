"""
FME PythonCaller Example - DWFX to PDF Conversion
==================================================

This script demonstrates how to use the DWFX to PDF converter
in FME's PythonCaller transformer.

SETUP:
1. Place dwfx_to_pdf.py in FME Python scripts directory
2. Add PythonCaller transformer to workspace
3. Copy this code into PythonCaller's Python Script parameter
4. Configure input/output attributes as shown below

REQUIRED ATTRIBUTES (Input):
- dwfx_path: Path to input DWFX file (string)

OPTIONAL ATTRIBUTES (Input):
- output_directory: Custom output directory (string)
- output_filename: Custom output filename (string)

OUTPUT ATTRIBUTES (Set by this script):
- pdf_path: Path to generated PDF file (string)
- conversion_status: 'success' or 'failed' (string)
- error_message: Error details if failed (string)
- page_count: Number of pages converted (integer)
- file_size_bytes: Output PDF size in bytes (integer)
- conversion_time_ms: Time taken in milliseconds (integer)
"""

import fme
import fmeobjects
import os
import time
from pathlib import Path

# Import the DWFX to PDF converter
from dwfx_to_pdf import DWFXToPDFConverter, convert_dwfx_to_pdf

# Initialize converter (shared across all features)
converter = DWFXToPDFConverter()


def processFeature(feature):
    """
    Process each feature through the PythonCaller
    
    This function is called once for each feature that enters the transformer.
    """
    
    # Start timing
    start_time = time.time()
    
    try:
        # ===================================================================
        # STEP 1: Get input attributes
        # ===================================================================
        
        dwfx_path = feature.getAttribute('dwfx_path')
        
        if not dwfx_path:
            raise ValueError("Missing required attribute: dwfx_path")
        
        if not os.path.exists(dwfx_path):
            raise FileNotFoundError(f"DWFX file not found: {dwfx_path}")
        
        # ===================================================================
        # STEP 2: Determine output path
        # ===================================================================
        
        # Check for custom output directory
        output_dir = feature.getAttribute('output_directory')
        if not output_dir:
            # Use same directory as input file
            output_dir = os.path.dirname(dwfx_path)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Check for custom output filename
        output_filename = feature.getAttribute('output_filename')
        if not output_filename:
            # Use input filename with .pdf extension
            input_filename = Path(dwfx_path).stem
            output_filename = f"{input_filename}.pdf"
        
        # Construct full output path
        pdf_path = os.path.join(output_dir, output_filename)
        
        # ===================================================================
        # STEP 3: Convert DWFX to PDF
        # ===================================================================
        
        success = converter.convert(dwfx_path, pdf_path)
        
        # ===================================================================
        # STEP 4: Set output attributes
        # ===================================================================
        
        if success:
            # Conversion successful
            feature.setAttribute('pdf_path', pdf_path)
            feature.setAttribute('conversion_status', 'success')
            feature.setAttribute('error_message', '')
            
            # Get output file stats
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                feature.setAttribute('file_size_bytes', file_size)
            
            # Calculate conversion time
            conversion_time_ms = int((time.time() - start_time) * 1000)
            feature.setAttribute('conversion_time_ms', conversion_time_ms)
            
            # Log success
            print(f"✅ Converted: {dwfx_path} → {pdf_path} ({file_size:,} bytes, {conversion_time_ms}ms)")
            
        else:
            # Conversion failed
            error_msg = converter.get_last_error()
            feature.setAttribute('pdf_path', '')
            feature.setAttribute('conversion_status', 'failed')
            feature.setAttribute('error_message', error_msg)
            
            # Log failure
            print(f"❌ Failed: {dwfx_path} - {error_msg}")
        
        # ===================================================================
        # STEP 5: Output feature
        # ===================================================================
        
        pyoutput(feature)
        
    except Exception as e:
        # Handle any unexpected errors
        error_msg = f"Unexpected error: {str(e)}"
        feature.setAttribute('pdf_path', '')
        feature.setAttribute('conversion_status', 'failed')
        feature.setAttribute('error_message', error_msg)
        
        print(f"❌ Error processing feature: {error_msg}")
        
        # Output feature even on error (so it can be logged)
        pyoutput(feature)


# ============================================================================
# ALTERNATIVE: Batch Processing Version
# ============================================================================

def processFeature_Batch(feature):
    """
    Alternative version for batch processing
    
    This version expects:
    - input_directory: Directory containing DWFX files
    - output_directory: Directory for PDF output
    
    It will convert ALL DWFX files in the input directory.
    """
    
    try:
        # Get directories
        input_dir = feature.getAttribute('input_directory')
        output_dir = feature.getAttribute('output_directory')
        
        if not input_dir or not output_dir:
            raise ValueError("Missing required attributes: input_directory, output_directory")
        
        # Batch convert
        results = converter.batch_convert(input_dir, output_dir)
        
        # Set result attributes
        feature.setAttribute('total_files', results['total'])
        feature.setAttribute('success_count', results['success'])
        feature.setAttribute('failed_count', results['failed'])
        feature.setAttribute('conversion_status', 'complete')
        
        # Log results
        print(f"📊 Batch conversion complete:")
        print(f"   Total: {results['total']}")
        print(f"   Success: {results['success']}")
        print(f"   Failed: {results['failed']}")
        
        # Output feature
        pyoutput(feature)
        
    except Exception as e:
        error_msg = f"Batch conversion error: {str(e)}"
        feature.setAttribute('conversion_status', 'failed')
        feature.setAttribute('error_message', error_msg)
        print(f"❌ {error_msg}")
        pyoutput(feature)


# ============================================================================
# USAGE NOTES
# ============================================================================

"""
SINGLE FILE CONVERSION:
-----------------------
Use the processFeature() function above (default).

Required FME setup:
1. Reader → Provides features with dwfx_path attribute
2. PythonCaller → Uses this script
3. Tester → Filter by conversion_status
4. Writers → Success/failure outputs


BATCH CONVERSION:
-----------------
Use the processFeature_Batch() function instead.

Required FME setup:
1. Creator → Create single feature
2. AttributeCreator → Set input_directory and output_directory
3. PythonCaller → Uses processFeature_Batch (rename function)
4. Logger → Log results


EXAMPLE WORKFLOW:
-----------------

[DirectoryReader]
    ↓ (list DWFX files)
[AttributeManager]
    ↓ (set dwfx_path = @Value(path))
[PythonCaller] ← THIS SCRIPT
    ↓
[Tester]
    ↓ conversion_status = 'success'
[AttributeManager]
    ↓ (prepare success log)
[TextFileWriter] (success.log)
    ↓ conversion_status = 'failed'
[AttributeManager]
    ↓ (prepare error log)
[TextFileWriter] (errors.log)


TESTING IN FME:
---------------

1. Create simple workspace:
   - Creator (1 feature)
   - AttributeCreator: dwfx_path = "C:/path/to/test.dwfx"
   - PythonCaller: Use this script
   - Logger: Log pdf_path and conversion_status

2. Run workspace and check log output

3. Verify PDF was created at expected location


TROUBLESHOOTING:
----------------

Issue: "Module not found: dwfx_to_pdf"
Solution: Ensure dwfx_to_pdf.py is in FME Python path
          or add: sys.path.append('/path/to/script')

Issue: "Permission denied"
Solution: Check FME has write access to output directory

Issue: "Conversion failed"
Solution: Check error_message attribute for details
          Enable verbose logging in converter


PERFORMANCE TIPS:
-----------------

1. Use batch mode for multiple files (faster)
2. Process features in parallel if possible
3. Use local/fast storage for temp files
4. Consider memory limits for large files


SUPPORT:
--------

See DWFX_TO_PDF_DOCUMENTATION.md for complete guide
"""
