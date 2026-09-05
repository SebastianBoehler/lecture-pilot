"""Run with .venv/bin/python -m unittest discover -s scripts -p test_read_capacity.py."""

import unittest

from benchmark_read_capacity import local_url, percentile, summary
from seed_read_capacity import validate_database


class CapacityGuardTests(unittest.TestCase):
    def test_loopback_origin(self):
        self.assertEqual(local_url("http://127.0.0.1:58001/"), "http://127.0.0.1:58001")

    def test_rejects_remote_or_credentialed_target(self):
        for target in (
            "https://lecturepilot.example",
            "http://127.0.0.1.example",
            "http://user:secret@127.0.0.1",
            "http://127.0.0.1/agent/turn",
            "http://127.0.0.1?target=production",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                local_url(target)

    def test_disposable_database_only(self):
        validate_database(
            "postgresql://u:p@127.0.0.1:55432/lecturepilot_capacity_pytest"
        )
        for target in (
            "postgresql://u:p@db.example/lecturepilot_capacity_pytest",
            "postgresql://u:p@127.0.0.1/lecturepilot",
            "http://127.0.0.1/lecturepilot_capacity_pytest",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_database(target)

    def test_nearest_rank_percentile(self):
        self.assertEqual(percentile(list(range(1, 101)), 0.95), 95)
        self.assertEqual(percentile([], 0.95), 0)

    def test_errors_count_as_requests(self):
        result = summary(
            [
                {"ms": 10, "status": 200, "bytes": 100},
                {"ms": 20, "status": 503, "bytes": 20},
                {"ms": 30, "status": "ReadTimeout", "bytes": 0},
            ],
            2,
        )
        self.assertEqual(result["requests_per_second"], 1.5)
        self.assertEqual(
            result["status_counts"], {"200": 1, "503": 1, "ReadTimeout": 1}
        )
        self.assertEqual(result["response_bytes_total"], 120)


if __name__ == "__main__":
    unittest.main()
