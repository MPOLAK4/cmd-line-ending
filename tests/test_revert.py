"""Tests for R2.5 and R2.6: reverting a recorded change.

Each test name starts with the requirement ID from spec.md that it checks.
"""

import contextlib
import io

from helpers import AppTestCase


class RevertTests(AppTestCase):
    def history_ids(self):
        _, out, _ = self.run_app("history")
        return [int(line[1:].split()[0]) for line in out.splitlines() if line.startswith("#")]

    def test_R2_5_without_an_id_reverts_the_newest_entry(self):
        a = self.write("a.txt", b"x\r\n")
        b = self.write("b.txt", b"y\n")
        self.run_app("convert", a, "--to", "lf")  # entry 1
        self.run_app("convert", b, "--to", "cr")  # entry 2 (newest)
        code, out, _ = self.run_app("revert")
        self.assertEqual(code, 0)
        self.assertEqual(b.read_bytes(), b"y\n")  # newest was undone
        self.assertEqual(a.read_bytes(), b"x\n")  # older one is still converted
        self.assertEqual(self.history_ids(), [1])

    def test_R2_5_a_given_id_reverts_that_entry_only(self):
        a = self.write("a.txt", b"x\r\n")
        b = self.write("b.txt", b"y\n")
        self.run_app("convert", a, "--to", "lf")  # entry 1
        self.run_app("convert", b, "--to", "cr")  # entry 2
        code, _, _ = self.run_app("revert", "1")
        self.assertEqual(code, 0)
        self.assertEqual(a.read_bytes(), b"x\r\n")
        self.assertEqual(b.read_bytes(), b"y\r")  # untouched by this revert
        self.assertEqual(self.history_ids(), [2])

    def test_R2_5_a_batch_goes_back_to_each_files_own_original_style(self):
        a = self.write("a.txt", b"x\r\ny\r\n")
        b = self.write("b.txt", b"x\ry\r")
        c = self.write("c.txt", b"x\ny\n")
        self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual(a.read_bytes(), b"x\ny\n")
        self.run_app("revert")
        self.assertEqual(a.read_bytes(), b"x\r\ny\r\n")
        self.assertEqual(b.read_bytes(), b"x\ry\r")
        self.assertEqual(c.read_bytes(), b"x\ny\n")

    def test_R2_5_output_lines_and_summary(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        _, out, _ = self.run_app("revert")
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("reverted"))
        self.assertIn("lf -> crlf", lines[0])
        self.assertTrue(lines[0].endswith(str(f.resolve())))
        self.assertEqual(lines[-1], "1 reverted, 0 skipped")

    def test_R2_5_revert_does_not_add_a_history_entry(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        self.run_app("revert")
        self.assertEqual(self.history_ids(), [])

    def test_R2_5_empty_history_is_an_error(self):
        code, out, err = self.run_app("revert")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertNotEqual(err, "")

    def test_R2_5_unknown_id_is_an_error_and_changes_nothing(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        code, out, err = self.run_app("revert", "99")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("99", err)
        self.assertEqual(f.read_bytes(), b"x\n")
        self.assertEqual(self.history_ids(), [1])

    def test_R2_5_id_must_be_a_number(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                self.run_app("revert", "abc")
        self.assertEqual(caught.exception.code, 2)

    def test_R2_5_the_same_entry_cannot_be_reverted_twice(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        self.run_app("revert", "1")
        code, out, err = self.run_app("revert", "1")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertNotEqual(err, "")

    def test_R2_6_missing_file_is_skipped_and_the_others_are_reverted(self):
        gone = self.write("a_gone.txt", b"x\r\n")
        kept = self.write("b_kept.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        gone.unlink()
        code, out, _ = self.run_app("revert")
        self.assertEqual(code, 0)
        self.assertEqual(kept.read_bytes(), b"x\r\n")
        gone_line = [l for l in out.splitlines() if "a_gone.txt" in l][0]
        self.assertTrue(gone_line.startswith("skipped"))
        self.assertIn("missing", gone_line)
        self.assertEqual(out.splitlines()[-1], "1 reverted, 1 skipped")

    def test_R2_6_file_edited_since_is_skipped_and_left_alone(self):
        edited = self.write("a_edited.txt", b"x\r\n")
        kept = self.write("b_kept.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        edited.write_bytes(b"someone\r\nwrote\r\nthis\r\n")  # now crlf, not lf
        _, out, _ = self.run_app("revert")
        self.assertEqual(edited.read_bytes(), b"someone\r\nwrote\r\nthis\r\n")
        self.assertEqual(kept.read_bytes(), b"x\r\n")
        line = [l for l in out.splitlines() if "a_edited.txt" in l][0]
        self.assertTrue(line.startswith("skipped"))
        self.assertIn("changed since", line)

    def test_R2_6_file_that_became_binary_or_mixed_counts_as_changed(self):
        binary = self.write("a.txt", b"x\r\n")
        mixed = self.write("b.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        binary.write_bytes(b"\x00\x01\n")
        mixed.write_bytes(b"a\nb\r\n")
        _, out, _ = self.run_app("revert")
        self.assertEqual(out.count("changed since"), 2)
        self.assertEqual(out.splitlines()[-1], "0 reverted, 2 skipped")

    def test_R2_6_entry_is_removed_even_when_some_files_were_skipped(self):
        gone = self.write("a.txt", b"x\r\n")
        self.write("b.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        gone.unlink()
        self.run_app("revert")
        self.assertEqual(self.history_ids(), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
