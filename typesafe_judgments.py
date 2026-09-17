"""Optional TypeSafe-backed judgments for status text this printer's firmware
doesn't document in a stable, parseable format.

This module is entirely opt-in. Every function here degrades to returning
None when no API key is configured, so callers must already have a legacy
fallback path -- this never becomes a hard dependency for users who don't
want a third-party API call in their update loop.

Background (see coordinator.py's endstop-parsing comments and the project's
own issue tracker): the Adventurer 5M / 5M Pro's M119 response is a
free-text, undocumented blob that doesn't match the Marlin-style
"x_min:open" keys a naive parser expects, and the exact wording used when an
endstop or the filament sensor actually trips has never been captured. A
keyword parser can't be correct against a format nobody has fully seen. A
semantic judgment can still reason about the text that IS there.

Similarly, matching the printer's self-reported "currently printing"
filename against the known list of printable files is a fuzzy string
problem (prefix differences, `/data/` inclusion, truncation) rather than an
exact-lookup problem -- a good fit for Choice's candidate-selection pattern
rather than a bidirectional endswith() heuristic.
"""
from __future__ import annotations

import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)

try:
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

    _TYPESAFE_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when the optional dep isn't installed
    _TYPESAFE_AVAILABLE = False

# Noul returns a probability, not a boolean. This is the cut point at which
# we treat "probably triggered" as triggered. 0.5 is the natural default
# (more-likely-than-not); raise it if false positives matter more than
# false negatives for a given install, e.g. if this ever drives an
# automation that pauses a print.
ENDSTOP_TRIGGERED_THRESHOLD = 0.5

_ENDSTOP_QUESTION = (
    "Based on the M119 status text in `m119_response`, is the {axis} endstop "
    "currently triggered/activated (as opposed to open, at rest, or simply "
    "not reported)?"
)
_FILAMENT_QUESTION = (
    "Based on the M119 status text in `m119_response`, does it indicate the "
    "filament runout/presence sensor is triggered (filament out or sensor "
    "activated)? If the text doesn't mention a filament sensor at all, "
    "answer with low probability."
)


async def judge_endstop_status(
    api_key: Optional[str], m119_response: str
) -> Optional[dict[str, bool]]:
    """Ask TypeSafe to interpret a raw M119 response.

    Returns a dict with keys x/y/z/filament -> bool, or None if TypeSafe
    isn't configured/available or the call fails. Callers should fall back
    to the legacy keyword parser on None, not treat it as "all clear".
    """
    if not api_key or not _TYPESAFE_AVAILABLE:
        return None

    try:
        async with AsyncTypeSafeClient(api_key=api_key) as client:
            response = await client.system_one(
                state={"m119_response": m119_response},
                questions={
                    "x": Noul(instructions=_ENDSTOP_QUESTION.format(axis="X-axis")),
                    "y": Noul(instructions=_ENDSTOP_QUESTION.format(axis="Y-axis")),
                    "z": Noul(instructions=_ENDSTOP_QUESTION.format(axis="Z-axis")),
                    "filament": Noul(instructions=_FILAMENT_QUESTION),
                },
            )
    except Exception as e:  # noqa: BLE001 - any SDK/network failure just means "no judgment"
        _LOGGER.warning("TypeSafe endstop judgment failed, falling back to legacy parsing: %s", e)
        return None

    answers = response.answers
    return {
        axis: answers[axis].noul >= ENDSTOP_TRIGGERED_THRESHOLD
        for axis in ("x", "y", "z", "filament")
    }


async def judge_current_print_file(
    api_key: Optional[str], reported_filename: str, candidate_paths: list[str]
) -> Optional[str]:
    """Ask TypeSafe which candidate path matches the printer-reported filename.

    Returns the matched candidate path, or None (either "genuinely no
    match" per the model, or TypeSafe unavailable/failed -- callers should
    fall back to the legacy endswith() heuristic in the latter case, same
    as judge_endstop_status).
    """
    if not api_key or not _TYPESAFE_AVAILABLE or not candidate_paths:
        return None

    criteria = {str(i): path for i, path in enumerate(candidate_paths)}
    criteria["no_match"] = (
        "None of the listed paths refer to the same file as the reported filename"
    )

    try:
        async with AsyncTypeSafeClient(api_key=api_key) as client:
            response = await client.system_one(
                state={
                    "reported_filename": reported_filename,
                    "candidate_paths": candidate_paths,
                },
                questions={
                    "match": Choice(
                        instructions=(
                            "The printer reports it is currently printing "
                            "`reported_filename`. Which entry in `candidate_paths` "
                            "(by its option key) refers to the exact same file, "
                            "accounting for path prefixes, formatting differences, "
                            "or truncation? If none genuinely match, choose no_match."
                        ),
                        criteria=criteria,
                    ),
                },
            )
    except Exception as e:  # noqa: BLE001
        _LOGGER.warning("TypeSafe file-match judgment failed, falling back to legacy matching: %s", e)
        return None

    choice = response.answers["match"].choice
    if choice == "no_match":
        return None
    return candidate_paths[int(choice)]
