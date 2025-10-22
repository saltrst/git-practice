#!/usr/bin/env python3
"""
Universal DWF/DWFX to PDF Converter - WITH COMPREHENSIVE LOGGING
Handles ALL DWF formats with full state preservation for debugging

This version saves ALL intermediate files and logs every step for debugging.

Usage:
    python dwf_universal_to_pdf_logged.py input.dwf output.pdf
    python dwf_universal_to_pdf_logged.py input.dwfx output.pdf
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import importlib.util


def load_module(name: str, path: str):
    """Load a Python module from file path"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UniversalDWFConverterLogged:
    """
    Universal converter with FULL logging and state preservation

    Creates a log directory for each conversion with:
    - Original input file copy
    - Routing decision log (JSON)
    - Preprocessing files (if applicable)
    - Intermediate XPS files
    - Processing logs at each step
    - Final PDF output

    NEVER deletes temp files - everything is preserved for debugging
    """

    def __init__(self, log_base_dir: str = "conversion_logs"):
        self.log_base_dir = Path(log_base_dir)
        self.log_dir = None
        self.manifest = {
            "timestamp": None,
            "input_file": None,
            "output_file": None,
            "steps": [],
            "errors": []
        }

    def create_log_directory(self, input_path: str) -> Path:
        """Create timestamped log directory for this conversion"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_name = Path(input_path).stem

        log_dir = self.log_base_dir / f"{timestamp}_{input_name}"
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_dir = log_dir
        self.manifest["timestamp"] = timestamp
        self.manifest["input_file"] = str(input_path)

        return log_dir

    def log_step(self, step_name: str, data: dict, save_json: bool = True):
        """Log a processing step with JSON data"""
        step_info = {
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.manifest["steps"].append(step_info)

        if save_json and self.log_dir:
            step_file = self.log_dir / f"step_{len(self.manifest['steps']):02d}_{step_name}.json"
            with open(step_file, 'w', encoding='utf-8') as f:
                json.dump(step_info, f, indent=2, ensure_ascii=False)

        return step_info

    def save_file_copy(self, source: str, dest_name: str) -> str:
        """Save a copy of a file to log directory"""
        if not self.log_dir:
            return None

        dest_path = self.log_dir / dest_name
        shutil.copy2(source, dest_path)
        return str(dest_path)

    def detect_format(self, file_path: str) -> dict:
        """Detect if file has W2D binary or XPS XML"""
        result = {
            "has_w2d": False,
            "has_xps": False,
            "format": "unknown",
            "needs_preprocessing": False,
            "w2d_files": [],
            "xps_files": [],
            "all_files": []
        }

        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                result["all_files"] = file_list

                # Check for W2D files
                w2d_files = [f for f in file_list if f.endswith('.w2d')]
                if w2d_files:
                    result["has_w2d"] = True
                    result["w2d_files"] = w2d_files
                    result["format"] = "DWF (W2D binary)"
                    result["needs_preprocessing"] = True

                # Check for XPS pages
                fpage_files = [f for f in file_list if f.endswith('.fpage')]
                if fpage_files:
                    result["has_xps"] = True
                    result["xps_files"] = fpage_files
                    result["format"] = "DWFX (XPS XML)"
                    result["needs_preprocessing"] = False

                # Mixed format
                if result["has_w2d"] and result["has_xps"]:
                    result["format"] = "Mixed (W2D + XPS)"
                    result["needs_preprocessing"] = False  # XPS takes priority

        except Exception as e:
            result["error"] = str(e)
            self.manifest["errors"].append({
                "stage": "format_detection",
                "error": str(e)
            })

        return result

    def convert(self, input_path: str, output_path: str, verbose: bool = True) -> bool:
        """
        Universal conversion with FULL logging

        Creates a log directory with:
        - 00_original_input.[dwf|dwfx] - Copy of input file
        - step_01_format_detection.json - Format detection results
        - step_02_routing_claim.json - Decision on what to do
        - step_03_preprocessing/ - Preprocessing files (if needed)
        - step_04_xps_files/ - Extracted XPS files
        - step_05_pdf_generation.json - PDF generation log
        - step_06_final_output.pdf - Final PDF
        - manifest.json - Complete conversion manifest
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Universal DWF/DWFX to PDF Converter - LOGGED VERSION")
            print(f"{'='*60}")
            print(f"Input:  {input_path}")
            print(f"Output: {output_path}")

        try:
            # Create log directory
            log_dir = self.create_log_directory(input_path)
            if verbose:
                print(f"Log directory: {log_dir}")

            # Save original input file
            input_ext = Path(input_path).suffix
            original_copy = self.save_file_copy(input_path, f"00_original_input{input_ext}")
            if verbose:
                print(f"✓ Saved original input to: {Path(original_copy).name}")

            # Step 1: Detect format
            if verbose:
                print(f"\n📋 Step 1: Detecting format...")

            format_info = self.detect_format(input_path)
            self.log_step("format_detection", format_info)

            if verbose:
                print(f"   Format: {format_info['format']}")
                print(f"   Has W2D: {'✅' if format_info['has_w2d'] else '❌'} ({len(format_info.get('w2d_files', []))} files)")
                print(f"   Has XPS: {'✅' if format_info['has_xps'] else '❌'} ({len(format_info.get('xps_files', []))} files)")
                print(f"   Needs preprocessing: {'✅' if format_info['needs_preprocessing'] else '❌'}")

            # Step 2: Log routing claim (what SHOULD happen)
            routing_claim = {
                "format_detected": format_info['format'],
                "needs_preprocessing": format_info['needs_preprocessing'],
                "planned_pipeline": []
            }

            if format_info['needs_preprocessing']:
                routing_claim["planned_pipeline"] = [
                    "Extract W2D binary files",
                    "Parse W2D opcodes",
                    "Generate XPS XML pages",
                    "Create DWFX archive",
                    "Extract XPS pages",
                    "Parse XPS XML",
                    "Generate PDF"
                ]
            else:
                routing_claim["planned_pipeline"] = [
                    "Extract XPS pages directly",
                    "Parse XPS XML",
                    "Generate PDF"
                ]

            self.log_step("routing_claim", routing_claim)

            if verbose:
                print(f"\n📋 Step 2: Routing claim")
                print(f"   Pipeline: {' → '.join(routing_claim['planned_pipeline'])}")

            # Step 3: Preprocess if needed
            working_file = input_path
            preprocessing_dir = None

            if format_info['needs_preprocessing']:
                if verbose:
                    print(f"\n🔄 Step 3: Preprocessing W2D → XPS...")

                # Create preprocessing directory
                preprocessing_dir = log_dir / "step_03_preprocessing"
                preprocessing_dir.mkdir(exist_ok=True)

                temp_dwfx = preprocessing_dir / "preprocessed.dwfx"

                # Convert W2D to XPS
                script_dir = Path(__file__).parent
                sys.path.insert(0, str(script_dir))
                from dwf_to_dwfx_preprocessor import convert_dwf_to_dwfx

                success = convert_dwf_to_dwfx(str(input_path), str(temp_dwfx), verbose=verbose)

                if not success:
                    raise Exception("Preprocessing failed")

                # Log preprocessing results
                preprocessing_info = {
                    "success": success,
                    "input": str(input_path),
                    "output": str(temp_dwfx),
                    "output_size": temp_dwfx.stat().st_size if temp_dwfx.exists() else 0
                }

                # Extract preprocessed DWFX to see what was created
                extract_dir = preprocessing_dir / "extracted"
                extract_dir.mkdir(exist_ok=True)
                with zipfile.ZipFile(temp_dwfx, 'r') as zf:
                    zf.extractall(extract_dir)
                    preprocessing_info["extracted_files"] = zf.namelist()

                self.log_step("preprocessing_applied", preprocessing_info)

                working_file = str(temp_dwfx)
            else:
                if verbose:
                    print(f"\n✅ Step 3: No preprocessing needed (XPS format)")

                self.log_step("preprocessing_applied", {
                    "skipped": True,
                    "reason": "XPS format detected, no preprocessing needed"
                })

            # Step 4: Extract XPS files
            if verbose:
                print(f"\n📦 Step 4: Extracting XPS files...")

            xps_extract_dir = log_dir / "step_04_xps_files"
            xps_extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(working_file, 'r') as zf:
                zf.extractall(xps_extract_dir)
                extracted_files = zf.namelist()

            # Find all .fpage files
            fpage_files = list(xps_extract_dir.rglob("*.fpage"))

            xps_extraction_info = {
                "working_file": str(working_file),
                "extract_directory": str(xps_extract_dir),
                "total_files_extracted": len(extracted_files),
                "fpage_files_found": [str(f.relative_to(xps_extract_dir)) for f in fpage_files],
                "fpage_count": len(fpage_files)
            }

            # Sample first fpage file content
            if fpage_files:
                with open(fpage_files[0], 'r', encoding='utf-8') as f:
                    sample_content = f.read(2000)  # First 2000 chars
                xps_extraction_info["first_fpage_sample"] = sample_content

            self.log_step("xps_extraction", xps_extraction_info)

            if verbose:
                print(f"   Extracted: {len(extracted_files)} files")
                print(f"   Found: {len(fpage_files)} XPS pages")
                for fpage in fpage_files:
                    print(f"     - {fpage.relative_to(xps_extract_dir)}")

            # Step 5: Convert to PDF
            if verbose:
                print(f"\n🔨 Step 5: Converting to PDF...")

            from dwfx_to_pdf import convert_dwfx_to_pdf

            # Use a temp output first
            temp_pdf = log_dir / "step_05_temp_output.pdf"
            success = convert_dwfx_to_pdf(str(working_file), str(temp_pdf), verbose=verbose)

            if not success:
                raise Exception("PDF conversion failed")

            # Log PDF generation
            pdf_info = {
                "success": success,
                "temp_pdf": str(temp_pdf),
                "temp_pdf_size": temp_pdf.stat().st_size if temp_pdf.exists() else 0,
                "final_pdf": str(output_path)
            }

            self.log_step("pdf_generation", pdf_info)

            # Copy to final output
            shutil.copy2(temp_pdf, output_path)

            # Also save to log directory
            final_copy = log_dir / "step_06_final_output.pdf"
            shutil.copy2(output_path, final_copy)

            # Save final manifest
            self.manifest["output_file"] = str(output_path)
            self.manifest["log_directory"] = str(log_dir)
            self.manifest["success"] = True

            manifest_path = log_dir / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2, ensure_ascii=False)

            if verbose:
                file_size = Path(output_path).stat().st_size
                print(f"\n{'='*60}")
                print(f"✅ Conversion Complete!")
                print(f"{'='*60}")
                print(f"Output: {output_path}")
                print(f"Size:   {file_size:,} bytes")
                print(f"Log directory: {log_dir}")
                print(f"{'='*60}\n")

            return True

        except Exception as e:
            if verbose:
                print(f"\n❌ Conversion failed: {e}")
                import traceback
                traceback.print_exc()

            # Log error
            self.manifest["errors"].append({
                "stage": "conversion",
                "error": str(e)
            })
            self.manifest["success"] = False

            # Save manifest even on error
            if self.log_dir:
                manifest_path = self.log_dir / "manifest.json"
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(self.manifest, f, indent=2, ensure_ascii=False)

            return False


