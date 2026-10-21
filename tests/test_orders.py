import pytest
import requests
from jsonschema import validate

from tests.helpers import TIMEOUT, create_order, load_json


@pytest.mark.smoke
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
    # Bonus 3 : le schéma couvre la forme (champs, types) ; restent à vérifier le métier ci-dessous
    validate(instance=commande, schema=load_json("schemas/order.schema.json"))
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


# ---------------------------------------------------------------------------
# Exercice 6 : règles métier, refus et données externalisées
# ---------------------------------------------------------------------------

CAS_QUANTITES = load_json("data/order_quantities.json")
ID_INEXISTANT = 10**9  # constante nommée : on veut un identifiant qui n'existe PAS


# Même scénario : une seule ligne, quantité variable -> statut et raison attendus (RM3 + minimum 1).
# Les billets sont pris sur big_event (neuf à chaque test) : pas de pollution du catalogue.
@pytest.mark.parametrize("cas", CAS_QUANTITES, ids=[c["cas"] for c in CAS_QUANTITES])
def test_quantite_sur_une_ligne(base_url, auth_headers, big_event, cas):
    categorie = big_event["categories"][0]

    response = create_order(
        base_url, auth_headers, big_event["id"],
        [{"category_id": categorie["id"], "quantity": cas["quantity"]}],
    )

    assert response.status_code == cas["expected_status"], response.text
    # 201 : pas de "detail" dans la réponse -> None == None ; refus : la raison doit correspondre
    assert response.json().get("detail") == cas["expected_detail"], response.text


# La limite de six porte sur la COMMANDE ENTIÈRE, pas sur la ligne : le fichier JSON
# (une seule ligne de commande) ne peut pas exprimer ce cas, d'où un test séparé.
def test_plafond_de_six_porte_sur_la_commande_entiere(base_url, auth_headers, big_event):
    cat_a, cat_b = big_event["categories"]

    response = create_order(
        base_url, auth_headers, big_event["id"],
        [{"category_id": cat_a["id"], "quantity": 4}, {"category_id": cat_b["id"], "quantity": 4}],
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Maximum 6 tickets per order"


# Même scénario : la commande référence une chose qui n'existe pas / ne correspond pas.
# L'API répond 400 "Invalid ticket category" pour tous (choix discutable : un 404 serait défendable
# pour un id inexistant ; le test documente le comportement retenu).
@pytest.mark.parametrize(
    "cas",
    ["categorie_inexistante", "categorie_d_un_autre_evenement", "evenement_inexistant"],
)
def test_reference_invalide_refusee(base_url, auth_headers, big_event, make_event, cas):
    categorie = big_event["categories"][0]
    event_id = big_event["id"]
    if cas == "categorie_inexistante":
        category_id = ID_INEXISTANT
    elif cas == "categorie_d_un_autre_evenement":
        category_id = make_event(5)["categories"][0]["id"]
    else:
        category_id, event_id = categorie["id"], ID_INEXISTANT

    response = create_order(
        base_url, auth_headers, event_id, [{"category_id": category_id, "quantity": 1}]
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Invalid ticket category"


# Même scénario : un code promo que RM4 ne permet pas d'utiliser. Le statut dépend de la raison :
# expiré = règle (400) ; inconnu = ressource introuvable (404).
@pytest.mark.parametrize(
    "promo, statut, detail",
    [
        ("EXPIRED", 400, "Promo code expired"),
        ("CODE_QUI_N_EXISTE_PAS", 404, "Unknown promo code"),
    ],
    ids=["code_expire", "code_inconnu"],
)
def test_code_promo_refuse(base_url, auth_headers, big_event, promo, statut, detail):
    categorie = big_event["categories"][0]

    response = create_order(
        base_url, auth_headers, big_event["id"],
        [{"category_id": categorie["id"], "quantity": 1}],
        promo_code=promo,
    )

    assert response.status_code == statut, response.text
    assert response.json()["detail"] == detail


# Même scénario : payload mal formé -> 422 de FastAPI, et "loc" désigne le champ incriminé.
@pytest.mark.parametrize(
    "mutation, loc_attendu",
    [
        (lambda p: p["items"][0].update(quantity="abc"), ["body", "items", 0, "quantity"]),
        (lambda p: p.pop("items"), ["body", "items"]),
        (lambda p: p.update(event_id="x"), ["body", "event_id"]),
    ],
    ids=["quantite_non_numerique", "items_absent", "event_id_non_numerique"],
)
def test_payload_mal_forme_designe_le_champ_fautif(base_url, auth_headers, big_event, mutation, loc_attendu):
    payload = {
        "event_id": big_event["id"],
        "items": [{"category_id": big_event["categories"][0]["id"], "quantity": 1}],
    }
    mutation(payload)

    response = requests.post(f"{base_url}/api/orders", json=payload, headers=auth_headers, timeout=TIMEOUT)

    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == loc_attendu


# Bonus 1 : remise WELCOME10 (-10 %). Prix 1000 cts x 2 = 2000 -> 1800 : résultat entier, pas d'arrondi
# donc oracle fiable. (Avec 24,95 EUR x 1 ou x 3 on tombe sur .5 : l'arrondi n'est pas spécifié.)
def test_welcome10_applique_10_pourcent_sur_deux_billets(base_url, auth_headers, big_event):
    categorie = big_event["categories"][0]

    response = create_order(
        base_url, auth_headers, big_event["id"],
        [{"category_id": categorie["id"], "quantity": 2}],
        promo_code="WELCOME10",
    )

    assert response.status_code == 201, response.text
    assert response.json()["total_cents"] == categorie["price_cents"] * 2 * 90 // 100
