"""Tests for R1 (scan): which files can change, and what to change them to.

Each test name starts with the requirement ID from spec.md that it checks.
"""

import unittest

from app.lineendings import detect_style
from helpers import AppTestCase


class DetectStyleTests(unittest.TestCase):
    """R1.2 and R1.3: classify raw bytes."""

    def test_R1_2_lf(self):
        self.assertEqual(detect_style(b"a\nb\n"), "lf")

    def test_R1_2_crlf(self):
        self.assertEqual(detect_style(b"a\r\nb\r\n"), "crlf")

    def test_R1_2_cr(self):
        self.assertEqual(detect_style(b"a\rb\r"), "cr")

    def test_R1_2_crlf_is_not_counted_as_cr_plus_lf(self):
        # "\r\n" is ONE ending. If we counted \r and \n separately this would
        # wrongly look mixed.
        self.assertEqual(detect_style(b"one\r\n"), "crlf")

    def test_R1_3_mixed(self):
        self.assertEqual(detect_style(b"a\r\nb\nc\n"), "mixed")

    def test_R1_3_mixed_cr_and_lf(self):
        self.assertEqual(detect_style(b"a\rb\n"), "mixed")

    def test_R1_3_empty_has_no_line_endings(self):
        self.assertEqual(detect_style(b""), "no line endings")

    def test_R1_3_single_line_has_no_line_endings(self):
        self.assertEqual(detect_style(b"just one line"), "no line endings")

    def test_R1_3_nul_byte_is_binary(self):
        self.assertEqual(detect_style(b"a\n\x00b\n"), "binary")

    def test_R1_3_invalid_utf8_is_binary(self):
        self.assertEqual(detect_style(b"a\n\xff\xfe\n"), "binary")

    def test_R1_3_valid_utf8_text_is_not_binary(self):
        self.assertEqual(detect_style("café\n".encode("utf-8")), "lf")


class ScanCommandTests(AppTestCase):
    def test_R1_1_missing_path_is_an_error(self):
        code, out, err = self.run_app("scan", self.work / "nope")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("nope", err)

    def test_R1_1_accepts_a_single_file(self):
        f = self.write("a.txt", b"x\r\ny\r\n")
        code, out, _ = self.run_app("scan", f)
        self.assertEqual(code, 0)
        self.assertIn(str(f), out)

    def test_R1_1_accepts_a_directory(self):
        self.write("a.txt", b"x\r\n")
        self.write("b.txt", b"x\n")
        code, out, _ = self.run_app("scan", self.work)
        self.assertEqual(code, 0)
        self.assertIn("a.txt", out)
        self.assertIn("b.txt", out)

    def test_R1_4_suggests_lf_for_crlf(self):
        f = self.write("a.txt", b"x\r\n")
        _, out, _ = self.run_app("scan", f)
        line = out.splitlines()[0]
        self.assertTrue(line.startswith("changeable"))
        self.assertIn("crlf -> lf", line)

    def test_R1_4_suggests_crlf_for_lf(self):
        f = self.write("a.txt", b"x\n")
        _, out, _ = self.run_app("scan", f)
        self.assertIn("lf -> crlf", out.splitlines()[0])

    def test_R1_4_suggests_lf_for_cr(self):
        f = self.write("a.txt", b"x\ry\r")
        _, out, _ = self.run_app("scan", f)
        self.assertIn("cr -> lf", out.splitlines()[0])

    def test_R1_3_skipped_files_show_their_reason(self):
        self.write("bin.dat", b"\x00\x01\n")
        self.write("mixed.txt", b"a\r\nb\n")
        self.write("empty.txt", b"")
        _, out, _ = self.run_app("scan", self.work)
        lines = {line.split()[-1].replace("\\", "/").split("/")[-1]: line
                 for line in out.splitlines()[:-1]}
        for name, reason in [("bin.dat", "binary"), ("mixed.txt", "mixed"),
                             ("empty.txt", "no line endings")]:
            self.assertTrue(lines[name].startswith("skipped"), lines[name])
            self.assertIn(reason, lines[name])

    def test_R1_5_recurses_into_subdirectories(self):
        self.write("sub/deeper/c.txt", b"x\r\n")
        _, out, _ = self.run_app("scan", self.work)
        self.assertIn("c.txt", out)

    def test_R1_5_files_are_listed_in_sorted_order(self):
        for name in ["b.txt", "c.txt", "a.txt"]:
            self.write(name, b"x\n")
        _, out, _ = self.run_app("scan", self.work)
        names = [line.split()[-1] for line in out.splitlines()[:-1]]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), 3)

    def test_R1_5_ignored_directories_are_not_entered(self):
        for d in [".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv"]:
            self.write(f"{d}/inside.txt", b"x\n")
        self.write("kept.txt", b"x\n")
        _, out, _ = self.run_app("scan", self.work)
        self.assertIn("kept.txt", out)
        self.assertNotIn("inside.txt", out)

    def test_R1_6_scan_does_not_modify_files(self):
        f = self.write("a.txt", b"x\r\ny\r\n")
        before_bytes, before_mtime = f.read_bytes(), f.stat().st_mtime_ns
        self.run_app("scan", self.work)
        self.assertEqual(f.read_bytes(), before_bytes)
        self.assertEqual(f.stat().st_mtime_ns, before_mtime)

    def test_R1_6_scan_does_not_create_history(self):
        self.write("a.txt", b"x\r\n")
        self.run_app("scan", self.work)
        self.assertFalse((self.home / "history.json").exists())

    def test_R1_7_summary_line_counts_both_kinds(self):
        self.write("a.txt", b"x\r\n")
        self.write("b.txt", b"x\n")
        self.write("c.bin", b"\x00")
        _, out, _ = self.run_app("scan", self.work)
        self.assertEqual(out.splitlines()[-1], "2 changeable, 1 skipped")

    def test_R1_7_one_line_per_file_plus_summary(self):
        self.write("a.txt", b"x\r\n")
        self.write("b.txt", b"x\n")
        _, out, _ = self.run_app("scan", self.work)
        self.assertEqual(len(out.splitlines()), 3)

    def test_R1_7_empty_directory_still_prints_summary(self):
        _, out, _ = self.run_app("scan", self.work)
        self.assertEqual(out.splitlines(), ["0 changeable, 0 skipped"])


if __name__ == "__main__":
    unittest.main()
