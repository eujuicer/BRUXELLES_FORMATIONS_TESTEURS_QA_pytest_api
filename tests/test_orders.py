from tests.helpers import TIMEOUT, create_order
import requests


def test_creation_commande_deux_billets(base_url, auth_headers, get_bookable):
    event = get_bookable["event"]
    categorie = get_bookable["categorie"]
    quantite = 2

    response = create_order(
        base_url, auth_headers, event["id"],
        [{"category_id": categorie["id"], "quantity": quantite}],
    )

    assert response.status_code == 201, response.text
    commande = response.json()
    assert commande["event_id"] == event["id"]
    assert commande["status"] == "pending"
    assert commande["expires_at"] is not None
    assert len(commande["items"]) == 1
    assert commande["items"][0]["category_id"] == categorie["id"]
    assert commande["items"][0]["quantity"] == quantite
    # oracle indépendant : prix lu dans le catalogue x quantité demandée
    assert commande["total_cents"] == categorie["price_cents"] * quantite


# Partie D : on relit la commande créée
def test_commande_relue_correspond_a_la_creation(base_url, auth_headers, get_bookable):
    event = get_bookable["event"]
    categorie = get_bookable["categorie"]

    creation = create_order(
        base_url, auth_headers, event["id"],
        [{"category_id": categorie["id"], "quantity": 2}],
    )
    assert creation.status_code == 201, creation.text
    order_id = creation.json()["id"]

    response = requests.get(f"{base_url}/api/orders/{order_id}", headers=auth_headers, timeout=TIMEOUT)

    assert response.status_code == 200, response.text
    relue = response.json()
    assert relue["id"] == order_id
    assert relue["event_id"] == event["id"]
    assert relue["event_title"] == event["title"]
    assert relue["status"] == "pending"
    assert relue["total_cents"] == categorie["price_cents"] * 2
    assert relue["items"][0]["category_id"] == categorie["id"]
    assert relue["items"][0]["quantity"] == 2
