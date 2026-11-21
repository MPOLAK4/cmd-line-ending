"""Tests for R2.1 to R2.4 and R2.7: the cache of recent changes.

Each test name starts with the requirement ID from spec.md that it checks.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from helpers import AppTestCase

HEADER = re.compile(r"^#(\d+)  \d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC  to (\w+)  (\d+) files?$")


class RecordingTests(AppTestCase):
    """R2.1: what gets written to the cache."""

    def cache(self):
        return json.loads((self.home / "history.json").read_text(encoding="utf-8"))

    def test_R2_1_single_file_change_makes_one_entry_with_one_file(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        entries = self.cache()["entries"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["id"], 1)
        self.assertEqual(entry["to"], "lf")
        self.assertEqual(entry["files"], [{"path": str(f.resolve()), "from": "crlf"}])

    def test_R2_1_directory_change_makes_one_batch_entry(self):
        a = self.write("a.txt", b"x\r\n")
        b = self.write("sub/b.txt", b"x\r")
        self.run_app("convert", self.work, "--to", "lf")
        entries = self.cache()["entries"]
        self.assertEqual(len(entries), 1)
        recorded = {f["path"]: f["from"] for f in entries[0]["files"]}
        self.assertEqual(recorded, {str(a.resolve()): "crlf", str(b.resolve()): "cr"})

    def test_R2_1_only_files_that_really_changed_are_recorded(self):
        changed = self.write("changed.txt", b"x\r\n")
        self.write("already.txt", b"x\n")
        self.write("mixed.txt", b"a\r\nb\n")
        self.write("pic.bin", b"\x00")
        self.run_app("convert", self.work, "--to", "lf")
        files = self.cache()["entries"][0]["files"]
        self.assertEqual([f["path"] for f in files], [str(changed.resolve())])

    def test_R2_1_entry_has_a_utc_timestamp_of_now(self):
        self.write("a.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        stamp = self.cache()["entries"][0]["time"]
        self.assertRegex(stamp, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLess(abs(datetime.now(timezone.utc) - when), timedelta(minutes=1))

    def test_R2_1_a_convert_that_changes_nothing_adds_no_entry(self):
        self.write("a.txt", b"x\n")
        self.write("pic.bin", b"\x00")
        self.run_app("convert", self.work, "--to", "lf")
        self.assertFalse((self.home / "history.json").exists())

    def test_R2_1_no_entry_is_added_when_nothing_changed_after_earlier_entries(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        self.run_app("convert", f, "--to", "lf")  # already lf: nothing changes
        self.assertEqual(len(self.cache()["entries"]), 1)

    def test_R2_1_each_changing_convert_adds_its_own_entry(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        self.run_app("convert", f, "--to", "cr")
        entries = self.cache()["entries"]
        self.assertEqual([e["id"] for e in entries], [1, 2])
        self.assertEqual([e["to"] for e in entries], ["lf", "cr"])

    def test_R2_1_relative_paths_are_stored_as_absolute(self):
        self.write("a.txt", b"x\r\n")
        old_cwd = os.getcwd()
        self.addCleanup(os.chdir, old_cwd)
        os.chdir(self.work)
        self.run_app("convert", "a.txt", "--to", "lf")
        path = self.cache()["entries"][0]["files"][0]["path"]
        self.assertTrue(os.path.isabs(path))
        self.assertEqual(Path(path), (self.work / "a.txt").resolve())


class CacheLocationTests(AppTestCase):
    """R2.2: where the cache lives."""

    def test_R2_2_uses_the_folder_named_by_the_environment_variable(self):
        self.write("a.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        self.assertTrue((self.home / "history.json").is_file())
        json.loads((self.home / "history.json").read_text(encoding="utf-8"))  # valid JSON

    def test_R2_2_defaults_to_dot_cmd_line_ending_in_the_home_folder(self):
        fake_home = self.home.parent / "fake-user-home"
        env = {k: v for k, v in os.environ.items() if k != "CMD_LINE_ENDING_HOME"}
        self.write("a.txt", b"x\r\n")
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(Path, "home", return_value=fake_home):
            self.run_app("convert", self.work, "--to", "lf")
        self.assertTrue((fake_home / ".cmd-line-ending" / "history.json").is_file())

    def test_R2_2_cache_is_not_written_into_the_scanned_folder(self):
        self.write("a.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        self.assertEqual([p.name for p in self.work.iterdir()], ["a.txt"])


class SizeLimitTests(AppTestCase):
    def test_R2_3_keeps_only_the_50_newest_entries(self):
        f = self.write("a.txt", b"x\r\n")
        for i in range(52):  # alternate so every convert really changes the file
            self.run_app("convert", f, "--to", "lf" if i % 2 == 0 else "crlf")
        entries = json.loads((self.home / "history.json").read_text(encoding="utf-8"))["entries"]
        self.assertEqual(len(entries), 50)
        self.assertEqual(entries[0]["id"], 3)
        self.assertEqual(entries[-1]["id"], 52)

    def test_R2_1_ids_are_not_reused_after_old_entries_are_dropped(self):
        f = self.write("a.txt", b"x\r\n")
        for i in range(52):
            self.run_app("convert", f, "--to", "lf" if i % 2 == 0 else "crlf")
        self.run_app("convert", f, "--to", "cr")
        entries = json.loads((self.home / "history.json").read_text(encoding="utf-8"))["entries"]
        self.assertEqual(entries[-1]["id"], 53)

    def test_R2_1_ids_are_not_reused_after_a_revert(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")  # id 1
        self.run_app("revert")  # removes id 1
        self.run_app("convert", f, "--to", "lf")  # must be id 2, not 1 again
        entries = json.loads((self.home / "history.json").read_text(encoding="utf-8"))["entries"]
        self.assertEqual([e["id"] for e in entries], [2])


class HistoryCommandTests(AppTestCase):
    """R2.4: the `history` command."""

    def test_R2_4_empty_history_says_so(self):
        code, out, _ = self.run_app("history")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "No recent changes.")

    def test_R2_4_shows_a_single_change(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        code, out, _ = self.run_app("history")
        lines = out.splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 2)
        match = HEADER.match(lines[0])
        self.assertIsNotNone(match, lines[0])
        self.assertEqual(match.groups(), ("1", "lf", "1"))
        self.assertTrue(lines[0].endswith("1 file"))
        self.assertEqual(lines[1], "    " + str(f.resolve()))

    def test_R2_4_shows_a_batch_with_all_its_files(self):
        a = self.write("a.txt", b"x\r\n")
        b = self.write("b.txt", b"x\r\n")
        self.run_app("convert", self.work, "--to", "lf")
        _, out, _ = self.run_app("history")
        lines = out.splitlines()
        self.assertEqual(HEADER.match(lines[0]).groups(), ("1", "lf", "2"))
        self.assertTrue(lines[0].endswith("2 files"))
        self.assertEqual(lines[1:], ["    " + str(a.resolve()), "    " + str(b.resolve())])

    def test_R2_4_newest_entry_comes_first(self):
        f = self.write("a.txt", b"x\r\n")
        self.run_app("convert", f, "--to", "lf")
        self.run_app("convert", f, "--to", "cr")
        _, out, _ = self.run_app("history")
        headers = [HEADER.match(l) for l in out.splitlines() if l.startswith("#")]
        self.assertEqual([m.group(1) for m in headers], ["2", "1"])
        self.assertEqual([m.group(2) for m in headers], ["cr", "lf"])


class DamagedCacheTests(AppTestCase):
    """R2.7: a bad cache file never crashes a command."""

    def damage(self, content):
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "history.json").write_bytes(content)

    def test_R2_7_missing_cache_is_an_empty_history(self):
        _, out, _ = self.run_app("history")
        self.assertEqual(out.strip(), "No recent changes.")

    def test_R2_7_garbage_wrong_shape_and_empty_files_are_an_empty_history(self):
        for content in (b"this is not json", b"", b"[1, 2, 3]", b'{"entries": "nope"}',
                        b'{"entries": [{"id": 1}], "next_id": 2}', b"\xff\xfe\x00"):
            with self.subTest(content=content):
                self.damage(content)
                code, out, err = self.run_app("history")
                self.assertEqual(code, 0)
                self.assertEqual(out.strip(), "No recent changes.")
                self.assertEqual(err, "")

    def test_R2_7_convert_still_works_and_repairs_the_cache(self):
        self.damage(b"this is not json")
        f = self.write("a.txt", b"x\r\n")
        code, _, _ = self.run_app("convert", f, "--to", "lf")
        self.assertEqual(code, 0)
        self.assertEqual(f.read_bytes(), b"x\n")
        entries = json.loads((self.home / "history.json").read_text(encoding="utf-8"))["entries"]
        self.assertEqual(len(entries), 1)

    def test_R2_7_revert_on_a_damaged_cache_is_a_clean_error(self):
        self.damage(b"this is not json")
        code, _, err = self.run_app("revert")
        self.assertEqual(code, 1)
        self.assertNotEqual(err, "")

    def test_R2_7_unwritable_cache_warns_but_the_conversion_still_happens(self):
        # A folder where history.json should be makes reading AND writing fail.
        (self.home / "history.json").mkdir(parents=True)
        f = self.write("a.txt", b"x\r\n")
        code, out, err = self.run_app("convert", f, "--to", "lf")
        self.assertEqual(code, 0)
        self.assertEqual(f.read_bytes(), b"x\n")
        self.assertIn("converted", out)
        self.assertIn("warning: could not save history", err)
