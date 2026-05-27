"""Tests for env_paths.py — OneDrive placeholder resolution."""
from __future__ import annotations

import os

import pytest

from env_paths import (
    apply_onedrive_placeholders,
    detect_onedrive_root,
    expand_placeholders,
)


# ---------------------------------------------------------------------------
# expand_placeholders — string-level substitution
# ---------------------------------------------------------------------------

class TestExpandPlaceholders:
    def test_single_placeholder(self):
        assert expand_placeholders(
            "${ROOT}/data", {"ROOT": "C:\\OneDrive"}
        ) == "C:\\OneDrive/data"

    def test_multiple_placeholders(self):
        result = expand_placeholders(
            "${A}/x/${B}", {"A": "/a", "B": "b"},
        )
        assert result == "/a/x/b"

    def test_strips_surrounding_quotes(self):
        assert expand_placeholders('"plain"', {}) == "plain"
        assert expand_placeholders("'plain'", {}) == "plain"

    def test_unknown_placeholder_kept(self):
        # Unknown placeholders must survive untouched so callers can decide
        # whether to treat them as an error.
        assert expand_placeholders(
            "${MISSING}/x", {"OTHER": "y"},
        ) == "${MISSING}/x"

    def test_no_placeholders(self):
        assert expand_placeholders("plain/path", {}) == "plain/path"


# ---------------------------------------------------------------------------
# detect_onedrive_root — discovery logic with a synthetic filesystem
# ---------------------------------------------------------------------------

class TestDetectOneDriveRoot:
    def test_manual_override_wins(self, tmp_path, monkeypatch):
        target = tmp_path / "Custom"
        target.mkdir()
        monkeypatch.setenv("ONEDRIVE_DATAME", str(target))
        # Ensure scan-based sources can't accidentally match
        monkeypatch.delenv("OneDriveCommercial", raising=False)
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "noprofile"))
        assert detect_onedrive_root("ONEDRIVE_DATAME") == str(target)

    def test_userprofile_scan_finds_matching_folder(self, tmp_path, monkeypatch):
        profile = tmp_path / "user"
        profile.mkdir()
        (profile / "OneDrive - DataME").mkdir()
        (profile / "OneDrive - Other").mkdir()
        monkeypatch.delenv("ONEDRIVE_DATAME", raising=False)
        monkeypatch.delenv("OneDriveCommercial", raising=False)
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(profile))
        got = detect_onedrive_root("ONEDRIVE_DATAME")
        assert got is not None
        assert got.endswith("OneDrive - DataME")

    def test_returns_none_when_no_candidate(self, tmp_path, monkeypatch):
        profile = tmp_path / "empty"
        profile.mkdir()
        monkeypatch.delenv("ONEDRIVE_DATAME", raising=False)
        monkeypatch.delenv("OneDriveCommercial", raising=False)
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(profile))
        assert detect_onedrive_root("ONEDRIVE_DATAME") is None

    def test_windows_env_var_matched_by_fragment(self, tmp_path, monkeypatch):
        # %OneDriveCommercial% points at a folder whose name contains DataME.
        target = tmp_path / "drive_root" / "OneDrive - DataME"
        target.mkdir(parents=True)
        monkeypatch.delenv("ONEDRIVE_DATAME", raising=False)
        monkeypatch.setenv("OneDriveCommercial", str(target))
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "noprofile"))
        assert detect_onedrive_root("ONEDRIVE_DATAME") == str(target)

    def test_finds_sibling_via_onedrive_parent(self, tmp_path, monkeypatch):
        # OneDrive folders sit at a drive root, sibling to each other.
        # %OneDriveCommercial% only points at the DataME tenant, but the
        # IUCN folder is its sibling — detection must still find it.
        # / Las carpetas OneDrive son hermanas en la raíz del disco.
        drive_root = tmp_path / "drive_root"
        datame = drive_root / "OneDrive - DataME"
        iucn = drive_root / "OneDrive - IUCN International Union for Conservation of Nature"
        datame.mkdir(parents=True)
        iucn.mkdir(parents=True)
        monkeypatch.delenv("ONEDRIVE_IUCN", raising=False)
        monkeypatch.setenv("OneDriveCommercial", str(datame))
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "noprofile"))
        got = detect_onedrive_root("ONEDRIVE_IUCN")
        assert got is not None
        assert "IUCN" in got


# ---------------------------------------------------------------------------
# apply_onedrive_placeholders — end-to-end expansion over a dict
# ---------------------------------------------------------------------------

class TestApplyOneDrivePlaceholders:
    def test_expands_values_in_supplied_env(self, tmp_path, monkeypatch):
        profile = tmp_path / "user"
        profile.mkdir()
        (profile / "OneDrive - DataME").mkdir()
        monkeypatch.delenv("ONEDRIVE_DATAME", raising=False)
        monkeypatch.delenv("OneDriveCommercial", raising=False)
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(profile))

        env = {
            "FOLDER_C1": r"${ONEDRIVE_DATAME}\data\gis\C1",
            "OTHER": "no_placeholder",
        }
        detected = apply_onedrive_placeholders(env)
        assert detected["ONEDRIVE_DATAME"].endswith("OneDrive - DataME")
        assert env["FOLDER_C1"].endswith(r"OneDrive - DataME\data\gis\C1")
        assert env["OTHER"] == "no_placeholder"

    def test_unresolved_placeholder_left_intact(self, tmp_path, monkeypatch):
        profile = tmp_path / "empty"
        profile.mkdir()
        monkeypatch.delenv("ONEDRIVE_DATAME", raising=False)
        monkeypatch.delenv("ONEDRIVE_IUCN", raising=False)
        monkeypatch.delenv("OneDriveCommercial", raising=False)
        monkeypatch.delenv("OneDrive", raising=False)
        monkeypatch.delenv("OneDriveConsumer", raising=False)
        monkeypatch.setenv("USERPROFILE", str(profile))
        env = {"EXCEL_DB_DIR": r"${ONEDRIVE_IUCN}\db"}
        detected = apply_onedrive_placeholders(env)
        assert detected["ONEDRIVE_IUCN"] == ""
        # Placeholder stays so the operator can spot the missing OneDrive.
        assert env["EXCEL_DB_DIR"] == r"${ONEDRIVE_IUCN}\db"
