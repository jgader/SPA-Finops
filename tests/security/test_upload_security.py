import gzip
import io
import os

import pytest

from app.security.csv_sanitize import sanitize_cell
from app.security.path_safety import PathTraversalRejected, safe_join, sanitize_display_filename
from app.security.upload_guard import (
    DecompressionLimitExceeded,
    UnsupportedFormat,
    UploadTooLarge,
    decompress_gzip_with_limit,
    save_upload_stream,
    validate_extension,
    validate_magic_bytes,
)


def test_path_traversal_rejected(tmp_path):
    base = tmp_path / "incoming"
    base.mkdir()
    with pytest.raises(PathTraversalRejected):
        safe_join(str(base), "..", "..", "etc", "passwd")


def test_path_traversal_with_absolute_path_disguised_as_filename_rejected(tmp_path):
    base = tmp_path / "incoming"
    base.mkdir()
    with pytest.raises(PathTraversalRejected):
        safe_join(str(base), "/etc/passwd")


def test_safe_join_allows_legitimate_nested_path(tmp_path):
    base = tmp_path / "incoming"
    base.mkdir()
    result = safe_join(str(base), "batch-123", "file.csv")
    assert result.startswith(str(base))


def test_sanitize_display_filename_never_used_as_path_strips_traversal_chars():
    assert sanitize_display_filename("../../etc/passwd") == "passwd"
    assert sanitize_display_filename("report;rm -rf.csv") == "report_rm_-rf.csv" or ".csv" in sanitize_display_filename(
        "report;rm -rf.csv"
    )


def test_extension_allowlist_rejects_unknown_extension():
    with pytest.raises(UnsupportedFormat):
        validate_extension("payload.exe")
    assert validate_extension("data.csv") == ".csv"


def test_upload_exceeding_max_bytes_is_rejected_and_partial_file_removed(tmp_path):
    dest = tmp_path / "upload.tmp"
    stream = io.BytesIO(b"x" * 1000)
    with pytest.raises(UploadTooLarge):
        save_upload_stream(stream, str(dest), max_bytes=100)
    assert not dest.exists()


def test_magic_bytes_reject_binary_disguised_as_csv(tmp_path):
    fake_csv = tmp_path / "fake.csv"
    fake_csv.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00binary-not-csv")
    with pytest.raises(UnsupportedFormat):
        validate_magic_bytes(str(fake_csv), ".csv")


def test_magic_bytes_accept_genuine_csv(tmp_path):
    real_csv = tmp_path / "real.csv"
    real_csv.write_text("a,b,c\n1,2,3\n")
    validate_magic_bytes(str(real_csv), ".csv")  # não levanta


def test_decompression_bomb_aborted_and_no_file_left_behind(tmp_path):
    compressed = tmp_path / "bomb.csv.gz"
    # 1MB comprimido que descomprimiria para bem mais que o limite configurado nesse teste
    huge_payload = b"0" * (50 * 1024 * 1024)
    with gzip.open(compressed, "wb") as handle:
        handle.write(huge_payload)

    destination = tmp_path / "decompressed.csv"
    with pytest.raises(DecompressionLimitExceeded):
        decompress_gzip_with_limit(str(compressed), str(destination))
    assert not destination.exists()


def test_csv_formula_injection_neutralized_on_output():
    assert sanitize_cell("=cmd|'/c calc'!A1") == "'=cmd|'/c calc'!A1"
    assert sanitize_cell("+1+1") == "'+1+1"
    assert sanitize_cell("@SUM(1,2)") == "'@SUM(1,2)"
    assert sanitize_cell("normal value") == "normal value"
