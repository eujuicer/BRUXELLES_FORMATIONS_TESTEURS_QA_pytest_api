from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import os
import uuid
import pytest
import requests

from tests.helpers import TIMEOUT, get_all_events, get_bookable_event_cat, login

load_dotenv()

@pytest.fixture(scope="session")
def base_url():
    url = os.getenv("API_URL")
    return url

@pytest.fixture
def real_event(base_url):
    response = requests.get(f"{base_url}/api/events", timeout=5)
    assert response.status_code == 200
    return response.json()[0]

@pytest.fixture(scope='session')
def auth_headers(base_url):
    email = os.getenv('EF_CLIENT_USERNAME')
    password = os.getenv('EF_CLIENT_PASSWORD')
    return login(base_url, email, password)

@pytest.fixture
def all_events(base_url):
    return get_all_events(base_url)

@pytest.fixture
def get_bookable(base_url, all_events):
    event_cat = get_bookable_event_cat(base_url, all_events, 6)
    if not event_cat:
        pytest.skip(reason="Aucun événement publié avec une catégorie ayant au moins 6 places disponibles")
    return event_cat


# session : l'organisateur ne change pas, on ne se connecte qu'une fois
@pytest.fixture(scope="session")
def orga_headers(base_url):
    """Organisateur du seed : sert uniquement à PRÉPARER des données de test."""
    return login(
        base_url,
        os.getenv("EF_ORGA_EMAIL", "orga@eventflow.test"),
        os.getenv("EF_ORGA_PASSWORD", "orga1234"),
    )


# Fabrique d'événements dédiés. Chaque appel crée un événement NEUF ; au
# teardown tous ceux créés par le test sont archivés (EventFlow n'a pas de DELETE).
# scope function : les tests réservent des places dessus, donc jamais partagé.
@pytest.fixture
def make_event(base_url, orga_headers):
    created = []

    def _make(*quotas, price_cents=1000):
        starts_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        payload = {
            "title": f"[TEST J4] {uuid.uuid4().hex[:8]}",
            "city": "Testville",
            "starts_at": starts_at.isoformat(),
            "capacity": 100,
            "categories": [
                {"name": f"Cat{i}", "price_cents": price_cents * (i + 1), "quota": quota}
                for i, quota in enumerate(quotas)
            ],
        }
        response = requests.post(
            f"{base_url}/api/admin/events", json=payload, headers=orga_headers, timeout=TIMEOUT
        )
        assert response.status_code == 201, response.text
        event = response.json()
        created.append(event)
        return event

    yield _make

    for event in created:
        requests.put(
            f"{base_url}/api/admin/events/{event['id']}",
            json={"status": "archived"},
            headers=orga_headers,
            timeout=TIMEOUT,
        )


@pytest.fixture
def small_event(make_event):
    """Event dédié : 2 catégories de 3 places (Cat0 à 10,00 €, Cat1 à 20,00 €)."""
    return make_event(3, 3)


@pytest.fixture
def big_event(make_event):
    """Event dédié avec beaucoup de stock (2 x 20) : pour les tests qui n'étudient pas le stock."""
    return make_event(20, 20)
