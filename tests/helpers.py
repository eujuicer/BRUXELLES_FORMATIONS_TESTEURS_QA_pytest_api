TIMEOUT = 5

# Contrat d'un événement du catalogue (GET /api/events), repris de la
# spécification OpenAPI publiée par EventFlow (GET /openapi.json -> EventOut).
EVENT_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "title",
        "description",
        "city",
        "venue",
        "starts_at",
        "capacity",
        "status",
        "cover_color",
    ],
    "properties": {
        "id": {"type": "integer"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "city": {"type": "string"},
        "venue": {"type": "string"},
        "starts_at": {"type": "string"},
        "capacity": {"type": "integer"},
        "status": {"type": "string"},
        "cover_color": {"type": "string"},
    },
}
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_json(relative_path):
    with open(PROJECT_ROOT / relative_path, encoding="utf-8") as f:
        return json.load(f)
