# 0003. Test with the standard library's unittest

Date: 2026-11-21. Status: accepted (chosen by the project owner). Requirements:
all, since every test cites a requirement ID.

In the context of **choosing a test tool for a small Python command-line app whose
README promises "no libraries to install"**,
facing **`CLAUDE.md` naming `pytest` while `README.md` named `unittest`**,
we decided for **`unittest`, run with `python -m unittest discover -s tests -v`**,
and neglected **`pytest`**,
to achieve **tests that run on any machine with Python and nothing else, and one
command that matches the README**,
accepting that **tests are a little wordier (classes, `self.assertEqual`) and
there is no fixture or parametrize feature, so we use `setUp` and `subTest`
instead**.
