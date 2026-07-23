from __future__ import annotations

import json
from pathlib import Path

from scarag.config import RagConfig


def test_from_profile_maps_synonyms_and_lifecycle_overlay(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_payload = {
        "profile_id": "default",
        "display_name": "Default",
        "synonyms_path": "config/custom-synonyms.json",
        "lifecycle": {
            "preferred_statuses": ["active", "pending_review"],
            "excluded_statuses": ["retired", "deleted"],
            "freshness_days_default": 45,
            "missing_timestamp_policy": "exclude",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile("default")

    assert config.metadata == profile_payload
    assert config.thesaurus_path == "config/custom-synonyms.json"
    assert config.status_allow_list == ["active", "pending_review"]
    assert config.status_deny_list == ["retired", "deleted"]
    assert config.freshness_max_age_days == 45
    assert config.freshness_missing_ts_policy == "exclude"


def test_from_profile_overrides_take_precedence(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_payload = {
        "profile_id": "default",
        "synonyms_path": "config/synonyms-from-profile.json",
        "lifecycle": {
            "preferred_statuses": ["active"],
            "excluded_statuses": ["retired"],
            "freshness_days_default": 10,
            "missing_timestamp_policy": "include",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile(
        "default",
        thesaurus_path="config/synonyms-from-override.json",
        freshness_max_age_days=7,
        freshness_missing_ts_policy="exclude",
    )

    assert config.thesaurus_path == "config/synonyms-from-override.json"
    assert config.freshness_max_age_days == 7
    assert config.freshness_missing_ts_policy == "exclude"
