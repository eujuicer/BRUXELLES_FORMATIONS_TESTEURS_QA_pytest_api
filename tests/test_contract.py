import pytest
import requests
from tests.helpers import TIMEOUT, load_json, event_Array_Schema
from jsonschema import ValidationError, validate

BASE_URL = "http://localhost:8000"

EVENT_SCHEMA = load_json("schemas/event.schema.json")
CATALOGUE_SCHEMA = {"type": "array", "minItems": 1, "items": EVENT_SCHEMA}


# Partie B : un seul appel valide chaque champ de chaque événement du catalogue
def test_catalogue_respecte_le_contrat():
    response = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    validate(instance=response.json(), schema=CATALOGUE_SCHEMA)


# Partie C : le schéma doit refuser un événement abîmé.
# Sorte 1 : on retire un champ requis.
@pytest.mark.parametrize("champ", ["title", "capacity", "status"])
def test_schema_refuse_champ_manquant(champ):
    event = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT).json()[0]
    mutant = dict(event)  # copie : on ne touche pas à la vraie donnée
    del mutant[champ]

    with pytest.raises(ValidationError):
        validate(instance=mutant, schema=EVENT_SCHEMA)


# Sorte 2 : on remplace une valeur par une valeur invalide (type, borne, enum, format).
@pytest.mark.parametrize(
    "champ, valeur_invalide",
    [
        ("id", "4"),
        ("capacity", 0),
        ("status", "supprime"),
        ("cover_color", "rouge"),
    ],
)
def test_schema_refuse_valeur_invalide(champ, valeur_invalide):
    event = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT).json()[0]
    mutant = dict(event)
    mutant[champ] = valeur_invalide

    with pytest.raises(ValidationError):
        validate(instance=mutant, schema=EVENT_SCHEMA)


# Partie D : le détail d'un événement
EVENT_DETAIL_SCHEMA = load_json("schemas/event_detail.schema.json")


def test_detail_respecte_le_contrat_et_la_regle_metier():
    event_id = requests.get(f"{BASE_URL}/api/events", timeout=TIMEOUT).json()[0]["id"]
    response = requests.get(f"{BASE_URL}/api/events/{event_id}", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    detail = response.json()

    validate(instance=detail, schema=EVENT_DETAIL_SCHEMA)  # contrat : structure, types

    # métier : le schéma ne sait pas comparer deux valeurs entre elles
    assert detail["available"] <= detail["capacity"]
    assert detail["available"] == sum(c["available"] for c in detail["categories"])



def test_valide_events_schema(base_url) :
    res = requests.get(base_url+ "/api/events")
    obj = res.json()
    event_list_schema = event_Array_Schema()
    validate(obj, event_list_schema)

def test_echou_events_schema(base_url):
    res = requests.get(base_url+ "/api/events")
    obj = res.json()
    event = obj[0]
    schema = load_json("schemas/eventOut.json")
    del event["id"]
    with pytest.raises(ValidationError):
        validate(event,schema)

@pytest.mark.parametrize("key, wrong_value", [
    ("capacity", "more"),
    ("capacity", -5),
    ("capacity", 1.24),
    ("id", -5)
], ids= ["Must be a valid value", "Value must be a string", "Value must be an integer", "Id must be positive"])

def test_broken_value(real_event, key, wrong_value):
    mock_event = dict(real_event)
    mock_event[key] = wrong_value
    schema = load_json("schemas/eventOut.json")

    with pytest.raises(ValidationError):
        validate(instance=mock_event, schema=schema)
