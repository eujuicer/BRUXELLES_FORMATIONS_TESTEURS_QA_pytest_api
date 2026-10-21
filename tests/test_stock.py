import requests

from tests.helpers import TIMEOUT, create_order


def _categorie(base_url, event_id, category_id):
    detail = requests.get(f"{base_url}/api/events/{event_id}", timeout=TIMEOUT).json()
    return next(c for c in detail["categories"] if c["id"] == category_id)


# RM1 : small_event a 3 places par catégorie. 4 billets > stock -> conflit d'état (409).
def test_stock_insuffisant_refuse_en_409(base_url, auth_headers, small_event):
    categorie = small_event["categories"][0]

    response = create_order(
        base_url, auth_headers, small_event["id"],
        [{"category_id": categorie["id"], "quantity": 4}],
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == f"Not enough stock for {categorie['name']}"


# Cas limite RM1 : commander EXACTEMENT le stock est accepté, le suivant est refusé.
def test_commander_exactement_le_stock_restant(base_url, auth_headers, small_event):
    categorie = small_event["categories"][0]
    items = [{"category_id": categorie["id"], "quantity": 3}]

    response = create_order(base_url, auth_headers, small_event["id"], items)

    assert response.status_code == 201, response.text
    assert _categorie(base_url, small_event["id"], categorie["id"])["available"] == 0
    encore_un = create_order(
        base_url, auth_headers, small_event["id"],
        [{"category_id": categorie["id"], "quantity": 1}],
    )
    assert encore_un.status_code == 409, encore_un.text
