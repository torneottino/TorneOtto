import pytest

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from app import create_app

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    return app

@pytest.fixture()
def client(app):
    return app.test_client()


def test_all_get_routes_return_200(client, app):
    """Itera su tutte le route senza parametri e verifica che restituiscano 200."""
    failures = []
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and not rule.arguments and not rule.rule.startswith("/static"):
            resp = client.get(rule.rule)
            if resp.status_code != 200:
                failures.append((rule.rule, resp.status_code))
    assert not failures, f"Route fallite: {failures}"
