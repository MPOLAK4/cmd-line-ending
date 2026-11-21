"""Tests for R1.8 and R1.9 (convert): change endings safely.

Each test name starts with the requirement ID from spec.md that it checks.
"""

import contextlib
import io
import os
import stat
import unittest
from pathlib import Path
from unittest import mock

from app.lineendings import convert_bytes
from helpers import AppTestCase

ENDINGS = {"lf": b"\n", "crlf": b"\r\n", "cr": b"\r"}


class ConvertBytesTests(unittest.TestCase):
    def test_R1_8_every_style_to_every_other_style(self):
        for source, source_bytes in ENDINGS.items():
            for target, target_bytes in ENDINGS.items():
                with self.subTest(source=source, target=target):
                    data = b"one" + source_bytes + b"two" + source_bytes
                    expected = b"one" + target_bytes + b"two" + target_bytes
                    self.assertEqual(convert_bytes(data, target), expected)

    def test_R1_8_only_line_endings_change(self):
        data = "café ✓\r\n\ttabbed  \r\nno ending at the end".encode("utf-8")
        expected = "café ✓\n\ttabbed  \nno ending at the end".encode("utf-8")
        self.assertEqual(convert_bytes(data, "lf"), expected)

    def test_R1_8_blank_lines_are_kept(self):
        self.assertEqual(convert_bytes(b"a\r\n\r\n\r\nb\r\n", "lf"), b"a\n\n\nb\n")


class ConvertCommandTests(AppTestCase):
    def test_R1_8_converts_a_single_file(self):
        f = self.write("a.txt", b"x\r\ny\r\n")
        code, out, _ = self.run_app("convert", f, "--to", "lf")
        self.assertEqual(code, 0)
        self.assertEqual(f.read_bytes(), b"x\ny\n")
        self.assertTrue(out.splitlines()[0].startswith("converted"))
        self.assertIn("crlf -> lf", out.splitlines()[0])

    def test_R1_8_converts_every_changeable_file_in_a_directory(self):
        a = self.write("a.txt", b"x\r\n")
        b = self.write("sub/b.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual(a.read_bytes(), b"x\n")
        self.assertEqual(b.read_bytes(), b"x\n")

    def test_R1_8_file_already_in_target_style_is_untouched(self):
        f = self.write("a.txt", b"x\ny\n")
        before = f.stat().st_mtime_ns
        _, out, _ = self.run_app("convert", f, "--to", "lf")
        self.assertEqual(f.read_bytes(), b"x\ny\n")
        self.assertEqual(f.stat().st_mtime_ns, before)
        line = out.splitlines()[0]
        self.assertTrue(line.startswith("unchanged"))
        self.assertIn("already lf", line)

    def test_R1_8_skipped_files_are_untouched_and_explained(self):
        binary = self.write("pic.bin", b"\x00\r\n\x01")
        mixed = self.write("mixed.txt", b"a\r\nb\n")
        _, out, _ = self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual(binary.read_bytes(), b"\x00\r\n\x01")
        self.assertEqual(mixed.read_bytes(), b"a\r\nb\n")
        self.assertIn("binary", out)
        self.assertIn("mixed", out)
        self.assertEqual(out.count("skipped"), 3)  # 2 lines + summary

    def test_R1_8_summary_line(self):
        self.write("a.txt", b"x\r\n")
        self.write("b.txt", b"x\n")
        self.write("c.bin", b"\x00")
        _, out, _ = self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual(out.splitlines()[-1], "1 converted, 1 unchanged, 1 skipped")

    def test_R1_8_missing_path_is_an_error(self):
        code, out, err = self.run_app("convert", self.work / "nope", "--to", "lf")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("nope", err)

    def test_R1_8_target_style_is_required_and_checked(self):
        f = self.write("a.txt", b"x\r\n")
        for argv in (["convert", f], ["convert", f, "--to", "banana"]):
            with self.subTest(argv=argv):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        self.run_app(*argv)
                self.assertEqual(caught.exception.code, 2)
        self.assertEqual(f.read_bytes(), b"x\r\n")

    def test_R1_8_converting_all_the_way_around_gives_the_original_bytes(self):
        original = b"a\r\nb\r\n\r\nc\r\n"
        f = self.write("a.txt", original)
        for target in ("lf", "cr", "crlf"):
            self.run_app("convert", f, "--to", target)
        self.assertEqual(f.read_bytes(), original)

    def test_R1_9_no_temporary_files_are_left_behind(self):
        self.write("a.txt", b"x\r\n")
        self.write("b.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual(sorted(p.name for p in self.work.iterdir()), ["a.txt", "b.txt"])

    def test_R1_9_permissions_are_kept(self):
        f = self.write("script.sh", b"echo hi\r\n")
        os.chmod(f, 0o600)
        before = stat.S_IMODE(f.stat().st_mode)
        self.run_app("convert", f, "--to", "lf")
        self.assertEqual(stat.S_IMODE(f.stat().st_mode), before)

    def test_R1_9_failed_write_leaves_the_original_and_carries_on(self):
        bad = self.write("a_bad.txt", b"x\r\n")
        good = self.write("b_good.txt", b"x\r\n")
        real_replace = os.replace

        def fake_replace(src, dst):
            if Path(dst).name == "a_bad.txt":
                raise PermissionError("denied")
            return real_replace(src, dst)

        with mock.patch("os.replace", fake_replace):
            code, out, _ = self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual(code, 0)
        self.assertEqual(bad.read_bytes(), b"x\r\n")  # untouched
        self.assertEqual(good.read_bytes(), b"x\n")  # the rest still happened
        bad_line = [l for l in out.splitlines() if "a_bad.txt" in l][0]
        self.assertTrue(bad_line.startswith("skipped"))
        self.assertIn("write failed", bad_line)
        self.assertEqual(sorted(p.name for p in self.work.iterdir()),
                         ["a_bad.txt", "b_good.txt"])  # temp file cleaned up
        self.assertEqual(out.splitlines()[-1], "1 converted, 0 unchanged, 1 skipped")


if __name__ == "__main__":
    unittest.main()
