#!/usr/bin/env python3
"""
DWF Orchestrator Version 2 - Independent Build
==============================================

This orchestrator dynamically imports all 44 agent modules and builds a
complete dispatch table for DWF opcode parsing. It supports all three
DWF opcode formats:

1. Single-byte binary opcodes (0x00-0xFF)
2. Extended ASCII opcodes starting with '('
3. Extended Binary opcodes starting with '{'

The orchestrator automatically discovers all opcode handler functions
from the agent modules without modifying them.

Author: Orchestrator V2 Builder
Date: 2025-10-22
"""

import sys
import os
import importlib
import inspect
import struct
from typing import Dict, Any, BinaryIO, Callable, Optional, List
from io import BytesIO


# =============================================================================
# AGENT MODULE DISCOVERY
# =============================================================================

def discover_agent_modules(agents_dir: str) -> List[str]:
    """
    Discover all agent module files in the agents directory.

    Args:
        agents_dir: Path to agents/agent_outputs directory

    Returns:
        List of agent module names (e.g., ['agent_01_opcode_0x6C', ...])
    """
    agent_files = []

    if not os.path.exists(agents_dir):
        raise FileNotFoundError(f"Agents directory not found: {agents_dir}")

    for filename in sorted(os.listdir(agents_dir)):
        if filename.startswith('agent_') and filename.endswith('.py'):
            module_name = filename[:-3]  # Remove .py extension
            agent_files.append(module_name)

    return agent_files


def import_agent_module(module_name: str, agents_dir: str):
    """
    Import an agent module dynamically.

    Args:
        module_name: Name of the module (e.g., 'agent_01_opcode_0x6C')
        agents_dir: Path to agents directory

    Returns:
        Imported module object
    """
    # Add agents directory to Python path if not already present
    if agents_dir not in sys.path:
        sys.path.insert(0, agents_dir)

    try:
        module = importlib.import_module(module_name)
        return module
    except Exception as e:
        print(f"Warning: Failed to import {module_name}: {e}")
        return None


# =============================================================================
# OPCODE HANDLER DISCOVERY
# =============================================================================

def discover_opcode_handlers(module) -> Dict[int, Callable]:
    """
    Discover all opcode handler functions in a module.

    Looks for functions matching these patterns:
    - opcode_0xXX_*
    - parse_opcode_0xXX_*
    - handle_opcode_0xXX_*
    - opcode_0xXX*

    Args:
        module: Imported agent module

    Returns:
        Dictionary mapping opcode byte to handler function
    """
    handlers = {}

    if module is None:
        return handlers

    for name, obj in inspect.getmembers(module):
        if not inspect.isfunction(obj):
            continue

        # Check for various naming patterns
        if name.startswith('opcode_0x') or name.startswith('parse_opcode_0x'):
            # Extract opcode hex value from function name
            # Pattern: opcode_0xXX_* or parse_opcode_0xXX_*
            parts = name.split('_')
            for part in parts:
                if part.startswith('0x'):
                    try:
                        opcode_value = int(part, 16)
                        if 0 <= opcode_value <= 0xFF:
                            handlers[opcode_value] = obj
                    except ValueError:
                        pass

        # Also check for patterns like opcode_0x0C_draw_line_16r
        elif 'opcode' in name.lower() and '0x' in name:
            try:
                # Find 0xXX pattern in name
                idx = name.find('0x')
                if idx >= 0:
                    hex_str = name[idx:idx+4]  # Get 0xXX
                    if len(hex_str) == 4:
                        opcode_value = int(hex_str, 16)
                        if 0 <= opcode_value <= 0xFF:
                            handlers[opcode_value] = obj
            except (ValueError, IndexError):
                pass

    return handlers


def discover_extended_ascii_handlers(module) -> Dict[str, Callable]:
    """
    Discover Extended ASCII opcode handlers (opcodes starting with '(').

    These handlers parse opcodes like (Author "..."), (Title "..."), etc.

    Args:
        module: Imported agent module

    Returns:
        Dictionary mapping opcode name to handler function
    """
    handlers = {}

    if module is None:
        return handlers

    # Look for handler classes or functions that deal with Extended ASCII
    for name, obj in inspect.getmembers(module):
        # Check for metadata opcode classes (like AuthorOpcode, TitleOpcode)
        if inspect.isclass(obj) and 'Opcode' in name:
            # Check if it has OPCODE_NAME attribute
            if hasattr(obj, 'OPCODE_NAME'):
                opcode_name = obj.OPCODE_NAME
                handlers[opcode_name] = obj

        # Check for parse functions
        elif inspect.isfunction(obj):
            if 'parse_dwf_header' in name:
                handlers['DWF V'] = obj
                handlers['W2D V'] = obj
            elif 'parse_end_of_dwf' in name:
                handlers['EndOfDWF'] = obj
            elif 'parse_viewport' in name:
                handlers['Viewport'] = obj
            elif 'parse_view' in name and 'viewport' not in name:
                handlers['View'] = obj
            elif 'parse_named_view' in name:
                handlers['NamedView'] = obj

    return handlers


