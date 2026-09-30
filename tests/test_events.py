import pytest
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 5

def test_status_is_200():
    response = requests.get(f"{BASE_URL}/api/events",timeout=TIMEOUT)
    assert response.status_code == 200, response.text


def test_content_is_json():
    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT)
    assert response.headers["content-type"].startswith("application/json")

def test_liste_vide():
    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT)
    data = response.json()
    assert len(data) > 0, "La liste d'events est vide"

def test_structure():
    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT)
    data = response.json()
    assert data, "liste vide"
    for e in data:
        assert "id" in e and type(e["id"]) == int
        assert "title" in e and type(e["title"]) == str
        assert "description" in e and type(e["description"]) == str
        assert "city" in e and type(e["city"]) == str
        assert "venue" in e and type(e["venue"]) == str
        assert "starts_at" in e and type(e["starts_at"]) == str
        assert "capacity" in e and type(e["capacity"]) == int
        assert "status" in e and type(e["status"]) == str
        assert "cover_color" in e and type(e["cover_color"]) == str



# C1 + C2 : la recherche par mot-clé retrouve l'event, quelle que soit la casse du mot.
# Le mot vient du vrai catalogue (pas en dur) ; seule la transformation de casse est paramétrée.
@pytest.mark.parametrize("transformation", [
    lambda s: s,
    str.upper,
    str.lower,
], ids=["casse_originale", "majuscules", "minuscules"])
def test_recherche_insensible_a_la_casse(transformation):
    catalogue = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT).json()
    event_reference = catalogue[0]
    mot = event_reference["title"].split()[0]

    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT, params={"q": transformation(mot)})
    assert response.status_code == 200, response.text
    events = response.json()
    ids_obtenus = [e["id"] for e in events]
    assert event_reference["id"] in ids_obtenus


# C3 : une recherche sans aucune correspondance renvoie une liste vide, pas une erreur
def test_recherche_sans_correspondance():
    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT, params={"q": "zzz-aucun-titre-zzz"})
    assert response.status_code == 200, response.text
    assert response.json() == []


# C4 : une recherche vide (q="") ne filtre rien et retourne tout le catalogue
def test_recherche_vide_retourne_tout_le_catalogue():
    catalogue = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT).json()
    ids_catalogue = {e["id"] for e in catalogue}

    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT, params={"q": ""})
    assert response.status_code == 200, response.text
    events = response.json()
    ids_obtenus = {e["id"] for e in events}

    assert ids_obtenus == ids_catalogue




