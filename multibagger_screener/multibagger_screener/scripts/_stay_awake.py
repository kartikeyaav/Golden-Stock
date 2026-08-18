"""
scripts/_stay_awake.py — keep Windows from sleeping through a long local AI run.

WHY THIS EXISTS (2026-08-18). Both laptop-side AI jobs were being killed by the
machine sleeping mid-run, and neither failure looked like what it was:

  - the nightly analyst (2026-08-18) started at 05:02 and its 2400s timeout
    fired at 13:57 — ~9 hours of wall clock, because subprocess timeouts count
    suspended time. The log read "timed out", which points at a slow dive.
  - the weekly committee (2026-08-12) died with exit 0xC000013A
    (STATUS_CONTROL_C_EXIT) 40 seconds into a 3-hour budget. That reads like a
    crash; it was the OS tearing the process down on suspend.

Task Scheduler's "wake the computer to run this task" only covers the START of
a task, not the hours after it. So the request has to come from inside the
running process: SetThreadExecutionState with ES_CONTINUOUS tells Windows a
job is in flight until the flag is cleared. ES_DISPLAY_REQUIRED is deliberately
NOT set — the screen should still go dark on a laptop closed for the night.

Best-effort by design: a failed call logs and continues rather than aborting a
research run over a power hint. No-op on non-Windows (the cloud never runs
these wrappers, but the test suite imports them).

    with stay_awake(log):
        ... long AI subprocess ...
"""

from __future__ import annotations

import contextlib
import sys
from typing import Callable, Iterator

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


@contextlib.contextmanager
def stay_awake(log: Callable[[str], None] | None = None) -> Iterator[bool]:
    """Hold off system sleep for the duration of the block. Yields True if the
    request was actually granted, so callers can say so in their log."""
    def _say(msg: str) -> None:
        if log:
            log(msg)

    if not sys.platform.startswith("win"):
        yield False
        return

    held = False
    try:
        import ctypes
        # returns the PREVIOUS state, or 0 on failure
        if ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED) != 0:
            held = True
        else:
            _say("sleep-guard NOT held (SetThreadExecutionState refused) — "
                 "a suspend mid-run can still kill this job")
    except Exception as e:  # noqa: BLE001 — never fail a run over a power hint
        _say(f"sleep-guard unavailable ({str(e)[:80]})")

    try:
        yield held
    finally:
        if held:
            try:
                import ctypes
                # clear the flag — leaving it set would keep the machine awake
                # forever, which is worse than the bug being fixed
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except Exception as e:  # noqa: BLE001
                _say(f"sleep-guard release failed ({str(e)[:80]})")
