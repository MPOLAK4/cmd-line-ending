"""Safe file writing, shared by convert (R1.9) and the history cache (R2)."""

import contextlib
import os
import shutil
import tempfile
from pathlib import Path


def write_atomic(path: Path, data: bytes) -> None:
    """Replace (or create) the file's content safely.

    The new content goes into a temporary file next to the target, and only when
    it is complete does os.replace swap it in. If anything fails, the original is
    untouched and the temporary file is removed. Raises OSError on failure.
    """
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as temp:
            temp.write(data)
        with contextlib.suppress(FileNotFoundError):  # a brand-new file has no mode to copy
            shutil.copymode(path, temp_name)  # keep the original's permissions
        os.replace(temp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise
