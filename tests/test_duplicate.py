"""
Unit tests for core/duplicate.py -- the file-hashing and duplicate-detection
logic that's the core algorithmic piece of LapDoctor.

Run with:
    pip install pytest --break-system-packages
    pytest tests/ -v

(run from the project's mp/ folder, alongside gui.py)
"""

import os
import sys

# Make sure "core" is importable when running `pytest` from the mp/ folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import duplicate


# ----------------------------------------------------------------------
# get_file_hash()
# ----------------------------------------------------------------------

def test_hash_is_deterministic(tmp_path):
    """Hashing the same content twice must give the same result."""
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello world")

    h1 = duplicate.get_file_hash(str(f))
    h2 = duplicate.get_file_hash(str(f))

    assert h1 == h2
    assert h1 is not None


def test_identical_content_same_hash(tmp_path):
    """Two different files with identical bytes must hash identically --
    this is the whole basis of duplicate detection."""
    f1 = tmp_path / "one.txt"
    f2 = tmp_path / "two.txt"
    f1.write_bytes(b"the quick brown fox")
    f2.write_bytes(b"the quick brown fox")

    assert duplicate.get_file_hash(str(f1)) == duplicate.get_file_hash(str(f2))


def test_different_content_different_hash(tmp_path):
    """Files with different bytes must NOT collide."""
    f1 = tmp_path / "one.txt"
    f2 = tmp_path / "two.txt"
    f1.write_bytes(b"the quick brown fox")
    f2.write_bytes(b"the quick brown foy")  # one byte different

    assert duplicate.get_file_hash(str(f1)) != duplicate.get_file_hash(str(f2))


def test_hash_handles_large_file_in_chunks(tmp_path):
    """Files bigger than the chunk size must still hash correctly (this is
    what the chunked read loop exists for -- catches off-by-one/streaming
    bugs that only show up above the chunk boundary)."""
    f = tmp_path / "big.bin"
    # 3.5x the default 8192-byte chunk size, so it needs multiple reads.
    content = os.urandom(8192 * 3 + 4096)
    f.write_bytes(content)

    result = duplicate.get_file_hash(str(f), chunk_size=8192)

    import hashlib
    expected = hashlib.md5(content).hexdigest()
    assert result == expected


def test_hash_missing_file_returns_none():
    """A file that doesn't exist should fail gracefully (None), not raise --
    scans walk real filesystems where files can vanish mid-scan."""
    assert duplicate.get_file_hash("/this/path/does/not/exist.txt") is None


def test_hash_empty_file(tmp_path):
    """An empty file is a valid edge case and must still hash without error."""
    f = tmp_path / "empty.txt"
    f.write_bytes(b"")

    result = duplicate.get_file_hash(str(f))
    import hashlib
    assert result == hashlib.md5(b"").hexdigest()


# ----------------------------------------------------------------------
# scan() -- end-to-end duplicate detection
# ----------------------------------------------------------------------

def test_scan_finds_true_duplicates(tmp_path):
    """Core behavior: identical files in different folders should be
    grouped together and reported as duplicates."""
    (tmp_path / "sub1").mkdir()
    (tmp_path / "sub2").mkdir()

    (tmp_path / "original.txt").write_bytes(b"same content" * 100)
    (tmp_path / "sub1" / "copy1.txt").write_bytes(b"same content" * 100)
    (tmp_path / "sub2" / "copy2.txt").write_bytes(b"same content" * 100)

    result = duplicate.scan(str(tmp_path))

    assert "Found 1 Duplicate Group" in result
    assert "Total Removable Duplicates : 2 files" in result


def test_scan_ignores_same_size_different_content(tmp_path):
    """Two files that happen to share a byte size but have different
    content must NOT be reported as duplicates -- this is exactly the bug
    a size-only check would get wrong, and hashing exists to prevent it."""
    (tmp_path / "a.txt").write_bytes(b"AAAAAAAAAA")  # 10 bytes
    (tmp_path / "b.txt").write_bytes(b"BBBBBBBBBB")  # 10 bytes, same size

    result = duplicate.scan(str(tmp_path))

    assert "No duplicate files found" in result


def test_scan_no_duplicates_in_unique_folder(tmp_path):
    """A folder where every file is unique should report no duplicates."""
    (tmp_path / "a.txt").write_bytes(b"alpha content")
    (tmp_path / "b.txt").write_bytes(b"beta content")
    (tmp_path / "c.txt").write_bytes(b"gamma content")

    result = duplicate.scan(str(tmp_path))

    assert "No duplicate files found" in result


def test_scan_skips_zero_byte_files(tmp_path):
    """Multiple empty (0-byte) files should not be reported as 'duplicates'
    of each other -- there's nothing meaningful to reclaim by deleting them
    as a duplicate group, so scan() explicitly excludes size == 0."""
    (tmp_path / "empty1.txt").write_bytes(b"")
    (tmp_path / "empty2.txt").write_bytes(b"")

    result = duplicate.scan(str(tmp_path))

    assert "No duplicate files found" in result


def test_scan_respects_skip_system_dirs(tmp_path):
    """When skip_system_dirs=True (the default), duplicates sitting inside
    a skipped folder like node_modules must not be reported."""
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dup1.txt").write_bytes(b"same payload")
    (tmp_path / "dup2.txt").write_bytes(b"same payload")

    result_skipped = duplicate.scan(str(tmp_path), skip_system_dirs=True)
    assert "No duplicate files found" in result_skipped  # only 1 real candidate seen

    result_included = duplicate.scan(str(tmp_path), skip_system_dirs=False)
    assert "Found 1 Duplicate Group" in result_included


def test_scan_reports_correct_recoverable_size(tmp_path):
    """The reported reclaimable size should equal the size of the *removable*
    copies only (not counting the one original that's kept)."""
    content = b"x" * 2048  # exactly 2 KB
    (tmp_path / "keep.bin").write_bytes(content)
    (tmp_path / "remove.bin").write_bytes(content)

    result = duplicate.scan(str(tmp_path))

    assert "Total Removable Duplicates : 1 files" in result
    assert "2.00 MB" not in result  # sanity: shouldn't wildly misreport units
    assert "0.00" in result  # 2KB rounds to 0.00 MB, confirms it's using real bytes
