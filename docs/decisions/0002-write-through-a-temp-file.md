# 0002. Write converted files through a temporary file

Date: 2026-11-21. Status: accepted. Requirements: R1.9, R2.7.

In the context of **`convert` rewriting the user's real files**,
facing **a crash, full disk or permission error halfway through a write, which
would leave a half-written file and no way back**,
we decided for **writing the new content to a temporary file in the same folder
and then swapping it in with `os.replace`, cleaning the temp file up on any
error**,
and neglected **opening the original with mode `"wb"` and overwriting it in place,
and copying a `.bak` file next to every original**,
to achieve **a file that is always either completely old or completely new, with
no stray files left in the user's folders**,
accepting that **the new file is a different file on disk (so hard links are not
preserved and permissions have to be copied explicitly), and that it needs enough
free space for a second copy of one file at a time**.

The same helper (`app/fileio.py`) writes the history cache, so a crash cannot
corrupt `history.json` either.
