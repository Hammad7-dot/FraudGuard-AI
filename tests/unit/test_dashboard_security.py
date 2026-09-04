from pathlib import Path


DASHBOARD = Path(__file__).parents[2] / "dashboard" / "static" / "index.html"
COMPOSE = Path(__file__).parents[2] / "docker-compose.yml"


def test_dashboard_does_not_bundle_api_key():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "dev-api-key-change-me" not in source
    assert "window.FRAUDGUARD_API_KEY" not in source


def test_dashboard_escapes_untrusted_transaction_fields():
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "escapeHtml(t.transaction_id)" in source
    assert "escapeHtml(t.user_id)" in source
    assert "escapeHtml(topReason)" in source


def test_compose_requires_operator_supplied_api_key():
    source = COMPOSE.read_text(encoding="utf-8")
    assert "dev-api-key-change-me" not in source
    assert "API_KEY: ${API_KEY:?" in source
