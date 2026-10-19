from dotenv import load_dotenv
import os
import pytest
from helpers import login

load_dotenv()

@pytest.fixture(scope='session')
def base_url():
    url = os.getenv("API_URL")
    return url 

@pytest.fixture(scope="session")
def auth_headers(base_url):
    # scope="session" : un seul login pour tout le lancement de pytest.
    # Le token est seulement lu, jamais modifié par les tests, donc aucun
    # test ne peut perturber les autres. Un login par test (scope="function")
    # ferait autant d'appels inutiles à /api/auth/token.
    return login(base_url, "client@eventflow.test", "client1234")
