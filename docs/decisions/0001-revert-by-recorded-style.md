# 0001. Revert by recording each file's original style, not by keeping backups

Date: 2026-11-21. Status: accepted. Requirements: R2.1, R2.5, R2.6.

In the context of **R2, the "small cache of recently changed files" that lets the
user revert**,
facing **the choice between remembering only what a file used to be, or keeping a
full copy of every file we change**,
we decided for **storing only the path and the original line ending style of each
changed file in `history.json`, and reverting by converting back to that style**,
and neglected **saving a backup copy of each file's old bytes, and relying on git
or the OS recycle bin**,
to achieve **a cache that stays "small" (a few lines of JSON per file, 50 entries
at most) and that cannot leak or duplicate the contents of private files**,
accepting that **a revert is only safe while the file still has the style we gave
it, so a file edited afterwards is skipped and the user must fix it by hand**.

Why this is safe: convert only touches files that are uniform text with one style
(R1.3), and converting between styles loses nothing (see
`test_R1_8_converting_all_the_way_around_gives_the_original_bytes`). So the style
is enough to rebuild the original bytes exactly.
