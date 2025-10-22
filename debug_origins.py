#!/usr/bin/env python3
"""
Debug script to examine set_origin opcodes
"""

import sys
from pathlib import Path
import json

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file

def main():
    print("Parsing drawing.w2d...")
    opcodes = parse_dwf_file("drawing.w2d")

    print("\n=== SET_ORIGIN OPCODES ===")
    for i, op in enumerate(opcodes):
        if op.get('type') == 'set_origin':
            print(f"\nOpcode {i}:")
            print(json.dumps(op, indent=2, default=str))

    print("\n\n=== FIRST 30 OPCODES (showing all types) ===")
    for i, op in enumerate(opcodes[:30]):
        opcode_type = op.get('type', 'NO TYPE')
        relative = op.get('relative', False)
        print(f"{i}: {opcode_type:30} relative={relative}")
        if opcode_type == 'set_origin':
            print(f"   origin: {op.get('origin')}")
        elif 'points' in op:
            print(f"   first point: {op['points'][0] if op['points'] else 'empty'}")

if __name__ == "__main__":
    main()
