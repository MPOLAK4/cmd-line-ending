"""Shared test helpers (tests only; the app never imports this file)."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.cli import main


class AppTestCase(unittest.TestCase):
    """Gives each test a scratch folder for files and a private cache folder.

    CMD_LINE_ENDING_HOME points at a temporary folder so a test can never read or
    write the real ~/.cmd-line-ending cache.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name) / "work"
        self.home = Path(tmp.name) / "home"
        self.work.mkdir()
        patcher = mock.patch.dict(os.environ, {"CMD_LINE_ENDING_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, name, data):
        """Write raw bytes (binary mode, so Windows does not change line endings)."""
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run_app(self, *argv):
        """Run the CLI in-process. Returns (exit_code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(a) for a in argv])
        return code, out.getvalue(), err.getvalue()
