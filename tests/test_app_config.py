"""Tests for Flask config endpoints used by the dashboard sidebar."""

import pytest


@pytest.fixture
def client(monkeypatch):
    import app as app_module

    monkeypatch.setenv("DEFAULT_COMPONENT", "C2")
    monkeypatch.setenv("FOLDER_C1", r"E:\OneDrive - IUCN International Union for Conservation of Nature\AR_1_Activity\2. Smartsheet attachment\C1")
    monkeypatch.setenv("FOLDER_C2", r"E:\OneDrive - IUCN International Union for Conservation of Nature\AR_1_Activity\2. Smartsheet attachment\C2")
    monkeypatch.setenv("FOLDER_C3", r"E:\OneDrive - IUCN International Union for Conservation of Nature\AR_1_Activity\2. Smartsheet attachment\C3")
    monkeypatch.setenv("SMARTSHEET_ATTACH_DIR", r"E:\OneDrive - IUCN International Union for Conservation of Nature\AR_1_Activity\2. Smartsheet attachment")
    monkeypatch.delenv("SMARTSHEET_TOKEN", raising=False)
    monkeypatch.delenv("TOKEN", raising=False)
    # Prevent api_config() from re-reading the real .env over our monkeypatched values
    monkeypatch.setattr(app_module, "load_dotenv", lambda *a, **kw: None)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as flask_client:
        yield flask_client


def test_api_config_exposes_component_folder_defaults(client):
    response = client.get("/api/config")

    assert response.status_code == 200
    data = response.get_json()

    assert data["DEFAULT_COMPONENT"] == "C2"
    assert data["FOLDER_C1"].endswith("\\C1")
    assert data["FOLDER_C2"].endswith("\\C2")
    assert data["FOLDER_C3"].endswith("\\C3")
    assert data["SMARTSHEET_ATTACH_DIR"].endswith("2. Smartsheet attachment")
    assert data["has_token"] is False
    assert "SMARTSHEET_TOKEN" not in data


def test_ss_comments_returns_400_when_no_sheet_id(client, monkeypatch):
    """Comments endpoint returns 400 when no sheet ID is configured for the component."""
    import app as app_module
    monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "")

    response = client.post("/api/smartsheet/comments", json={"component": "C1"})

    assert response.status_code == 400


def test_ss_comments_returns_comments_dict(client, monkeypatch):
    """Comments endpoint returns a dict keyed by row ID."""
    import app as app_module
    import requests as req_module

    monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")
    monkeypatch.setattr(app_module, "_ss_headers", lambda: {"Authorization": "Bearer test"})

    class FakeResponse:
        ok = True
        def json(self):
            return {
                "data": [
                    {
                        "parentType": "ROW",
                        "parentId": 999,
                        "comments": [
                            {
                                "text": "Test comment",
                                "createdBy": {"name": "Ana"},
                                "createdAt": "2026-04-07T10:00:00Z",
                            }
                        ],
                    }
                ]
            }

    monkeypatch.setattr(app_module, "smartsheet_request", lambda *a, **kw: FakeResponse())

    response = client.post("/api/smartsheet/comments", json={"component": "C1"})

    assert response.status_code == 200
    data = response.get_json()
    assert "comments" in data
    assert data["comments"]["999"]["text"] == "Test comment"
    assert data["comments"]["999"]["author"] == "Ana"
    assert data["comments"]["999"]["date"] == "2026-04-07"