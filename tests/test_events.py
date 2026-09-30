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