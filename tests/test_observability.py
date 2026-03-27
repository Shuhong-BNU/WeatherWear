from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from weatherwear.support import observability


class ObservabilityTests(unittest.TestCase):
    def test_log_event_respects_silence_env(self):
        with patch.dict(os.environ, {"WEATHERWEAR_SILENCE_STDOUT_EVENTS": "1"}, clear=False):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                observability.log_event("demo.event", message="demo")
        self.assertEqual(buffer.getvalue(), "")

    def test_log_event_prints_when_not_silenced(self):
        buffer = io.StringIO()
        with patch.object(observability, "_should_emit_stdout_events", return_value=True):
            with redirect_stdout(buffer):
                observability.log_event("demo.event", message="demo")
        self.assertIn('"type": "demo.event"', buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
