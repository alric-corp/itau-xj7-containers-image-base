import socket
import time
import unittest
from scripts.pipeline.runtime.readiness import ReadinessTimeout, wait_until_ready


class ReadinessTests(unittest.TestCase):
    def test_fast_service_pays_no_fixed_wait(self):
        calls = []

        def probe():
            calls.append(1)
            return 'ready'

        started = time.monotonic()
        result, attempt = wait_until_ready(probe, interval=1.0, timeout=10.0, attempts=50)
        elapsed = time.monotonic() - started
        self.assertEqual(result, 'ready')
        self.assertEqual(attempt, 1)
        self.assertEqual(len(calls), 1)
        self.assertLess(elapsed, 0.1, 'a service ready on the first try must not pay the interval wait')

    def test_service_that_never_starts_fails_within_the_attempt_limit(self):
        calls = []

        def probe():
            calls.append(1)
            raise ConnectionRefusedError('nobody listening')

        with self.assertRaises(ReadinessTimeout) as caught:
            wait_until_ready(probe, interval=0.001, timeout=10.0, attempts=5)
        self.assertEqual(len(calls), 5)
        self.assertIsInstance(caught.exception.__cause__, ConnectionRefusedError)

    def test_service_that_never_starts_fails_within_the_time_limit(self):
        calls = []

        def probe():
            calls.append(1)
            raise TimeoutError('connect timed out')

        started = time.monotonic()
        with self.assertRaises(ReadinessTimeout):
            wait_until_ready(probe, interval=0.01, timeout=0.05, attempts=100_000)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1.0, 'must not run anywhere close to the attempts budget')
        self.assertGreater(len(calls), 0)

    def test_becomes_ready_partway_through_retries(self):
        remaining = [3]

        def probe():
            remaining[0] -= 1
            if remaining[0] > 0:
                raise ConnectionRefusedError()
            return 'ready'

        result, attempt = wait_until_ready(probe, interval=0.001, timeout=5.0, attempts=10)
        self.assertEqual(result, 'ready')
        self.assertEqual(attempt, 3)

    def test_definitive_rejection_is_the_result_not_a_retry_reason(self):
        # A TLS certificate the client legitimately rejects is the test's
        # actual outcome, not a "not up yet" signal -- must not be retried.
        calls = []

        def probe():
            calls.append(1)
            raise ValueError('certificate verify failed: self-signed certificate')

        with self.assertRaises(ValueError):
            wait_until_ready(probe, interval=1.0, timeout=10.0, attempts=50)
        self.assertEqual(len(calls), 1, 'a definitive rejection must not be retried')

    def test_dns_failure_is_treated_as_not_ready(self):
        calls = []

        def probe():
            calls.append(1)
            if len(calls) < 2:
                raise socket.gaierror('name or service not known')
            return 'ready'

        result, attempt = wait_until_ready(probe, interval=0.001, timeout=5.0, attempts=10)
        self.assertEqual(result, 'ready')
        self.assertEqual(attempt, 2)
