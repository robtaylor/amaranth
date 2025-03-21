#!/usr/bin/env python3
"""
Script to test all tutorial code examples in the docs/_code directory.
"""

import os
import sys
import subprocess
import time

# List of tutorial example files to test
# Exclude VCD and GTKW files, as well as generated Verilog
EXAMPLES = [
    "and_gate.py",
    "blinky.py",
    "controlled_blinker.py", 
    "led_blinker.py",
    "program_icestick.py",
    "uart_receiver.py",
    "uart_sim.py",
    "up_counter.py"
]

# Track results
results = {
    "passed": [],
    "failed": []
}

# Get current directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Check if this is a CI environment
is_ci = os.environ.get("CI", "false").lower() == "true"

def print_header(text):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70 + "\n")

def run_example(filename):
    """Run a Python example file and return True if it succeeds."""
    print(f"Testing {filename}...")
    
    full_path = os.path.join(script_dir, filename)
    
    # Use 'pdm run python' to run the example
    cmd = ["pdm", "run", "python", full_path]
    
    # Add --test flag for hardware-dependent examples
    if filename in ["led_blinker.py", "program_icestick.py"]:
        cmd.append("--test")
    
    try:
        # Set a timeout for each example
        timeout = 30
        
        # Run the example
        start_time = time.time()
        process = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        # Check if the process completed successfully
        if process.returncode == 0:
            print(f"✅ {filename} passed in {duration:.2f}s")
            return True, None
        else:
            error_msg = process.stderr or "Unknown error"
            print(f"❌ {filename} failed in {duration:.2f}s")
            print(f"Error: {error_msg}")
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        print(f"❌ {filename} timed out after {timeout}s")
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        print(f"❌ {filename} failed with exception: {str(e)}")
        return False, str(e)

def main():
    print_header("TESTING AMARANTH TUTORIAL EXAMPLES")
    
    # Run each example
    for example in EXAMPLES:
        success, error = run_example(example)
        if success:
            results["passed"].append(example)
        else:
            results["failed"].append((example, error))
    
    # Print summary
    print_header("TEST SUMMARY")
    print(f"Total examples: {len(EXAMPLES)}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results["failed"]:
        print("\nFailed examples:")
        for example, error in results["failed"]:
            print(f" - {example}: {error}")
        return 1
    else:
        print("\nAll examples passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())