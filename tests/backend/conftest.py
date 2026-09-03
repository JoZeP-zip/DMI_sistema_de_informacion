"""
Fixtures compartidas para las pruebas del backend (main.py en la raíz).

IMPORTANTE:
- Al hacer `from main import app`, se ejecuta TODO el código a nivel de
  módulo de main.py, incluyendo create_engine(DATABASE_URL) y
  create_client(SUPABASE_URL, SUPABASE_KEY). Esto NO hace llamadas de
  red por sí solo (solo instancia los clientes), así que es seguro.
- Lo que SÍ debemos evitar es que los tests disparen llamadas reales a
  supabase.auth.sign_in_with_password(...) o a la base de datos.
  Por eso mockeamos main.supabase en cada test que lo necesite.
"""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client():
    """Cliente HTTP de pruebas contra tu FastAPI real."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def mock_supabase_auth(mocker):
    """
    Reemplaza main.supabase por un Mock, para que ningun test golpee
    tu proyecto Supabase real. Devuelve el mock para que cada test
    configure la respuesta que necesita.
    """
    fake_supabase = mocker.patch("main.supabase")
    return fake_supabase