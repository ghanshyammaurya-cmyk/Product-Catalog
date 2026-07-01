"""
Run automation tests from this file (do NOT run conftest.py directly).

Examples:
    python run_tests.py
    python run_tests.py --headed
    python run_tests.py --headed --slow-mo 800
    python run_tests.py -m smoke
    python run_tests.py tests/test_partner_spotlight.py -v
"""
import os
import sys

# Project root on path
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
  import pytest

  # Default args; pass extra flags after run_tests.py
  # e.g. python run_tests.py --headed -v
  default_args = [
    ROOT,
    "-v",
    "--tb=short",
    "--reruns",
    "0",
  ]

  user_args = sys.argv[1:]

  # Shortcut: python run_tests.py visual
  if user_args and user_args[0].lower() == "visual":
    user_args = ["--headed", "--slow-mo", "600"] + user_args[1:]

  exit_code = pytest.main(default_args + user_args)
  sys.exit(exit_code)


if __name__ == "__main__":
  main()
