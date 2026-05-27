"""Tests for PASO 3 cleaning stats — pipeline_state and API endpoints."""
import json
import pytest

from pipeline_state import PipelineState


# ── PipelineState unit tests ──────────────────────────────────────────────────

class TestCleaningStatsField:
    def test_default_is_empty_dict(self, tmp_path):
        state = PipelineState(tmp_path)
        assert state.cleaning_stats == {}

    def test_set_cleaning_stats_stores_value(self, tmp_path):
        state = PipelineState(tmp_path)
        stats = {
            "before": {"count": 120, "area_ha": 5400.5},
            "after":  {"count": 115, "area_ha": 5210.3},
            "removed": [{"cdg": "ACT001", "area_ha": 10.2, "reason": "Overlap"}],
        }
        state.set_cleaning_stats(stats)
        assert state.cleaning_stats["before"]["count"] == 120
        assert state.cleaning_stats["after"]["area_ha"] == 5210.3
        assert len(state.cleaning_stats["removed"]) == 1

    def test_to_dict_includes_cleaning_stats(self, tmp_path):
        state = PipelineState(tmp_path)
        state.set_cleaning_stats({"before": {"count": 50, "area_ha": 100.0}, "after": {"count": 48, "area_ha": 96.5}, "removed": []})
        d = state.to_dict()
        assert "cleaning_stats" in d
        assert d["cleaning_stats"]["before"]["count"] == 50

    def test_cleaning_stats_persisted_to_json(self, tmp_path):
        state = PipelineState(tmp_path)
        state.set_cleaning_stats({"before": {"count": 10, "area_ha": 200.0}, "after": {"count": 9, "area_ha": 180.0}, "removed": []})
        state.flush()  # set_cleaning_stats is debounced; flush before reading disk
        saved = json.loads((tmp_path / "pipeline_state.json").read_text(encoding="utf-8"))
        assert saved["cleaning_stats"]["before"]["count"] == 10

    def test_cleaning_stats_loaded_from_json(self, tmp_path):
        state = PipelineState(tmp_path)
        state.set_cleaning_stats({"before": {"count": 77, "area_ha": 3000.0}, "after": {"count": 75, "area_ha": 2950.0}, "removed": []})
        state.flush()  # set_cleaning_stats is debounced; flush before reading disk

        state2 = PipelineState(tmp_path)
        state2.load()
        assert state2.cleaning_stats["before"]["count"] == 77

    def test_load_missing_cleaning_stats_defaults_empty(self, tmp_path):
        # Write a state JSON without cleaning_stats key
        state_file = tmp_path / "pipeline_state.json"
        state_file.write_text(json.dumps({"paso_status": {"1": "pending"}}), encoding="utf-8")
        state = PipelineState(tmp_path)
        state.load()
        assert state.cleaning_stats == {}

    def test_set_cleaning_stats_overwrites(self, tmp_path):
        state = PipelineState(tmp_path)
        state.set_cleaning_stats({"before": {"count": 5, "area_ha": 50.0}, "after": {"count": 4, "area_ha": 40.0}, "removed": []})
        state.set_cleaning_stats({"before": {"count": 20, "area_ha": 200.0}, "after": {"count": 18, "area_ha": 180.0}, "removed": []})
        assert state.cleaning_stats["before"]["count"] == 20


# ── Flask API endpoint tests ──────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Flask test client with a fresh PipelineState."""
    import app as app_module
    new_state = PipelineState(tmp_path)
    monkeypatch.setattr(app_module, "_pipeline_state", new_state)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


class TestCleaningStatsAPI:
    def test_get_returns_empty_dict_initially(self, client):
        resp = client.get("/api/pipeline/cleaning-stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {}

    def test_post_saves_stats(self, client):
        payload = {
            "before": {"count": 100, "area_ha": 4000.0},
            "after":  {"count": 95,  "area_ha": 3800.0},
            "removed": [{"cdg": "X001", "area_ha": 5.0, "reason": "Duplicate"}],
        }
        resp = client.post(
            "/api/pipeline/cleaning-stats",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["stats"]["before"]["count"] == 100
        assert data["stats"]["after"]["area_ha"] == 3800.0

    def test_get_after_post_returns_saved(self, client):
        payload = {
            "before": {"count": 30, "area_ha": 1500.0},
            "after":  {"count": 28, "area_ha": 1400.0},
            "removed": [],
        }
        client.post(
            "/api/pipeline/cleaning-stats",
            data=json.dumps(payload),
            content_type="application/json",
        )
        resp = client.get("/api/pipeline/cleaning-stats")
        data = resp.get_json()
        assert data["before"]["count"] == 30
        assert data["after"]["area_ha"] == 1400.0

    def test_post_missing_fields_defaults_to_zero(self, client):
        resp = client.post(
            "/api/pipeline/cleaning-stats",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["stats"]["before"]["count"] == 0
        assert data["stats"]["after"]["area_ha"] == 0.0

    def test_post_saves_saved_at_timestamp(self, client):
        payload = {"before": {"count": 1, "area_ha": 10.0}, "after": {"count": 1, "area_ha": 10.0}, "removed": []}
        resp = client.post(
            "/api/pipeline/cleaning-stats",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = resp.get_json()
        assert "saved_at" in data["stats"]
        assert data["stats"]["saved_at"]  # non-empty string
