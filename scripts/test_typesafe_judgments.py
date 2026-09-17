"""Manual probe for the TypeSafe-backed endstop and print-file judgments.

Standalone script (only needs typesafe-sdk installed, no Home Assistant or
repo imports) so it can be run independently to sanity-check the judgments
in typesafe_judgments.py after any prompt-wording change, without needing a
live printer connection.

The M119 and M661 fixtures below are real captures taken directly from a
live Adventurer 5M Pro (2026-09-16, idle/READY, nothing printing) -- not
synthesized examples. There is deliberately no "endstop actually triggered"
fixture: nobody has captured that state yet (see coordinator.py's own
comments on the M119 parsing gap), which is part of why a keyword parser
can't be verified correct either way, and part of the case for a semantic
judgment that can still reason sensibly about the states we do have
captures for.

Usage:
    export TYPESAFE_API_KEY=...
    python scripts/test_typesafe_judgments.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typesafe_judgments import judge_current_print_file, judge_endstop_status

# Real M119 response, captured live, printer idle/READY, nothing triggered.
M119_IDLE = (
    "CMD M119 Received.\r\n"
    "Endstop: X-max: 110 Y-max: 110 Z-min: 0\r\n"
    "MachineStatus: READY\r\n"
    "MoveMode: READY\r\n"
    "Status: S:1 L:0 J:0 F:0\r\n"
    "LED: 1\r\n"
    "CurrentFile: \r\n"
    "ok\r\n"
)

# A subset of real file paths from this printer's actual M661 response.
CANDIDATE_PATHS = [
    "/data/adv_5m_pro_tool_holder_v2_ready_to_ptint_PLA_2h5m.gcode.3mf",
    "/data/kangaroo_omni_lockbox_v7_PLA_11h39m.gcode.3mf",
    "/data/kangaroo_omni_lockbox_v6_PLA_16m29s_20Percent_Test.gcode.3mf",
    "/data/laptop_stand_PLA_1h33m.gcode.3mf",
    "/data/3DBenchy.gcode",
    "/data/Christmas_Ornament_-_Snowflakex3.gcode",
    "/data/Christmas_Ornament_-_Snowflake.gcode",
]

# A realistic printer-reported filename: short form, no /data/ prefix. This
# is exactly the shape the old bidirectional endswith() heuristic in
# select.py handled by luck rather than by design -- and where it's most at
# risk of matching the wrong candidate when two paths share a long prefix
# (compare the two "kangaroo_omni_lockbox" and two "Christmas_Ornament -
# Snowflake*" entries above).
REPORTED_FILENAME = "kangaroo_omni_lockbox_v7_PLA_11h39m.gcode.3mf"
EXPECTED_MATCH = "/data/kangaroo_omni_lockbox_v7_PLA_11h39m.gcode.3mf"


async def main() -> int:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        print("TYPESAFE_API_KEY not set in environment.", file=sys.stderr)
        return 1

    print("=== Endstop judgment (real idle M119 capture) ===")
    result = await judge_endstop_status(api_key, M119_IDLE)
    if result is None:
        print("FAIL: judge_endstop_status returned None (check API key / SDK install)")
        return 1
    print(f"  x={result['x']} y={result['y']} z={result['z']} filament={result['filament']}")
    # Sanity assertions for the one real fixture available: the printer is
    # idle with no filament-sensor mention in the text at all, so X/Y/filament
    # should read as "not triggered". Z is genuinely ambiguous in this text
    # ("Z-min: 0" could be a travel limit or a real trigger) and isn't
    # asserted either way -- see the module docstring.
    assert result["x"] is False, f"expected X not-triggered on idle capture, got {result['x']}"
    assert result["y"] is False, f"expected Y not-triggered on idle capture, got {result['y']}"
    assert result["filament"] is False, f"expected filament not-triggered (unmentioned), got {result['filament']}"
    print("  OK: X/Y/filament read as not-triggered on the idle capture, as expected")

    print()
    print("=== Print-file matching judgment (real M661 file list) ===")
    match = await judge_current_print_file(api_key, REPORTED_FILENAME, CANDIDATE_PATHS)
    print(f"  reported='{REPORTED_FILENAME}' -> matched='{match}'")
    assert match == EXPECTED_MATCH, f"expected {EXPECTED_MATCH!r}, got {match!r}"
    print("  OK: matched the correct candidate despite the shared-prefix decoys")

    print()
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
