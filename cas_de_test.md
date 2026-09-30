| ID | Endpoint / param | Idée | Entrée | Attendu | Source |
|----|------------------|------|--------|---------|--------|
| C1 | q | positif | un mot d'un titre existant | l'event est dans les résultats | fonction « recherche » |
| C2 | q | casse | même mot en MAJUSCULES / minuscules | mêmes résultats | observé sur l'API : confirmé |
| C3 | q | aucune correspondance | zzz-aucun-titre-zzz | 200 + [] | logique : une recherche vide n'est pas une erreur |
| C4 | q | vide | q= | catalogue complet | vérifié : q vide = pas de filtre |
| C5 | city | positif | une ville présente | uniquement cette ville, liste non vide | fonction « filtre » |
| C6 | city | inconnue | Atlantis | 200 + [] | logique |
| C7 | city | casse | bruxelles | question ouverte (voir plus bas) | aucune spec |
| C8 | {id} | positif | id lu dans le catalogue | 200, bon id, catégories | |
| C9 | {id} | inexistant | 999999 | 404 + "Event not found" | |
| C10 | {id} | mal formé | abc, 1.5 | 422, loc = ["path", "event_id"] | validation FastAPI |
| C11 | {id} | limite basse | 0, -1 | 404 (vérifié) | |
