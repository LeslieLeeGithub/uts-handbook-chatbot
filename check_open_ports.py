#!/usr/bin/env python3
"""
Check which processes are opening many ports.
"""

import subprocess
import sys
from collections import defaultdict


def get_port_info():
    """Get port information using lsof."""
    try:
        result = subprocess.run(
            ['lsof', '-i', '-P', '-n'],
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout
    except FileNotFoundError:
        print("❌ 'lsof' command not found. Please install it first.")
        return None


def analyze_ports():
    """Analyze which processes are opening the most ports."""
    output = get_port_info()
    if not output:
        return
    
    # Parse lsof output
    process_ports = defaultdict(set)
    process_info = {}
    
    for line in output.split('\n'):
        if not line.strip() or line.startswith('COMMAND'):
            continue
        
        parts = line.split()
        if len(parts) < 2:
            continue
        
        try:
            command = parts[0]
            pid = parts[1]
            
            # Find port information (usually in format like "127.0.0.1:PORT" or "*:PORT")
            for part in parts:
                if ':' in part and part.split(':')[-1].isdigit():
                    port = part.split(':')[-1]
                    process_ports[pid].add(port)
                    if pid not in process_info:
                        process_info[pid] = {
                            'command': command,
                            'full_line': ' '.join(parts[:9])  # First 9 parts usually contain useful info
                        }
        except (ValueError, IndexError):
            continue
    
    # Sort by number of ports
    sorted_processes = sorted(
        process_ports.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    print("🔍 Processes opening the most ports:")
    print("=" * 70)
    print(f"{'PID':<8} {'Ports':<8} {'Command':<30} {'Info'}")
    print("-" * 70)
    
    total_ports = 0
    for pid, ports in sorted_processes[:20]:  # Top 20
        info = process_info.get(pid, {})
        command = info.get('command', 'unknown')
        port_count = len(ports)
        total_ports += port_count
        
        # Check if it's Jupyter-related
        is_jupyter = 'jupyter' in command.lower() or 'ipython' in command.lower() or 'notebook' in command.lower()
        marker = "🔴" if is_jupyter else "  "
        
        print(f"{marker} {pid:<8} {port_count:<8} {command:<30} {info.get('full_line', '')[:50]}")
    
    print("-" * 70)
    print(f"📊 Total unique processes: {len(process_ports)}")
    print(f"📊 Total ports opened: {sum(len(ports) for ports in process_ports.values())}")
    
    # Check for Jupyter processes specifically
    jupyter_processes = []
    for pid, ports in sorted_processes:
        info = process_info.get(pid, {})
        command = info.get('command', '').lower()
        if 'jupyter' in command or 'ipython' in command or 'notebook' in command:
            jupyter_processes.append((pid, len(ports), info.get('full_line', '')))
    
    if jupyter_processes:
        print("\n🔴 Jupyter-related processes found:")
        print("-" * 70)
        for pid, port_count, info in jupyter_processes:
            print(f"   PID {pid}: {port_count} ports - {info}")
        print("\n💡 To kill these processes, run:")
        print("   ./kill_jupyter_processes.sh")
        print("   or")
        print("   pkill -f jupyter")
        print("   pkill -f ipython")


if __name__ == "__main__":
    analyze_ports()

