"""Shared pytest fixtures — Windows temp directory cleanup."""
import os
import stat
import pytest


@pytest.fixture(autouse=True)
def _fix_windows_tmp_cleanup(tmp_path):
    """Remove read-only flags before pytest tries to clean temp dirs.

    On Windows with OneDrive or strict ACLs, tmp_path cleanup fails
    with PermissionError. This fixture clears read-only bits post-test.
    """
    yield
    for root, dirs, files in os.walk(str(tmp_path), topdown=False):
        for name in files:
            fp = os.path.join(root, name)
            try:
                os.chmod(fp, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
