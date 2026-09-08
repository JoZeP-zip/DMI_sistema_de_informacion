from main import (
    es_admin,
    es_mecanico,
    normalizar_rol_empleado
)


def test_usuario_es_admin():
    usuario = {
        "id": "123",
        "nombre": "Administrador",
        "rol": "admin"
    }

    assert es_admin(usuario) is True


def test_usuario_no_es_admin():
    usuario = {
        "id": "123",
        "nombre": "Cliente",
        "rol": "usuario"
    }

    assert es_admin(usuario) is False


def test_usuario_es_mecanico():
    usuario = {
        "id": "456",
        "nombre": "Mecanico",
        "rol": "mecanico"
    }

    assert es_mecanico(usuario) is True


def test_usuario_no_es_mecanico():
    usuario = {
        "id": "789",
        "nombre": "Cliente",
        "rol": "usuario"
    }

    assert es_mecanico(usuario) is False


def test_normalizar_rol_mecanico():
    resultado = normalizar_rol_empleado("Mecánico")

    assert resultado == "mecanico"


def test_normalizar_rol_conductor():
    resultado = normalizar_rol_empleado("Conductor de grúa")

    assert resultado == "conductor_grua"


def test_normalizar_rol_desconocido():
    resultado = normalizar_rol_empleado("Administrador")

    assert resultado is None