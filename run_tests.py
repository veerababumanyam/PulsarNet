#!/usr/bin/env python3
"""Script to run tests with code coverage for PulsarNet.

This script provides a convenient way to run all unit and integration tests
for the PulsarNet application with code coverage reporting.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for PulsarNet")
    
    parser.add_argument(
        "--with-coverage",
        action="store_true",
        help="Run tests with code coverage"
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Generate XML coverage report"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests"
    )
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug output"
    )
    
    return parser.parse_args()


def run_tests(args):
    """Run the tests based on the provided arguments."""
    # Prepare test command
    test_cmd = ["python", "-m", "pytest"]
    
    # Add coverage if requested
    if args.with_coverage:
        test_cmd.extend([
            "--cov=pulsarnet",
            "--cov-report=term"
        ])
        
        if args.html:
            test_cmd.append("--cov-report=html")
        
        if args.xml:
            test_cmd.append("--cov-report=xml")
    
    # Configure test selection
    if args.unit and not args.integration:
        test_cmd.append("tests/unit")
    elif args.integration and not args.unit:
        test_cmd.append("tests/integration")
    else:
        test_cmd.append("tests")
    
    # Add verbosity if debug enabled
    if args.debug:
        test_cmd.append("-v")
    
    # Print command being run
    print(f"Running command: {' '.join(test_cmd)}")
    
    # Run the tests
    try:
        result = subprocess.run(test_cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running tests: {e}")
        return e.returncode


def main():
    """Main entry point for the test runner."""
    args = parse_args()
    
    # If no test type specified, run all
    if not args.unit and not args.integration:
        args.unit = True
        args.integration = True
    
    # Create any necessary directories
    if args.html:
        os.makedirs("htmlcov", exist_ok=True)
    
    # Run tests
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main()) 