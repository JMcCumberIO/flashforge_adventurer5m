"""Run the test suite with different configurations.

Tests requiring a physical printer are kept local-only and excluded from the
repository. This script runs whatever tests are present; exit code 5
(no tests collected) is treated as success in CI.
"""
import argparse
import subprocess
import sys

# pytest exit codes
EXIT_OK = 0
EXIT_TESTS_FAILED = 1
EXIT_NO_TESTS = 5  # No tests collected — treated as success in CI


def build_pytest_cmd(config: str, coverage: bool) -> list:
    cmd = [sys.executable, "-m", "pytest"]

    if coverage:
        cmd += ["--cov=.", "--cov-report=xml", "--cov-report=term-missing"]

    if config == "quick":
        cmd += ["-x", "--tb=short", "-q"]
    elif config == "full":
        cmd += ["--tb=short", "-v"]
    elif config == "performance":
        cmd += ["--tb=short", "-v", "-m", "performance"]
    elif config == "stress":
        cmd += ["--tb=short", "-v", "-m", "stress"]

    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Flashforge test suite")
    parser.add_argument(
        "--config",
        default="quick",
        choices=["quick", "full", "performance", "stress"],
        help="Test configuration to run",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Collect coverage data"
    )
    args = parser.parse_args()

    cmd = build_pytest_cmd(args.config, args.coverage)
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    rc = result.returncode

    if rc == EXIT_NO_TESTS:
        print("No tests collected — skipping (tests require a physical printer).")
        sys.exit(EXIT_OK)

    sys.exit(rc)


if __name__ == "__main__":
    main()
