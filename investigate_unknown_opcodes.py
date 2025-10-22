#!/usr/bin/env python3
"""
Investigate Unknown Opcodes - Deep Dive Analysis

This script examines unknown opcodes in detail to determine if they
should be implemented in the parser or renderer.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent / 'dwf-to-pdf-project'
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file, OPCODE_HANDLERS

# Parse the W2D file
w2d_file = '/home/user/git-practice/drawing.w2d'
print("=" * 80)
print("UNKNOWN OPCODE INVESTIGATION")
print("=" * 80)
print(f"\nParsing: {w2d_file}")

opcodes = parse_dwf_file(w2d_file)

print(f"Total opcodes: {len(opcodes)}")
print()

# Filter unknown opcodes
unknown_opcodes = [op for op in opcodes if op.get('type', '').startswith('unknown') or op.get('type') == 'error']

print(f"Unknown opcodes found: {len(unknown_opcodes)}")
print()

# Group by hex value
from collections import defaultdict
unknown_by_hex = defaultdict(list)

for op in unknown_opcodes:
    hex_val = op.get('opcode_hex', op.get('opcode_id', 'N/A'))
    unknown_by_hex[hex_val].append(op)

print("=" * 80)
print("UNKNOWN OPCODE DETAILS")
print("=" * 80)

# Known opcode meanings based on DWF/W2D specification
OPCODE_MEANINGS = {
    0x03: "SET_COLOR_RGBA - Already implemented in parser (line 171)",
    0x17: "LINE_WEIGHT - Already implemented in parser (line 209)",
    0x46: "SET_FILL_ON - Already implemented in parser (line 173)",
    0x56: "SET_VISIBILITY_ON - Already implemented in parser (line 175)",
    0x63: "SET_COLOR_INDEXED (Single-byte color) - Already implemented in parser (line 270)",
    0xEE: "Undocumented opcode - Likely extended attribute",
    0xF6: "Undocumented opcode - Likely metadata",
    0xFE: "Undocumented opcode - Likely metadata/padding",
}

for hex_val, ops in sorted(unknown_by_hex.items()):
    print(f"\n{hex_val} ({len(ops)} occurrences)")
    print("-" * 80)

    # Get first example
    example = ops[0]
    print(f"Type: {example.get('type')}")

    # Check if it's in OPCODE_HANDLERS
    if hex_val.startswith('0x'):
        try:
            byte_val = int(hex_val, 16)
            if byte_val in OPCODE_HANDLERS:
                module, func = OPCODE_HANDLERS[byte_val]
                print(f"STATUS: IMPLEMENTED in parser!")
                print(f"  Module: {module.__name__}")
                print(f"  Function: {func}")
                print(f"  Note: Opcode is in dispatch table but may be returning 'unknown' type")
            else:
                print(f"STATUS: NOT in dispatch table")
                if byte_val in OPCODE_MEANINGS:
                    print(f"  Known meaning: {OPCODE_MEANINGS[byte_val]}")
        except:
            pass

    # Check for Extended ASCII
    if example.get('type') == 'unknown_extended_ascii':
        opcode_name = example.get('opcode_name', 'N/A')
        print(f"Opcode Name: {opcode_name}")
        print(f"Data: {example.get('data', '')[:100]}...")

        # W2DV0600 is W2D version marker
        if 'W2DV' in opcode_name:
            print(f"STATUS: This is a W2D version marker (metadata)")
            print(f"  Should be handled as metadata, not an error")

    # Show full details for first example
    if len(ops) <= 3:
        print(f"Full data:")
        for key, value in example.items():
            if key not in ['type', 'opcode_hex']:
                print(f"  {key}: {value}")

print()
print("=" * 80)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)
print()

# Count categories
implemented_but_marked_unknown = 0
truly_unknown = 0
extended_ascii_unknown = 0

for hex_val, ops in unknown_by_hex.items():
    if hex_val.startswith('0x'):
        try:
            byte_val = int(hex_val, 16)
            if byte_val in OPCODE_HANDLERS:
                implemented_but_marked_unknown += len(ops)
            else:
                truly_unknown += len(ops)
        except:
            pass
    else:
        extended_ascii_unknown += len(ops)

print(f"Opcodes implemented but marked 'unknown': {implemented_but_marked_unknown}")
print(f"  ACTION: Fix parser to return correct type field")
print()
print(f"Extended ASCII unknown: {extended_ascii_unknown}")
print(f"  ACTION: Add W2D version marker handler")
print()
print(f"Truly unknown opcodes: {truly_unknown}")
print(f"  ACTION: These are undocumented - treat as metadata")
print()

# Identify which opcodes are actually critical
print("CRITICAL FINDING:")
print()
if implemented_but_marked_unknown > 0:
    print(f"  {implemented_but_marked_unknown} opcodes are ALREADY IMPLEMENTED but being")
    print(f"  marked as 'unknown' due to incorrect type field in parser output!")
    print()
    print("  These opcodes ARE being parsed correctly, but the 'type' field")
    print("  in the returned dictionary doesn't match the expected values.")
    print()
    print("  FIX: Update parser functions to set correct 'type' field:")
    print("    - 0x03 should return type='set_color_rgba'")
    print("    - 0x17 should return type='line_weight'")
    print("    - 0x46 should return type='set_fill_on'")
    print("    - 0x56 should return type='set_visibility_on'")
    print("    - 0x63 should return type='color' or 'set_color_indexed'")

print()
print("=" * 80)
