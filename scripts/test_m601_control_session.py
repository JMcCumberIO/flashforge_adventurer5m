"""Manual probe for the FlashForge M601/M602 TCP control-session handshake.

Standalone script (stdlib only, no Home Assistant or repo imports) so it can
run against a real printer independently of the integration.

Background
----------
The integration's TCP client (flashforge_tcp.py) opens a fresh connection,
sends one command, reads the response, and closes -- for every single
M-code. It never sends `~M601 S1` (request control) or `~M602` (release
control). Some reverse-engineered FlashForge documentation describes M601 as
required on newer firmware before most commands are accepted, and M602 as
required before disconnecting. If that's true for this printer's firmware,
every command the integration sends could be silently degraded or rejected.

This script sends a handful of read-only, non-destructive commands in three
different session patterns and prints the raw responses so a human can
compare them:

  A) No handshake, one fresh connection per command (mirrors exactly what
     the integration does today).
  B) Persistent connection: M601 S1 once, several commands, then M602.
  C) Fresh connection per command, but M601 S1 sent immediately before the
     real command on *each* connection (in case the control session is
     scoped per-TCP-connection rather than per-printer).

Only read-only/query commands are used (M115, M119, M105, M27). Nothing here
moves an axis, changes a setpoint, or starts/cancels a print.

Usage:
    python scripts/test_m601_control_session.py --host 192.168.1.50
    python scripts/test_m601_control_session.py --host 192.168.1.50 --port 8899
"""

import argparse
import socket
import sys
import time

DEFAULT_PORT = 8899
DEFAULT_TIMEOUT = 5.0
RESPONSE_TERMINATOR = "ok\r\n"

# Read-only commands used for probing. None of these change printer state.
PROBE_COMMANDS = ["M115", "M119", "M105", "M27"]


def send_on_connection(sock: socket.socket, command: str, timeout: float) -> str:
    """Send one command on an already-open socket and read the response.

    Args:
        sock: An open, connected TCP socket.
        command: Bare command without ``~`` prefix or ``\\r\\n`` suffix.
        timeout: Per-read timeout in seconds.

    Returns:
        The decoded response text (stripped), possibly empty on timeout.
    """
    payload = f"~{command}\r\n".encode("utf-8")
    sock.sendall(payload)

    sock.settimeout(timeout)
    buf = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(1024)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
        if RESPONSE_TERMINATOR.encode("utf-8") in buf:
            break
    return buf.decode("utf-8", errors="ignore").strip()


def new_connection(host: str, port: int, timeout: float) -> socket.socket:
    """Open a new TCP connection to the printer."""
    sock = socket.create_connection((host, port), timeout=timeout)
    return sock


def run_pattern_a(host: str, port: int, timeout: float) -> list[tuple[str, str]]:
    """Pattern A: fresh connection per command, no M601/M602 (current behavior)."""
    results = []
    for cmd in PROBE_COMMANDS:
        sock = new_connection(host, port, timeout)
        try:
            resp = send_on_connection(sock, cmd, timeout)
        finally:
            sock.close()
        results.append((cmd, resp))
    return results


def run_pattern_b(host: str, port: int, timeout: float) -> list[tuple[str, str]]:
    """Pattern B: one persistent connection, M601 once, commands, then M602."""
    results = []
    sock = new_connection(host, port, timeout)
    try:
        results.append(("M601 S1", send_on_connection(sock, "M601 S1", timeout)))
        for cmd in PROBE_COMMANDS:
            results.append((cmd, send_on_connection(sock, cmd, timeout)))
        results.append(("M602", send_on_connection(sock, "M602", timeout)))
    finally:
        sock.close()
    return results


def run_pattern_c(host: str, port: int, timeout: float) -> list[tuple[str, str]]:
    """Pattern C: fresh connection per command, M601 sent first on each connection."""
    results = []
    for cmd in PROBE_COMMANDS:
        sock = new_connection(host, port, timeout)
        try:
            send_on_connection(sock, "M601 S1", timeout)
            resp = send_on_connection(sock, cmd, timeout)
        finally:
            sock.close()
        results.append((cmd, resp))
    return results


def print_results(title: str, results: list[tuple[str, str]]) -> None:
    print(f"\n=== {title} ===")
    for cmd, resp in results:
        flag = ""
        lowered = resp.lower()
        if not resp:
            flag = "  <-- EMPTY / TIMEOUT"
        elif any(
            kw in lowered
            for kw in ("denied", "not allow", "control", "unauthor", "error")
        ):
            flag = "  <-- CHECK: mentions control/error"
        print(f"~{cmd}\r\n  -> {resp!r}{flag}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe FlashForge M601/M602 control-session behavior over TCP 8899."
    )
    parser.add_argument("--host", required=True, help="Printer IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    print(f"Probing {args.host}:{args.port} (timeout={args.timeout}s)")
    print(
        "Sending only read-only commands (M115, M119, M105, M27). "
        "Nothing here will move an axis or change a setpoint."
    )

    try:
        results_a = run_pattern_a(args.host, args.port, args.timeout)
        print_results(
            "Pattern A: no handshake, fresh connection per command", results_a
        )

        results_b = run_pattern_b(args.host, args.port, args.timeout)
        print_results("Pattern B: persistent connection, M601 once ... M602", results_b)

        results_c = run_pattern_c(args.host, args.port, args.timeout)
        print_results(
            "Pattern C: fresh connection per command, M601 first each time", results_c
        )
    except OSError as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        return 1

    print("\n=== Summary ===")
    print(
        "Compare the three blocks above by eye:\n"
        "  - If A, B, and C all return the same normal-looking data for every "
        "command, the handshake is not required and the integration's current "
        "connect-per-command approach (Pattern A) is fine as-is.\n"
        "  - If A returns errors/empty responses that B or C do not, the "
        "handshake is required and the integration needs to adopt whichever "
        "pattern worked (persistent session vs. per-connection M601).\n"
        "  - Also check whether M602 in Pattern B produces a *different* "
        "response than a bare M602 with no prior M601 -- that confirms "
        "the printer is actually tracking session state."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