def main():
    """Command line interface"""
    if len(sys.argv) < 3:
        print("""
Universal DWF/DWFX to PDF Converter - LOGGED VERSION

This version saves ALL intermediate files and logs for debugging!

USAGE:
    python dwf_universal_to_pdf_logged.py input.dwf output.pdf
    python dwf_universal_to_pdf_logged.py input.dwfx output.pdf

LOG DIRECTORY STRUCTURE:
    conversion_logs/YYYYMMDD_HHMMSS_filename/
    ├── 00_original_input.[dwf|dwfx]    - Copy of input file
    ├── step_01_format_detection.json   - Format detection results
    ├── step_02_routing_claim.json      - Pipeline decision
    ├── step_03_preprocessing/          - Preprocessing files (if W2D)
    │   ├── preprocessed.dwfx
    │   └── extracted/                  - Extracted preprocessing result
    ├── step_04_xps_files/              - Extracted XPS files
    │   └── Documents/1/Pages/*.fpage   - XPS page files
    ├── step_05_temp_output.pdf         - Temp PDF output
    ├── step_06_final_output.pdf        - Final PDF copy
    └── manifest.json                   - Complete conversion log

FEATURES:
    ✅ Preserves ALL intermediate files (nothing deleted)
    ✅ Logs every processing step as JSON
    ✅ Saves original input for comparison
    ✅ Creates detailed manifest of entire conversion
    ✅ Perfect for debugging rendering issues

EXAMPLES:
    python dwf_universal_to_pdf_logged.py 1.dwfx output.pdf
    python dwf_universal_to_pdf_logged.py 3.dwf output.pdf

    # Check logs:
    cat conversion_logs/*/manifest.json
    ls -la conversion_logs/*/step_04_xps_files/
""")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    converter = UniversalDWFConverterLogged()
    success = converter.convert(input_file, output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