def discover_extended_binary_handlers(module) -> Dict[int, Callable]:
    """
    Discover Extended Binary opcode handlers (opcodes starting with '{').

    These handlers parse opcodes in format: {Size(4)Opcode(2)Data}

    Args:
        module: Imported agent module

    Returns:
        Dictionary mapping opcode ID to handler function
    """
    handlers = {}

    if module is None:
        return handlers

    for name, obj in inspect.getmembers(module):
        if not inspect.isfunction(obj):
            continue

        # Check for extended binary patterns
        if 'exbo' in name.lower() or 'extended_binary' in name.lower():
            # Try to extract opcode value from function name or docstring
            if 'encryption' in name.lower():
                handlers[0x0027] = obj  # WD_EXBO_ENCRYPTION
            elif 'password' in name.lower():
                handlers[331] = obj  # WD_EXBO_PASSWORD
            elif 'unknown' in name.lower():
                handlers['unknown'] = obj  # Fallback handler

    return handlers


# =============================================================================
# DISPATCH TABLE BUILDER
# =============================================================================

class DWFOpcodeDispatcher:
    """
    Main dispatcher for all DWF opcodes across all formats.

    Builds and manages dispatch tables for:
    - Single-byte binary opcodes (0x00-0xFF)
    - Extended ASCII opcodes (starting with '(')
    - Extended Binary opcodes (starting with '{')
    """

    def __init__(self, agents_dir: str):
        """
        Initialize dispatcher by scanning all agent modules.

        Args:
            agents_dir: Path to agents/agent_outputs directory
        """
        self.agents_dir = agents_dir
        self.binary_handlers: Dict[int, Callable] = {}
        self.extended_ascii_handlers: Dict[str, Callable] = {}
        self.extended_binary_handlers: Dict[int, Callable] = {}
        self.agent_modules = []

        self._build_dispatch_tables()

    def _build_dispatch_tables(self):
        """Build dispatch tables by scanning all agent modules."""
        print(f"Scanning agents directory: {self.agents_dir}")

        # Discover all agent modules
        agent_names = discover_agent_modules(self.agents_dir)
        print(f"Found {len(agent_names)} agent modules")

        # Import each agent and extract handlers
        for agent_name in agent_names:
            module = import_agent_module(agent_name, self.agents_dir)
            if module:
                self.agent_modules.append(module)

                # Discover binary opcode handlers
                binary_handlers = discover_opcode_handlers(module)
                self.binary_handlers.update(binary_handlers)

                # Discover Extended ASCII handlers
                ascii_handlers = discover_extended_ascii_handlers(module)
                self.extended_ascii_handlers.update(ascii_handlers)

                # Discover Extended Binary handlers
                ext_binary_handlers = discover_extended_binary_handlers(module)
                self.extended_binary_handlers.update(ext_binary_handlers)

        print(f"Built dispatch tables:")
        print(f"  - Binary opcodes: {len(self.binary_handlers)} handlers")
        print(f"  - Extended ASCII opcodes: {len(self.extended_ascii_handlers)} handlers")
        print(f"  - Extended Binary opcodes: {len(self.extended_binary_handlers)} handlers")

    def dispatch_binary_opcode(self, opcode: int, stream: BinaryIO) -> Optional[Dict[str, Any]]:
        """
        Dispatch a single-byte binary opcode to its handler.

        Args:
            opcode: Opcode byte value (0x00-0xFF)
            stream: Binary stream positioned after opcode byte

        Returns:
            Parsed result dictionary, or None if no handler found
        """
        handler = self.binary_handlers.get(opcode)
        if handler:
            try:
                return handler(stream)
            except Exception as e:
                print(f"Error parsing opcode 0x{opcode:02X}: {e}")
                return {'type': 'error', 'opcode': opcode, 'error': str(e)}

        return None

    def dispatch_extended_ascii(self, stream: BinaryIO) -> Optional[Dict[str, Any]]:
        """
        Dispatch an Extended ASCII opcode to its handler.

        Args:
            stream: Binary stream positioned at '('

        Returns:
            Parsed result dictionary, or None if no handler found
        """
        # Save position to backtrack if needed
        start_pos = stream.tell()

        try:
            # Try to parse opcode name
            stream.read(1)  # Read '('

            # Read opcode name (until whitespace or delimiter)
            name_chars = []
            while True:
                byte = stream.read(1)
                if not byte:
                    break
                char = chr(byte[0])
                if char in ' \t\n\r()':
                    stream.seek(-1, 1)  # Put back delimiter
                    break
                name_chars.append(char)

            opcode_name = ''.join(name_chars)

            # Reset to start
            stream.seek(start_pos)

            # Look for exact match
            handler = self.extended_ascii_handlers.get(opcode_name)
            if handler:
                try:
                    # Handler might be a class or function
                    if inspect.isclass(handler):
                        # Instantiate and materialize
                        instance = handler()
                        instance.materialize(stream)
                        return instance.to_dict() if hasattr(instance, 'to_dict') else {'value': instance.value}
                    else:
                        # Call function
                        return handler(stream)
                except Exception as e:
                    print(f"Error parsing Extended ASCII opcode '{opcode_name}': {e}")
                    return {'type': 'error', 'opcode': opcode_name, 'error': str(e)}

            # Try prefix matching (for Comments opcode)
            for prefix, handler in self.extended_ascii_handlers.items():
                if opcode_name.startswith(prefix):
                    try:
                        if inspect.isclass(handler):
                            instance = handler()
                            instance.materialize(stream)
                            return instance.to_dict() if hasattr(instance, 'to_dict') else {'value': instance.value}
                        else:
                            return handler(stream)
                    except Exception as e:
                        print(f"Error parsing Extended ASCII opcode '{opcode_name}': {e}")
                        return {'type': 'error', 'opcode': opcode_name, 'error': str(e)}

            return None

        except Exception as e:
            stream.seek(start_pos)
            return None

    def dispatch_extended_binary(self, stream: BinaryIO) -> Optional[Dict[str, Any]]:
        """
        Dispatch an Extended Binary opcode to its handler.

        Args:
            stream: Binary stream positioned at '{'

        Returns:
            Parsed result dictionary, or None if no handler found
        """
        # Save position
        start_pos = stream.tell()

        try:
            # Read header: {(1) + Size(4) + Opcode(2)
            stream.read(1)  # Read '{'

            # Read size
            size_bytes = stream.read(4)
            if len(size_bytes) != 4:
                stream.seek(start_pos)
                return None
            size = struct.unpack('<I', size_bytes)[0]

            # Read opcode
            opcode_bytes = stream.read(2)
            if len(opcode_bytes) != 2:
                stream.seek(start_pos)
                return None
            opcode_value = struct.unpack('<H', opcode_bytes)[0]

            # Reset to start
            stream.seek(start_pos)

            # Dispatch to handler
            handler = self.extended_binary_handlers.get(opcode_value)
            if not handler:
                handler = self.extended_binary_handlers.get('unknown')

            if handler:
                try:
                    return handler(stream)
                except Exception as e:
                    print(f"Error parsing Extended Binary opcode 0x{opcode_value:04X}: {e}")
                    return {'type': 'error', 'opcode': opcode_value, 'error': str(e)}

            return None

        except Exception as e:
            stream.seek(start_pos)
            return None

    def get_dispatch_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the dispatch tables.

        Returns:
            Dictionary with statistics
        """
        return {
            'agent_modules': len(self.agent_modules),
            'binary_opcodes': len(self.binary_handlers),
            'binary_opcode_list': sorted([f"0x{op:02X}" for op in self.binary_handlers.keys()]),
            'extended_ascii_opcodes': len(self.extended_ascii_handlers),
            'extended_ascii_list': sorted(self.extended_ascii_handlers.keys()),
            'extended_binary_opcodes': len(self.extended_binary_handlers),
            'extended_binary_list': sorted([f"0x{op:04X}" if isinstance(op, int) else op
                                           for op in self.extended_binary_handlers.keys()])
        }


# =============================================================================
# DWF FILE PARSER
# =============================================================================

def parse_dwf_file(file_path: str, max_opcodes: int = 1000) -> List[Dict[str, Any]]:
    """
    Parse a DWF file and extract all opcodes.

    This function reads a DWF file and dispatches each opcode to its
    appropriate handler based on the opcode format:
    - Single-byte binary: 0x00-0xFF
    - Extended ASCII: starts with '('
    - Extended Binary: starts with '{'

    Args:
        file_path: Path to DWF file
        max_opcodes: Maximum number of opcodes to parse (safety limit)

    Returns:
        List of parsed opcode results
    """
    # Get agents directory (relative to this file)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    agents_dir = os.path.join(project_dir, 'agents', 'agent_outputs')

    # Initialize dispatcher
    dispatcher = DWFOpcodeDispatcher(agents_dir)

    results = []

    with open(file_path, 'rb') as f:
        opcode_count = 0

        while opcode_count < max_opcodes:
            # Read next byte to determine opcode type
            byte = f.read(1)
            if not byte:
                break  # EOF

            byte_val = byte[0]

            if byte_val == ord('('):
                # Extended ASCII opcode
                f.seek(-1, 1)  # Put byte back
                result = dispatcher.dispatch_extended_ascii(f)
                if result:
                    results.append(result)
                else:
                    # Unknown Extended ASCII opcode, skip to closing paren
                    depth = 1
                    while depth > 0:
                        b = f.read(1)
                        if not b:
                            break
                        if b == b'(':
                            depth += 1
                        elif b == b')':
                            depth -= 1
                    results.append({'type': 'unknown_ascii', 'skipped': True})

            elif byte_val == ord('{'):
                # Extended Binary opcode
                f.seek(-1, 1)  # Put byte back
                result = dispatcher.dispatch_extended_binary(f)
                if result:
                    results.append(result)
                else:
                    # Unknown Extended Binary, try to skip
                    results.append({'type': 'unknown_binary', 'skipped': True})

            else:
                # Single-byte binary opcode
                result = dispatcher.dispatch_binary_opcode(byte_val, f)
                if result:
                    result['opcode_byte'] = f"0x{byte_val:02X}"
                    results.append(result)
                else:
                    # Unknown opcode
                    results.append({'type': 'unknown', 'opcode': f"0x{byte_val:02X}"})

            opcode_count += 1

            # Check for end of stream marker
            if result and result.get('type') == 'end_of_stream':
                break

    return results


# =============================================================================
# MAIN TEST
# =============================================================================

def main():
    """Test the DWF Orchestrator V2 by building dispatch tables."""
    print("=" * 70)
    print("DWF Orchestrator Version 2 - Independent Build")
    print("=" * 70)
    print()

    # Get agents directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    agents_dir = os.path.join(project_dir, 'agents', 'agent_outputs')

    print(f"Project directory: {project_dir}")
    print(f"Agents directory: {agents_dir}")
    print()

    # Initialize dispatcher
    dispatcher = DWFOpcodeDispatcher(agents_dir)

    # Print statistics
    print()
    print("=" * 70)
    print("Dispatch Table Statistics")
    print("=" * 70)

    stats = dispatcher.get_dispatch_stats()

    print(f"\nAgent Modules Loaded: {stats['agent_modules']}")
    print(f"\nBinary Opcodes ({stats['binary_opcodes']} total):")
    for i in range(0, len(stats['binary_opcode_list']), 10):
        print(f"  {', '.join(stats['binary_opcode_list'][i:i+10])}")

    print(f"\nExtended ASCII Opcodes ({stats['extended_ascii_opcodes']} total):")
    for opcode in stats['extended_ascii_list']:
        print(f"  - {opcode}")

    print(f"\nExtended Binary Opcodes ({stats['extended_binary_opcodes']} total):")
    for opcode in stats['extended_binary_list']:
        print(f"  - {opcode}")

    # Test parsing a simple opcode stream
    print()
    print("=" * 70)
    print("Test: Parsing Sample Opcode Stream")
    print("=" * 70)
    print()

    # Create a test stream with a few opcodes
    test_stream = BytesIO()

    # Add 0x00 (NOP)
    test_stream.write(b'\x00')

    # Add 0x01 (STREAM_VERSION) - version 6.2
    test_stream.write(b'\x01')
    version = (6 << 8) | 2
    test_stream.write(struct.pack('<H', version))

    # Add 0x6C (binary line) - line from (100,200) to (300,400)
    test_stream.write(b'\x6C')
    test_stream.write(struct.pack('<llll', 100, 200, 300, 400))

    # Add 0xFF (END_OF_STREAM)
    test_stream.write(b'\xFF')

    # Reset stream position
    test_stream.seek(0)

    # Parse the stream
    print("Parsing test stream with 4 opcodes...")
    results = []
    opcode_num = 0

    while True:
        byte = test_stream.read(1)
        if not byte:
            break

        byte_val = byte[0]
        result = dispatcher.dispatch_binary_opcode(byte_val, test_stream)

        if result:
            opcode_num += 1
            result['opcode_byte'] = f"0x{byte_val:02X}"
            results.append(result)
            print(f"  Opcode #{opcode_num}: 0x{byte_val:02X} -> {result.get('type', 'unknown')}")

            if result.get('type') == 'end_of_stream':
                break

    print(f"\nSuccessfully parsed {len(results)} opcodes")

    print()
    print("=" * 70)
    print("DWF Orchestrator V2 - Build Complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Loaded {stats['agent_modules']} agent modules")
    print(f"  - Discovered {stats['binary_opcodes']} binary opcode handlers")
    print(f"  - Discovered {stats['extended_ascii_opcodes']} Extended ASCII handlers")
    print(f"  - Discovered {stats['extended_binary_opcodes']} Extended Binary handlers")
    print(f"  - Successfully parsed test stream with {len(results)} opcodes")
    print()
    print("The orchestrator is ready to parse DWF files!")
    print()


if __name__ == '__main__':
    main()
