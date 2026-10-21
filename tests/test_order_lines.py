"""Exercice 8 : règles de composition d'une commande multi-lignes (POST /api/orders).

Cas couverts (chaque test s'appuie sur un event neuf, donc indépendant et rejouable) :
  Total
    - total d'une commande à 2 lignes = somme (prix x quantité), prix lus dans le catalogue
    - total avec WELCOME10 sur 2 lignes (6 billets à 10 + 20 EUR) : -10 % sur le total
  RM3 (plafond de 6 billets PAR COMMANDE)
    - 3 + 3 sur deux catégories = 6 -> accepté (limite)
    - 4 + 3 sur deux catégories = 7 -> 400 (alors que chaque ligne est <= 6)
  Disponibilités
    - une commande décrémente le stock de chaque catégorie commandée, pas des autres
    - le stock de l'événement baisse du total de billets
  RM1 (stock)
    - une ligne OK + une ligne au-dessus du stock -> 409 et AUCUNE place réservée (atomicité)
    - 2 lignes sur la même catégorie dont la somme dépasse le stock -> doit être refusé

ANOMALIE constatée (test marqué xfail strict)
  Titre      : RM1 non respectée quand une catégorie apparaît sur plusieurs lignes
  Repro      : event avec une catégorie de 3 places ; POST /api/orders avec 2 lignes
               {category_id: X, quantity: 2} + {category_id: X, quantity: 2}
  Attendu    : 409 "Not enough stock" (4 billets demandés pour 3 places)
  Obtenu     : 201, commande acceptée, la catégorie passe à available = 0 (4 vendus pour 3)
  Règle      : RM1 (on ne vend jamais plus que le stock disponible)
  Hypothèse  : le contrôle de stock se fait ligne par ligne au lieu de cumuler par catégorie.
"""
import pytest
import requests

from tests.helpers import TIMEOUT, create_order


def _detail(base_url, event_id):
    response = requests.get(f"{base_url}/api/events/{event_id}", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return response.json()


def _dispos(base_url, event):
    detail = _detail(base_url, event["id"])
    return {c["id"]: c["available"] for c in detail["categories"]}, detail["available"]


def _lignes(event, *quantites):
    return [
        {"category_id": cat["id"], "quantity": q}
        for cat, q in zip(event["categories"], quantites)
    ]


def test_total_de_deux_lignes_est_la_somme_des_lignes(base_url, auth_headers, big_event):
    cat_a, cat_b = big_event["categories"]

    response = create_order(base_url, auth_headers, big_event["id"], _lignes(big_event, 3, 2))

    assert response.status_code == 201, response.text
    attendu = cat_a["price_cents"] * 3 + cat_b["price_cents"] * 2
    assert response.json()["total_cents"] == attendu
    assert len(response.json()["items"]) == 2


def test_code_promo_applique_10_pourcent_sur_le_total_de_deux_lignes(base_url, auth_headers, big_event):
    cat_a, cat_b = big_event["categories"]

    response = create_order(
        base_url, auth_headers, big_event["id"], _lignes(big_event, 3, 3), promo_code="WELCOME10"
    )

    assert response.status_code == 201, response.text
    brut = cat_a["price_cents"] * 3 + cat_b["price_cents"] * 3  # 9000 : divisible, pas d'arrondi
    assert response.json()["total_cents"] == brut * 90 // 100


def test_six_billets_repartis_sur_deux_lignes_acceptes(base_url, auth_headers, big_event):
    response = create_order(base_url, auth_headers, big_event["id"], _lignes(big_event, 3, 3))

    assert response.status_code == 201, response.text


def test_plafond_de_six_applique_au_cumul_des_lignes(base_url, auth_headers, big_event):
    response = create_order(base_url, auth_headers, big_event["id"], _lignes(big_event, 4, 3))

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Maximum 6 tickets per order"


def test_commande_decremente_le_stock_des_categories_commandees_seulement(base_url, auth_headers, big_event):
    cat_a, cat_b = big_event["categories"]
    avant_cats, avant_event = _dispos(base_url, big_event)

    response = create_order(base_url, auth_headers, big_event["id"], _lignes(big_event, 3, 1))

    assert response.status_code == 201, response.text
    apres_cats, apres_event = _dispos(base_url, big_event)
    assert apres_cats[cat_a["id"]] == avant_cats[cat_a["id"]] - 3
    assert apres_cats[cat_b["id"]] == avant_cats[cat_b["id"]] - 1
    assert apres_event == avant_event - 4


def test_commande_refusee_ne_reserve_aucune_place(base_url, auth_headers, make_event):
    event = make_event(20, 2)  # 2e catégorie : 2 places seulement
    avant = _dispos(base_url, event)

    response = create_order(base_url, auth_headers, event["id"], _lignes(event, 2, 3))

    assert response.status_code == 409, response.text
    assert _dispos(base_url, event) == avant  # la 1re ligne (valide) n'a pas été réservée


@pytest.mark.xfail(
    strict=True,
    reason="ANO-1 : RM1 violée, le stock n'est pas cumulé quand une catégorie est sur 2 lignes "
    "(4 billets vendus pour 3 places, 201 au lieu de 409)",
)
def test_meme_categorie_sur_deux_lignes_ne_depasse_pas_le_stock(base_url, auth_headers, small_event):
    categorie = small_event["categories"][0]  # 3 places
    lignes = [
        {"category_id": categorie["id"], "quantity": 2},
        {"category_id": categorie["id"], "quantity": 2},
    ]

    response = create_order(base_url, auth_headers, small_event["id"], lignes)

    assert response.status_code == 409, response.text
