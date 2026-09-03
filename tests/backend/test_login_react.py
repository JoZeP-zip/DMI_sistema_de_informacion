"""
Pruebas de POST /login-react

Cubrimos 3 caminos del endpoint en main.py:
  1. Login exitoso -> 200 con access_token, role, email, nombre
  2. Credenciales incorrectas (res.user es None) -> 401
  3. Campos faltantes (sin email o sin password) -> 400
"""
from unittest.mock import MagicMock


def test_login_react_exitoso(client, mock_supabase_auth):
    fake_user = MagicMock()
    fake_session = MagicMock(access_token="fake-access-token-123")
    mock_supabase_auth.auth.sign_in_with_password.return_value = MagicMock(
        user=fake_user, session=fake_session
    )

    fake_query_result = MagicMock(
        data=[{
            "idusuarios": 1,
            "usuarionombre": "Kevin",
            "rol": "admin",
            "email": "kevin@example.com",
        }]
    )
    (
        mock_supabase_auth.schema.return_value
        .table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = fake_query_result

    response = client.post(
        "/login-react",
        json={"email": "kevin@example.com", "password": "claveSegura123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "fake-access-token-123"
    assert body["role"] == "admin"
    assert body["email"] == "kevin@example.com"
    assert "access_token" in response.cookies


def test_login_react_credenciales_incorrectas(client, mock_supabase_auth):
    mock_supabase_auth.auth.sign_in_with_password.return_value = MagicMock(user=None)

    response = client.post(
        "/login-react",
        json={"email": "kevin@example.com", "password": "claveMala"},
    )

    assert response.status_code == 401
    assert "message" in response.json()


def test_login_react_campos_faltantes(client, mock_supabase_auth):
    response = client.post("/login-react", json={"email": "kevin@example.com"})

    assert response.status_code == 400
    assert "message" in response.json()