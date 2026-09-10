"""Bounded readiness polling for a service started as an external process.

Runs from the harness (the caller), never inside the runtime image under
test -- it never assumes shell/curl exist there. Retries only the errors
that mean "not listening yet" (connection refused, no route, DNS not
resolved, timed out). Anything else -- including a completed TLS handshake
that the client or server legitimately rejects -- is the actual result of
the check, not evidence the service isn't up, and propagates immediately
instead of burning through retries.
"""
import time

NOT_READY = (ConnectionRefusedError, TimeoutError, ConnectionResetError)
# OSError/socket.gaierror covers "no route"/DNS failures without also
# catching ssl.SSLError, which is a *subclass* of OSError in CPython and
# must stay a definitive result rather than a retry signal.
try:
    import socket
    NOT_READY = NOT_READY + (socket.gaierror,)
except ImportError:  # pragma: no cover - socket is stdlib, always present
    pass


class ReadinessTimeout(RuntimeError):
    """The probe never reported ready within the attempt/time budget."""


def wait_until_ready(probe, *, interval=0.2, timeout=10.0, attempts=50):
    """Call `probe()` until it returns without raising a NOT_READY error.

    Returns `(result, attempt_number)` on success -- a fast service pays no
    fixed wait, since the first successful attempt returns immediately.
    Raises `ReadinessTimeout` (with the last underlying error attached via
    `__cause__`, for log collection) once either `attempts` or `timeout` is
    exhausted, whichever comes first -- a service that never starts fails
    within a bounded budget, not by hanging the caller.
    """
    started = time.monotonic()
    attempt = 0
    last_error = None
    while True:
        attempt += 1
        try:
            return probe(), attempt
        except NOT_READY as error:
            last_error = error
        if attempt >= attempts or time.monotonic() - started >= timeout:
            break
        time.sleep(interval)
    elapsed = time.monotonic() - started
    raise ReadinessTimeout(
        f'not ready after {attempt} attempt(s) in {elapsed:.2f}s '
        f'(limits: {attempts} attempts / {timeout}s timeout): {last_error}') from last_error
