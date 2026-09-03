from fastapi import FastAPI, Form, Request, Cookie, Header, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
from datetime import date, datetime, time, timedelta
import calendar
from decimal import Decimal
from urllib.parse import quote, quote_plus
from urllib.parse import urlparse
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from email.message import EmailMessage
import smtplib
import ssl
import os
import html
import re
import jwt
import json
import hashlib
from sqlalchemy import text
from datetime import datetime

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ADMIN_SECRET = os.getenv("ADMIN_SECRET")

missing_environment = [
    name for name, value in {
        "DATABASE_URL": DATABASE_URL,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
    }.items() if not value
]
if missing_environment:
    raise RuntimeError(
        "Faltan variables de entorno requeridas: " + ", ".join(missing_environment)
    )
# Enlace de pago hospedado creado en el panel de Wompi. Es publico, pero se
# puede cambiar desde Vercel con la variable WOMPI_PAYMENT_LINK sin editar codigo.
WOMPI_PAYMENT_LINK = os.getenv("WOMPI_PAYMENT_LINK", "https://checkout.wompi.co/l/VPOS_OEmmOs")
WOMPI_EVENTS_SECRET = os.getenv("WOMPI_EVENTS_SECRET", "")
# Correo transaccional. En Render se configura con variables de entorno; nunca
# se escriben claves de Gmail ni proveedores externos dentro del repositorio.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)

# Forzamos a SQLAlchemy a buscar directamente en el esquema dmi
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-csearch_path=dmi,public"}
)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_SERVICE_ROLE_KEY else None
)

# URL a la que Supabase redirige despues de validar el enlace de recuperacion.
# En produccion se debe definir PASSWORD_RECOVERY_REDIRECT_URL en el archivo .env.
PASSWORD_RECOVERY_REDIRECT_URL = os.getenv(
    "PASSWORD_RECOVERY_REDIRECT_URL",
    "https://dmi-sistema-de-informacion.vercel.app/?recovery=1",
)


def obtener_url_recuperacion_segura(candidate_url: str) -> str:
    """Acepta solo URLs conocidas de la aplicacion, evitando redirecciones externas."""
    if not candidate_url:
        return PASSWORD_RECOVERY_REDIRECT_URL

    try:
        parsed = urlparse(candidate_url)
        host = (parsed.hostname or "").lower()
        is_codespaces = host.endswith(".app.github.dev")
        is_vercel = host.endswith(".vercel.app")

        # localhost sirve solo en el computador donde corre el proyecto y no
        # funciona desde correos abiertos en un celular. Se usa Vercel como
        # respaldo publico y se aceptan URLs publicas de Codespaces/Vercel.
        if parsed.scheme == "https" and (is_codespaces or is_vercel):
            return f"{parsed.scheme}://{parsed.netloc}/?recovery=1"
    except Exception:
        pass

    return PASSWORD_RECOVERY_REDIRECT_URL

app = FastAPI()

class BotBuscarClienteRequest(BaseModel):
    tipoDocumento: str
    numeroDocumento: str

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.app\.github\.dev|http://localhost:3000|http://127\.0\.0\.1:3000|http://(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}):3000|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.cache = None
SERVICIOS_BASE_DMI = [
    ("SVC001", "Reparacion de motores diesel y gasolina"),
    ("SVC002", "Venta y reparacion de computadores"),
    ("SVC003", "Servicio de grua"),
    ("SVC004", "Inyeccion electronica"),
    ("SVC005", "Scanner, programacion ECU y llaves con chip"),
    ("SVC006", "Almacen de repuestos"),
    ("SVC007", "Stage 1 Stage 2"),
    ("SVC008", "Lavado de inyectores"),
]


def asegurar_servicios_base(conn):
    """Crea los servicios principales en Supabase si aun no existen."""
    columnas = {
        row["column_name"]: row["is_nullable"]
        for row in conn.execute(text("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'dmi' AND table_name = 'servicios'
        """)).mappings().fetchall()
    }
    if not columnas:
        return

    existentes = set(
        conn.execute(text("SELECT lower(codigoservicio) FROM dmi.servicios"))
        .scalars()
        .all()
    )

    pedido_id = conn.execute(
        text("SELECT idpedido FROM dmi.pedido ORDER BY idpedido DESC LIMIT 1")
    ).scalar()
    precio_id = None
    if table_exists(conn, "dmi", "serviciosprecio"):
        precio_id = conn.execute(
            text("SELECT idserviciosprecio FROM dmi.serviciosprecio ORDER BY idserviciosprecio LIMIT 1")
        ).scalar()

    necesita_pedido = columnas.get("pedido_idpedido") == "NO"
    necesita_precio = columnas.get("serviciosprecio_idserviciosprecio") == "NO"
    if (necesita_pedido and pedido_id is None) or (necesita_precio and precio_id is None):
        return

    for codigo, descripcion in SERVICIOS_BASE_DMI:
        if codigo.lower() in existentes:
            continue

        campos = ["codigoservicio", "descripcionservicio"]
        valores = [":codigo", ":descripcion"]
        params = {"codigo": codigo, "descripcion": descripcion}

        if pedido_id is not None and "pedido_idpedido" in columnas:
            campos.append("pedido_idpedido")
            valores.append(":pedido")
            params["pedido"] = pedido_id

        if precio_id is not None and "serviciosprecio_idserviciosprecio" in columnas:
            campos.append("serviciosprecio_idserviciosprecio")
            valores.append(":precio")
            params["precio"] = precio_id

        conn.execute(
            text("INSERT INTO dmi.servicios (" + ", ".join(campos) + ") VALUES (" + ", ".join(valores) + ")"),
            params,
        )
    conn.commit()


# ==================== OBTENER USUARIO ====================
def obtener_usuario(access_token: Optional[str], request: Request = None) -> Optional[dict]:
    if not access_token and request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]

    if not access_token:
        return None
    try:
        auth_response = supabase.auth.get_user(access_token)
        auth_user = getattr(auth_response, "user", None)
        if not auth_user or not getattr(auth_user, "id", None):
            return None

        user_id = str(auth_user.id)
        email = str(getattr(auth_user, "email", "") or "").strip().lower()
        with engine.connect() as conn:
            profile_columns = table_columns(conn, "dmi", "usuarios")
            filters = ["id = :auth_id"]
            if "activo" in profile_columns:
                filters.append("COALESCE(activo, TRUE) = TRUE")
            elif "estado" in profile_columns:
                filters.append("COALESCE(lower(estado), 'activo') NOT IN ('desactivado', 'inactivo', 'inactive')")
            profile = conn.execute(
                text(
                    "SELECT idusuarios, usuarionombre, rol, email "
                    "FROM dmi.usuarios WHERE " + " AND ".join(filters) + " LIMIT 1"
                ),
                {"auth_id": user_id},
            ).mappings().fetchone()

        if profile:
            usuario = {
                "id": user_id,
                "idusuarios": profile.get("idusuarios"),
                "nombre": profile.get("usuarionombre"),
                "email": profile.get("email") or email,
                "rol": profile.get("rol") or "usuario",
            }
            rol_empleado = obtener_rol_empleado_por_email(usuario["email"])
            if rol_empleado and usuario["rol"] != "admin":
                usuario["rol"] = rol_empleado
            return usuario

        rol_empleado = obtener_rol_empleado_por_email(email)
        if rol_empleado:
            return {
                "id": user_id,
                "idusuarios": None,
                "nombre": email.split("@")[0] if email else "Mecanico",
                "email": email,
                "rol": rol_empleado,
            }
    except Exception as e:
        print("ERROR obtener_usuario:", e)
    return None


def normalizar_rol_empleado(valor) -> Optional[str]:
    rol = str(valor or "").strip().lower().replace(" ", "_").replace("-", "_")
    if "mecanic" in rol or "mecanico" in rol:
        return "mecanico"
    if "grua" in rol or "conductor" in rol:
        return "conductor_grua"
    return None


def obtener_rol_empleado_por_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    try:
        with engine.connect() as conn:
            if not table_exists(conn, "dmi", "empleados"):
                return None
            cols = table_columns(conn, "dmi", "empleados")
            email_col = "email" if "email" in cols else "correo" if "correo" in cols else None
            if not email_col:
                return None

            rol_col = next((col for col in ("rol", "cargo", "tipo", "tipo_empleado", "especialidad") if col in cols), None)
            rol_expr = rol_col if rol_col else "'mecanico'"
            sql = f"SELECT {rol_expr} AS rol_empleado FROM dmi.empleados WHERE lower({email_col}) = lower(:email)"
            if "activo" in cols:
                sql += " AND COALESCE(activo, TRUE) = TRUE"
            elif "estado" in cols:
                sql += " AND COALESCE(lower(estado), 'activo') NOT IN ('desactivado', 'inactivo', 'inactive')"
            sql += " LIMIT 1"

            row = conn.execute(text(sql), {"email": email}).mappings().fetchone()
            if not row:
                return None
            return normalizar_rol_empleado(row.get("rol_empleado")) or "mecanico"
    except Exception as e:
        print("ERROR obtener_rol_empleado_por_email:", e)
        return None

# ==================== HELPERS DE PERMISOS ====================
def es_admin(usuario: Optional[dict]) -> bool:
    return usuario is not None and usuario.get("rol") == "admin"


def es_mecanico(usuario: Optional[dict]) -> bool:
    return usuario is not None and str(usuario.get("rol") or "").lower() in {"mecanico", "mecanico_taller"}


def empleado_orden_column(conn) -> Optional[str]:
    if not table_exists(conn, "dmi", "orden_trabajo"):
        return None
    cols = table_columns(conn, "dmi", "orden_trabajo")
    for col in ("empleado_id", "mecanico_id", "empleados_idempleado"):
        if col in cols:
            return col
    return None


def obtener_empleado_actual(conn, usuario: Optional[dict]) -> Optional[dict]:
    if not usuario or not table_exists(conn, "dmi", "empleados"):
        return None
    email = usuario.get("email")
    if not email:
        return None
    cols = table_columns(conn, "dmi", "empleados")
    pk = resolve_table_pk(conn, "empleados", "idempleado") or "id"
    email_col = "email" if "email" in cols else "correo" if "correo" in cols else None
    if not email_col:
        return None
    row = conn.execute(
        text(f"SELECT *, {pk} AS idempleado FROM dmi.empleados WHERE lower({email_col}) = lower(:email) LIMIT 1"),
        {"email": email},
    ).mappings().fetchone()
    return dict(row) if row else None


def usuario_puede_gestionar_orden(conn, usuario: Optional[dict], orden_id: int) -> bool:
    if es_admin(usuario):
        return True
    if not es_mecanico(usuario):
        return False
    empleado = obtener_empleado_actual(conn, usuario)
    orden_col = empleado_orden_column(conn)
    if not empleado or not orden_col:
        return False
    return conn.execute(
        text(f"SELECT 1 FROM dmi.orden_trabajo WHERE idorden = :orden_id AND {orden_col} = :empleado_id"),
        {"orden_id": orden_id, "empleado_id": empleado.get("idempleado")},
    ).scalar() is not None


def redirect_orden(usuario: Optional[dict], orden_id: int, mensaje: str = None, ok: bool = True) -> RedirectResponse:
    base = "/admin/ordenes" if es_admin(usuario) else "/mecanico/ordenes"
    suffix = ""
    if mensaje:
        key = "success" if ok else "error"
        suffix = f"?{key}={quote(mensaje)}"
    return RedirectResponse(url=f"{base}/{orden_id}{suffix}", status_code=302)

def redirigir_sin_permiso(destino: str = "/") -> RedirectResponse:
    return RedirectResponse(
        url=f"{destino}?error={quote('No tienes permiso para realizar esta accion')}",
        status_code=302,
    )

def quiere_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept or request.headers.get("x-requested-with") == "XMLHttpRequest"

# ==================== DATOS BASE ====================
def obtener_datos_base(conn) -> tuple[list, list]:
    data  = conn.execute(text("SELECT * FROM dmi.vehiculos LIMIT 20")).fetchall()
    tipos = conn.execute(
        text("SELECT idtipovehiculos, codigotipovehiculos FROM dmi.tipovehiculos")
    ).fetchall()
    return data, tipos


def obtener_citas_panel(conn) -> list:
    return conn.execute(
        text("""
            SELECT
                c.idcita,
                c.fecha,
                c.hora,
                COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo,
                COALESCE(v.placa, 'Sin placa') AS placa,
                COALESCE(c.motivo, 'Sin motivo') AS motivo,
                COALESCE(c.estado, 'pendiente') AS estado,
                COALESCE(c.notas, '') AS notas
            FROM dmi.citas c
            LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
            ORDER BY c.fecha DESC, c.hora DESC
            LIMIT 100
        """)
    ).fetchall()


def obtener_usuarios_panel(conn) -> list:
    return conn.execute(
        text("""
            SELECT
                idusuarios,
                nombre,
                apellidos,
                documento,
                email,
                telefono,
                usuarionombre,
                tipodedocumento,
                fechadenacimiento::text AS fechadenacimiento,
                id,
                NULL AS creado_en,
                vehiculos_idvehiculo,
                NULL AS actualizado_en,
                NULL AS estado,
                COALESCE(rol, 'usuario') AS rol
            FROM dmi.usuarios
            ORDER BY idusuarios
            LIMIT 100
        """)
    ).fetchall()


def obtener_inventario_catalogo_panel(conn) -> list:
    return conn.execute(
        text("""
            SELECT
                id,
                id_original,
                codigo,
                nombre,
                precio_costo,
                precio_venta,
                cantidad,
                categoria,
                departamento,
                imagen_url,
                activo
            FROM dmi.inventario_catalogo
            ORDER BY nombre
            LIMIT 1000
        """)
    ).mappings().fetchall()




def rango_mes(valor_mes: Optional[str]):
    if not valor_mes:
        return None
    try:
        inicio = datetime.strptime(valor_mes, "%Y-%m").date().replace(day=1)
        siguiente = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
        return inicio, siguiente
    except ValueError:
        return None


def obtener_ordenes_panel(conn, mes: Optional[str] = None) -> list:
    rango = rango_mes(mes)
    filtro_mes = ""
    parametros = {}
    if rango:
        filtro_mes = "WHERE fecha_apertura >= :inicio_mes AND fecha_apertura < :fin_mes"
        parametros = {"inicio_mes": rango[0], "fin_mes": rango[1]}
    return [dict(row) for row in conn.execute(
        text(f"""
            SELECT
                idorden,
                codigo_orden,
                estado,
                prioridad,
                fecha_apertura,
                fecha_inicio,
                fecha_finalizacion,
                fecha_entrega,
                total_orden,
                cliente_id,
                cliente,
                idvehiculo,
                placa,
                marca,
                modelo,
                idoficinas,
                codigo_oficina,
                oficina
            FROM dmi.v_ordenes_resumen
            {filtro_mes}
            ORDER BY fecha_apertura DESC, idorden DESC
        """), parametros
    ).mappings().fetchall()]


def obtener_ordenes_mecanico(conn, empleado_id: int, mes: Optional[str] = None) -> list:
    orden_col = empleado_orden_column(conn)
    if not orden_col:
        return []
    rango = rango_mes(mes)
    filtro_mes = ""
    parametros = {"empleado_id": empleado_id}
    if rango:
        filtro_mes = "AND r.fecha_apertura >= :inicio_mes AND r.fecha_apertura < :fin_mes"
        parametros.update({"inicio_mes": rango[0], "fin_mes": rango[1]})
    return [dict(row) for row in conn.execute(
        text(f"""
            SELECT r.*
            FROM dmi.v_ordenes_resumen r
            JOIN dmi.orden_trabajo ot ON ot.idorden = r.idorden
            WHERE ot.{orden_col} = :empleado_id
            {filtro_mes}
            ORDER BY r.fecha_apertura DESC, r.idorden DESC
        """),
        parametros,
    ).mappings().fetchall()]


def obtener_meses_ordenes(conn, empleado_id: Optional[int] = None) -> list:
    orden_col = empleado_orden_column(conn)
    if empleado_id and not orden_col:
        return []
    origen = "dmi.v_ordenes_resumen r"
    join = f"JOIN dmi.orden_trabajo ot ON ot.idorden = r.idorden" if empleado_id else ""
    where = f"WHERE ot.{orden_col} = :empleado_id" if empleado_id else ""
    params = {"empleado_id": empleado_id} if empleado_id else {}
    meses = [dict(row) for row in conn.execute(text(f"""
        SELECT to_char(r.fecha_apertura, 'YYYY-MM') AS clave,
               EXTRACT(MONTH FROM r.fecha_apertura)::int AS numero_mes,
               EXTRACT(YEAR FROM r.fecha_apertura)::int AS anio,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE r.estado IN ('finalizada', 'facturada', 'pagada', 'entregada')) AS cumplidas
        FROM {origen}
        {join}
        {where}
        GROUP BY to_char(r.fecha_apertura, 'YYYY-MM'),
                 EXTRACT(MONTH FROM r.fecha_apertura),
                 EXTRACT(YEAR FROM r.fecha_apertura)
        ORDER BY clave DESC
    """), params).mappings().fetchall()]
    nombres_meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    for mes in meses:
        mes["etiqueta"] = f"{nombres_meses[mes['numero_mes'] - 1].capitalize()} {mes['anio']}"
    return meses


def obtener_citas_programadas_hoy(conn, empleado_id: Optional[int] = None) -> list:
    orden_col = empleado_orden_column(conn)
    if empleado_id and not orden_col:
        return []
    filtro_empleado = f"AND ot.{orden_col} = :empleado_id" if empleado_id else ""
    params = {"hoy": date.today()}
    if empleado_id:
        params["empleado_id"] = empleado_id
    return [dict(row) for row in conn.execute(text(f"""
        SELECT c.idcita, c.fecha, c.hora, c.motivo, c.estado,
               r.idorden, r.codigo_orden, r.cliente, r.placa,
               COALESCE(r.marca, '') || ' ' || COALESCE(r.modelo, '') AS vehiculo
        FROM dmi.citas c
        JOIN dmi.orden_trabajo ot ON ot.cita_id = c.idcita
        JOIN dmi.v_ordenes_resumen r ON r.idorden = ot.idorden
        WHERE c.fecha >= :hoy
          AND lower(COALESCE(c.estado, 'pendiente')) NOT IN ('cancelada', 'cancelado', 'completada')
          {filtro_empleado}
        ORDER BY c.hora ASC, c.idcita ASC
        LIMIT 10
    """), params).mappings().fetchall()]


def obtener_citas_calendario_ordenes(conn, mes: Optional[str], empleado_id: Optional[int] = None) -> list:
    """Citas vigentes del mes para mostrar la agenda/calendario operativo."""
    rango = rango_mes(mes)
    if not rango:
        return []
    orden_col = empleado_orden_column(conn)
    if empleado_id and not orden_col:
        return []
    filtro_empleado = f"AND ot.{orden_col} = :empleado_id" if empleado_id else ""
    params = {"inicio_mes": rango[0], "fin_mes": rango[1]}
    if empleado_id:
        params["empleado_id"] = empleado_id
    return [dict(row) for row in conn.execute(text(f"""
        SELECT c.idcita, c.fecha, c.hora, c.motivo, c.estado,
               COALESCE(u.nombre, 'Cliente') AS cliente,
               COALESCE(v.placa, 'Sin placa') AS placa,
               ot.idorden, ot.codigo_orden
        FROM dmi.citas c
        LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
        LEFT JOIN dmi.usuarios u
                   ON u.idusuarios = v.cliente_id
                   OR u.vehiculos_idvehiculo = v.idvehiculo
        LEFT JOIN dmi.orden_trabajo ot ON ot.cita_id = c.idcita
        WHERE c.fecha >= :inicio_mes AND c.fecha < :fin_mes
          AND lower(COALESCE(c.estado, 'pendiente')) NOT IN ('cancelada', 'cancelado', 'completada')
          {filtro_empleado}
        ORDER BY c.fecha ASC, c.hora ASC, c.idcita ASC
    """), params).mappings().fetchall()]


def obtener_citas_reprogramadas_ordenes(conn, mes: Optional[str], empleado_id: Optional[int] = None) -> list:
    """Citas aprobadas que cambiaron de fecha u hora, separadas para seguimiento."""
    if "reprogramada_en" not in table_columns(conn, "dmi", "citas"):
        return []
    rango = rango_mes(mes)
    filtro_mes = ""
    params = {}
    if rango:
        filtro_mes = "AND c.fecha >= :inicio_mes AND c.fecha < :fin_mes"
        params.update({"inicio_mes": rango[0], "fin_mes": rango[1]})
    orden_col = empleado_orden_column(conn)
    if empleado_id and not orden_col:
        return []
    filtro_empleado = f"AND ot.{orden_col} = :empleado_id" if empleado_id else ""
    if empleado_id:
        params["empleado_id"] = empleado_id
    return [dict(row) for row in conn.execute(text(f"""
        SELECT c.idcita, c.fecha, c.hora, c.motivo, c.reprogramada_en,
               COALESCE(u.nombre, 'Cliente') AS cliente,
               COALESCE(v.placa, 'Sin placa') AS placa,
               ot.idorden, ot.codigo_orden
        FROM dmi.citas c
        LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
        LEFT JOIN dmi.usuarios u
                   ON u.idusuarios = v.cliente_id
                   OR u.vehiculos_idvehiculo = v.idvehiculo
        LEFT JOIN dmi.orden_trabajo ot ON ot.cita_id = c.idcita
        WHERE c.reprogramada_en IS NOT NULL
          {filtro_mes}
          {filtro_empleado}
        ORDER BY c.fecha ASC, c.hora ASC
        LIMIT 24
    """), params).mappings().fetchall()]


def organizar_ordenes(ordenes: list) -> dict:
    """Agrupa la lista para que la pantalla no mezcle trabajo vivo con historial."""
    estados_proceso = {"abierta", "diagnostico", "aprobada", "en_reparacion"}
    estados_cierre = {"finalizada", "facturada", "pagada"}
    entregadas = [orden for orden in ordenes if str(orden.get("estado") or "").lower() == "entregada"]
    return {
        "ordenes_en_proceso": [orden for orden in ordenes if str(orden.get("estado") or "").lower() in estados_proceso],
        "cotizaciones_enviadas": [orden for orden in ordenes if str(orden.get("estado") or "").lower() == "cotizada"],
        "ordenes_por_cerrar": [orden for orden in ordenes if str(orden.get("estado") or "").lower() in estados_cierre],
        "ordenes_terminadas": sorted(entregadas, key=lambda orden: (orden.get("fecha_entrega") or orden.get("fecha_finalizacion") or orden.get("fecha_apertura") or date.min, orden.get("idorden") or 0)),
    }


def construir_calendario_mes(mes: Optional[str], citas: list) -> list:
    """Matriz semanal simple para representar las citas del mes sin JavaScript externo."""
    rango = rango_mes(mes)
    if not rango:
        return []
    inicio, _ = rango
    citas_por_dia = {}
    for cita in citas:
        fecha_cita = cita.get("fecha")
        if isinstance(fecha_cita, datetime):
            fecha_cita = fecha_cita.date()
        if isinstance(fecha_cita, date):
            citas_por_dia.setdefault(fecha_cita.day, []).append(cita)
    calendario = calendar.Calendar(firstweekday=0)
    return [
        [{"dia": dia.day, "actual": dia.month == inicio.month, "citas": citas_por_dia.get(dia.day, [])} for dia in semana]
        for semana in calendario.monthdatescalendar(inicio.year, inicio.month)
    ]


def generar_codigo_orden(conn) -> str:
    base = f"OT-{datetime.utcnow().strftime('%Y%m%d')}"
    total_dia = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM dmi.orden_trabajo
            WHERE codigo_orden LIKE :base
        """),
        {"base": f"{base}%"},
    ).scalar() or 0
    return f"{base}-{int(total_dia) + 1:04d}"
# Las comprobaciones de disponibilidad de Codespaces usan HEAD /.
# FastAPI no crea esta variante automáticamente a partir de GET.
@app.head("/", include_in_schema=False)
async def healthcheck_root():
    return HTMLResponse(status_code=200)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_placeholder():
    """Evita un 404 cuando el navegador solicita el icono del sitio."""
    return HTMLResponse(content="", status_code=204)

# ==================== PÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂGINA PRINCIPAL ====================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: str = Cookie(None)):
    data = []
    tipos = []
    usuarios_data = []
    citas_data = []
    inventario_catalogo = []
    ordenes_data = []
    empleados = []
    error_msg   = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    usuario = obtener_usuario(access_token, request)

    try:
        with engine.connect() as conn:
            data, tipos = obtener_datos_base(conn)
          
            if es_admin(usuario):
                try:
                    usuarios_data = obtener_usuarios_panel(conn)
                except Exception as e:
                    error_msg = f"No se pudieron cargar usuarios: {e}"

                try:
                    citas_data = obtener_citas_panel(conn)
                except Exception as e:
                    error_msg = f"{error_msg or ''} No se pudieron cargar citas: {e}".strip()

                try:
                    inventario_catalogo = obtener_inventario_catalogo_panel(conn)
                except Exception as e:
                    error_msg = f"{error_msg or ''} No se pudo cargar inventario: {e}".strip()

                try:
                    ordenes_data = obtener_ordenes_panel(conn)
                except Exception as e:
                    error_msg = f"{error_msg or ''} No se pudieron cargar ordenes: {e}".strip()

                try:
                    if table_exists(conn, "dmi", "empleados"):
                        empleados = [dict(row) for row in conn.execute(text("SELECT * FROM dmi.empleados LIMIT 500")).mappings().fetchall()]
                except Exception as e:
                    error_msg = f"{error_msg or ''} No se pudieron cargar empleados: {e}".strip()
    except Exception as e:
        error_msg = str(e)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data": data,
            "tipos": tipos,
            "usuarios_data": usuarios_data,
            "citas_data": citas_data,
            "inventario_catalogo": inventario_catalogo,
            "ordenes_data": ordenes_data,
            "empleados": empleados,
            "usuario": usuario,
            "success_msg": success_msg,
            "error": error_msg,
            "vehicle_to_edit": None,
        },
    )




# ==================== MODULOS ADMIN DEDICADOS ====================
def obtener_vehiculos_admin_panel(conn) -> list:
    return [dict(row) for row in conn.execute(
        text("""
            SELECT
                v.idvehiculo,
                v.codigovehiculo,
                v.descripcionvehiculo,
                v.motor,
                v.cantidad_asientos,
                v.placa,
                v.capacidad,
                v.marca,
                v.modelo,
                COALESCE(tv.codigotipovehiculos, 'Sin tipo') AS tipo_vehiculo
            FROM dmi.vehiculos v
            LEFT JOIN dmi.tipovehiculos tv ON tv.idtipovehiculos = v.tipovehiculos_idtipovehiculos
            ORDER BY v.idvehiculo DESC
            LIMIT 500
        """)
    ).mappings().fetchall()]


def contar_por_estado_citas(conn, estado: str) -> int:
    return conn.execute(
        text("SELECT COUNT(*) FROM dmi.citas WHERE lower(COALESCE(estado, 'pendiente')) = :estado"),
        {"estado": estado},
    ).scalar() or 0


@app.get("/admin/citas", response_class=HTMLResponse)
async def admin_citas(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    citas = []
    total_pendientes = 0
    total_confirmadas = 0
    total_completadas = 0
    citas_hoy = []
    empleados = []

    try:
        with engine.connect() as conn:
            hoy = datetime.now(ZoneInfo("America/Bogota")).date()
            citas_sql = """
                SELECT
                    c.idcita,
                    c.fecha,
                    c.hora,
                    c.vehiculos_idvehiculo,
                    COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo,
                    COALESCE(v.placa, 'Sin placa') AS placa,
                    COALESCE(c.motivo, 'Sin motivo') AS motivo,
                    COALESCE(c.estado, 'pendiente') AS estado,
                    COALESCE(c.notas, '') AS notas,
                    COALESCE(u.nombre, '') || ' ' || COALESCE(u.apellidos, '') AS cliente,
                    COALESCE(u.telefono, '') AS telefono,
                    COALESCE(u.email, '') AS email
                FROM dmi.citas c
                LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                LEFT JOIN dmi.usuarios u ON u.idusuarios = v.cliente_id OR u.vehiculos_idvehiculo = v.idvehiculo
            """

            def preparar_cita(row):
                cita = dict(row)
                cita["fecha"] = str(cita.get("fecha") or "")
                cita["hora"] = str(cita.get("hora") or "")
                return cita

            citas = [preparar_cita(row) for row in conn.execute(
                text(citas_sql + """
                    ORDER BY c.fecha DESC, c.hora DESC
                    LIMIT 300
                """)
            ).mappings().fetchall()]

            citas_hoy = [preparar_cita(row) for row in conn.execute(
                text(citas_sql + """
                    WHERE c.fecha::date = :hoy
                    ORDER BY c.hora ASC, c.idcita ASC
                """),
                {"hoy": hoy},
            ).mappings().fetchall()]

            if table_exists(conn, "dmi", "empleados"):
                empleados_cols = table_columns(conn, "dmi", "empleados")
                empleado_pk = resolve_table_pk(conn, "empleados", "idempleado") or "id"

                def empleado_expr(alias, candidates, sql_type="varchar"):
                    for col in candidates:
                        if col in empleados_cols:
                            return f"{col} AS {alias}"
                    return f"NULL::{sql_type} AS {alias}"

                empleados_sql = f"""
                    SELECT
                        {empleado_pk} AS idempleado,
                        {empleado_expr('nombre', ['nombre', 'nombres'])},
                        {empleado_expr('apellido', ['apellido', 'apellidos'])},
                        {empleado_expr('rol', ['rol', 'cargo', 'tipo'])},
                        {empleado_expr('estado', ['estado'])},
                        {empleado_expr('activo', ['activo'], 'boolean')}
                    FROM dmi.empleados
                """
                if "activo" in empleados_cols:
                    empleados_sql += " WHERE COALESCE(activo, TRUE) = TRUE"
                elif "estado" in empleados_cols:
                    empleados_sql += " WHERE COALESCE(lower(estado), 'activo') NOT IN ('desactivado', 'inactivo', 'inactive')"
                empleados = [dict(row) for row in conn.execute(text(empleados_sql + f" ORDER BY {empleado_pk}")).mappings().fetchall()]

            total_pendientes = contar_por_estado_citas(conn, "pendiente")
            total_confirmadas = contar_por_estado_citas(conn, "confirmada")
            total_completadas = contar_por_estado_citas(conn, "completada")
    except Exception as e:
        error_msg = f"No se pudieron cargar las citas: {e}"

    return templates.TemplateResponse(
        request=request,
        name="admin_citas.html",
        context={
            "usuario": usuario,
            "citas": citas,
            "citas_hoy": citas_hoy,
            "empleados": empleados,
            "total_citas": len(citas),
            "total_pendientes": total_pendientes,
            "total_confirmadas": total_confirmadas,
            "total_completadas": total_completadas,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


@app.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    usuarios = []

    try:
        with engine.connect() as conn:
            usuarios = [dict(row._mapping) for row in obtener_usuarios_panel(conn)]
    except Exception as e:
        error_msg = f"No se pudieron cargar los usuarios: {e}"

    total_admin = sum(1 for row in usuarios if str(row.get("rol") or "").lower() == "admin")
    total_clientes = max(len(usuarios) - total_admin, 0)

    return templates.TemplateResponse(
        request=request,
        name="admin_usuarios.html",
        context={
            "usuario": usuario,
            "usuarios": usuarios,
            "total_usuarios": len(usuarios),
            "total_admin": total_admin,
            "total_clientes": total_clientes,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


@app.get("/admin/vehiculos", response_class=HTMLResponse)
async def admin_vehiculos(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    vehiculos = []

    try:
        with engine.connect() as conn:
            vehiculos = obtener_vehiculos_admin_panel(conn)
    except Exception as e:
        error_msg = f"No se pudieron cargar los vehiculos: {e}"

    con_placa = sum(1 for row in vehiculos if row.get("placa"))
    por_definir = sum(1 for row in vehiculos if "POR DEFINIR" in str(row.get("marca") or row.get("modelo") or ""))
    total_listos = max(len(vehiculos) - por_definir, 0)

    return templates.TemplateResponse(
        request=request,
        name="admin_vehiculos.html",
        context={
            "usuario": usuario,
            "vehiculos": vehiculos,
            "total_vehiculos": len(vehiculos),
            "con_placa": con_placa,
            "por_definir": por_definir,
            "total_listos": total_listos,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


@app.get("/admin/registros", response_class=HTMLResponse)
async def admin_registros(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    return templates.TemplateResponse(
        request=request,
        name="admin_registros.html",
        context={"usuario": usuario, "success_msg": request.query_params.get("success"), "error": request.query_params.get("error")},
    )


@app.get("/admin/facturas", response_class=HTMLResponse)
async def admin_facturas(request: Request, access_token: str = Cookie(None)):
    """Historial de facturas generadas para el administrador."""
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    facturas = []

    try:
        with engine.connect() as conn:
            if not table_exists(conn, "dmi", "facturas"):
                raise RuntimeError("La tabla dmi.facturas no existe.")

            facturas = [
                dict(row) for row in conn.execute(
                    text("""
                        SELECT
                            f.idfactura,
                            f.codigo_factura,
                            f.fecha_factura,
                            f.total,
                            f.saldo,
                            f.estado,
                            f.orden_id,
                            COALESCE(
                                NULLIF(trim(concat_ws(' ', u.nombre, u.apellidos)), ''),
                                NULLIF(u.usuarionombre, ''),
                                'Cliente'
                            ) AS cliente,
                            COALESCE(u.documento::text, 'Sin documento') AS documento,
                            COALESCE(ot.codigo_orden, 'Sin orden') AS codigo_orden
                        FROM dmi.facturas f
                        LEFT JOIN dmi.usuarios u ON u.idusuarios = f.cliente_id
                        LEFT JOIN dmi.orden_trabajo ot ON ot.idorden = f.orden_id
                        ORDER BY f.fecha_factura DESC, f.idfactura DESC
                    """)
                ).mappings().fetchall()
            ]

            for factura in facturas:
                fecha = factura.get("fecha_factura")
                factura["fecha_factura"] = (
                    fecha.strftime("%d/%m/%Y %H:%M")
                    if hasattr(fecha, "strftime")
                    else str(fecha or "Sin fecha")
                )
    except Exception as e:
        error_msg = f"No se pudieron cargar las facturas: {e}"

    return templates.TemplateResponse(
        request=request,
        name="admin_facturas.html",
        context={
            "usuario": usuario,
            "facturas": facturas,
            "total_facturas": len(facturas),
            "error": error_msg,
        },
    )


# ==================== ACCIONES DE ORDENES ====================
def insert_dynamic_returning(conn, table: str, data: dict, returning: str = None):
    cols = table_columns(conn, "dmi", table)
    payload = {key: value for key, value in data.items() if key in cols}
    if not payload:
        return None
    columns_sql = ", ".join(payload.keys())
    values_sql = ", ".join(f":{key}" for key in payload.keys())
    returning_sql = f" RETURNING {returning}" if returning and returning in cols else ""
    result = conn.execute(text(f"INSERT INTO dmi.{table} ({columns_sql}) VALUES ({values_sql}){returning_sql}"), payload)
    return result.scalar() if returning_sql else None


def update_dynamic(conn, table: str, pk: str, pk_value, data: dict):
    cols = table_columns(conn, "dmi", table)
    payload = {key: value for key, value in data.items() if key in cols}
    if not payload or pk not in cols:
        return
    payload["_pk_value"] = pk_value
    assignments = ", ".join(f"{key} = :{key}" for key in payload.keys() if key != "_pk_value")
    conn.execute(text(f"UPDATE dmi.{table} SET {assignments} WHERE {pk} = :_pk_value"), payload)


def actualizar_totales_orden(conn, orden_id: int):
    total_servicios = 0
    total_repuestos = 0
    if table_exists(conn, "dmi", "detalle_servicios") and "subtotal" in table_columns(conn, "dmi", "detalle_servicios"):
        total_servicios = conn.execute(
            text("SELECT COALESCE(SUM(subtotal), 0) FROM dmi.detalle_servicios WHERE orden_id = :id"),
            {"id": orden_id},
        ).scalar() or 0
    if table_exists(conn, "dmi", "detalle_repuestos") and "subtotal" in table_columns(conn, "dmi", "detalle_repuestos"):
        total_repuestos = conn.execute(
            text("SELECT COALESCE(SUM(subtotal), 0) FROM dmi.detalle_repuestos WHERE orden_id = :id"),
            {"id": orden_id},
        ).scalar() or 0
    total_orden = float(total_servicios or 0) + float(total_repuestos or 0)
    update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {
        "total_servicios": total_servicios,
        "total_repuestos": total_repuestos,
        "total_orden": total_orden,
    })
    return total_servicios, total_repuestos, total_orden


def obtener_cotizacion_activa(conn, orden_id: int):
    """Devuelve el último borrador o la última cotización enviada de una orden."""
    if not table_exists(conn, "dmi", "cotizaciones"):
        return None
    return conn.execute(
        text("""
            SELECT * FROM dmi.cotizaciones
            WHERE orden_id = :orden_id
            ORDER BY idcotizacion DESC
            LIMIT 1
        """),
        {"orden_id": orden_id},
    ).mappings().fetchone()


def obtener_items_cotizacion(conn, cotizacion_id: int) -> list:
    if not table_exists(conn, "dmi", "cotizacion_detalles"):
        return []
    return [dict(row) for row in conn.execute(
        text("""
            SELECT * FROM dmi.cotizacion_detalles
            WHERE cotizacion_id = :cotizacion_id
            ORDER BY iddetalle_cotizacion
        """),
        {"cotizacion_id": cotizacion_id},
    ).mappings().fetchall()]


def actualizar_totales_cotizacion(conn, cotizacion_id: int):
    total = conn.execute(
        text("""
            SELECT COALESCE(SUM(subtotal), 0)
            FROM dmi.cotizacion_detalles
            WHERE cotizacion_id = :cotizacion_id
        """),
        {"cotizacion_id": cotizacion_id},
    ).scalar() or 0
    update_dynamic(conn, "cotizaciones", "idcotizacion", cotizacion_id, {
        "subtotal": total,
        "impuestos": 0,
        "descuento": 0,
        "total": total,
    })
    return float(total)


def obtener_o_crear_borrador_cotizacion(conn, orden_id: int, cliente_id: int):
    cotizacion = obtener_cotizacion_activa(conn, orden_id)
    # La restriccion de Supabase solo acepta estados como pendiente, aprobada o
    # rechazada. Una pendiente sin fecha de envio se usa como borrador interno.
    if cotizacion and cotizacion.get("estado") == "pendiente" and not cotizacion.get("enviado_en"):
        return cotizacion
    codigo = generar_codigo_documento(conn, "cotizaciones", "codigo_cotizacion", "COT")
    cotizacion_id = insert_dynamic_returning(conn, "cotizaciones", {
        "cliente_id": cliente_id,
        "codigo_cotizacion": codigo,
        "orden_id": orden_id,
        "fecha_cotizacion": datetime.now(),
        "subtotal": 0,
        "impuestos": 0,
        "descuento": 0,
        "total": 0,
        "estado": "pendiente",
    }, returning="idcotizacion")
    return conn.execute(
        text("SELECT * FROM dmi.cotizaciones WHERE idcotizacion = :id"),
        {"id": cotizacion_id},
    ).mappings().fetchone()



def registrar_historial_orden(conn, orden_id: int, tipo_evento: str, descripcion: str, costo_total: float = 0, factura_id=None):
    if not table_exists(conn, "dmi", "historial_vehiculo"):
        return
    orden = obtener_resumen_orden(conn, orden_id)
    if not orden:
        return
    insert_dynamic_returning(conn, "historial_vehiculo", {
        "cliente_id": orden.get("cliente_id"),
        "vehiculo_id": orden.get("idvehiculo") or orden.get("vehiculo_id"),
        "orden_id": orden_id,
        "factura_id": factura_id,
        "fecha_evento": datetime.now(),
        "tipo_evento": tipo_evento,
        "descripcion": descripcion,
        "kilometraje": orden.get("kilometraje_actual"),
        "costo_total": costo_total,
    })
def generar_codigo_documento(conn, table: str, column: str, prefix: str):
    base = f"{prefix}-{datetime.utcnow().strftime('%Y%m%d')}"
    if not table_exists(conn, "dmi", table) or column not in table_columns(conn, "dmi", table):
        return f"{base}-0001"
    total_dia = conn.execute(
        text(f"SELECT COUNT(*) FROM dmi.{table} WHERE {column} LIKE :base"),
        {"base": f"{base}%"},
    ).scalar() or 0
    return f"{base}-{int(total_dia) + 1:04d}"


def obtener_factura_orden(conn, orden_id: int):
    if not table_exists(conn, "dmi", "facturas"):
        return None
    return conn.execute(
        text("SELECT * FROM dmi.facturas WHERE orden_id = :id ORDER BY fecha_factura DESC LIMIT 1"),
        {"id": orden_id},
    ).mappings().fetchone()


def obtener_resumen_orden(conn, orden_id: int):
    return conn.execute(
        text("SELECT * FROM dmi.v_ordenes_resumen WHERE idorden = :id"),
        {"id": orden_id},
    ).mappings().fetchone()

# ==================== ORDENES DE TRABAJO ====================
@app.get("/mecanico", response_class=HTMLResponse)
async def mecanico_panel(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not (es_admin(usuario) or es_mecanico(usuario)):
        return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    ordenes = []
    empleado = None
    meses_ordenes = []
    notificaciones = []
    citas_hoy_ordenes = []
    citas_calendario = []
    citas_reprogramadas = []
    calendario_mes = []
    panel_ordenes = organizar_ordenes([])
    mes_seleccionado = request.query_params.get("mes")

    try:
        with engine.connect() as conn:
            if es_admin(usuario):
                meses_ordenes = obtener_meses_ordenes(conn)
                mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
                ordenes = obtener_ordenes_panel(conn, mes_seleccionado)
                citas_hoy_ordenes = obtener_citas_programadas_hoy(conn)
                citas_calendario = obtener_citas_calendario_ordenes(conn, mes_seleccionado)
                citas_reprogramadas = obtener_citas_reprogramadas_ordenes(conn, mes_seleccionado)
                panel_ordenes = organizar_ordenes(obtener_ordenes_panel(conn))
            else:
                empleado = obtener_empleado_actual(conn, usuario)
                if empleado:
                    meses_ordenes = obtener_meses_ordenes(conn, empleado.get("idempleado"))
                    mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
                    ordenes = obtener_ordenes_mecanico(conn, empleado.get("idempleado"), mes_seleccionado)

                    # Notificaciones reales del mecánico. Se cargan desde la misma
                    # tabla que utiliza /api/notificaciones y la campanita del panel.
                    if table_exists(conn, "dmi", "notificaciones"):
                        notificaciones = [
                            dict(row) for row in conn.execute(
                                text("""
                                    SELECT *
                                    FROM dmi.notificaciones
                                    WHERE empleado_id = :empleado_id
                                    ORDER BY creado_en DESC
                                    LIMIT 10
                                """),
                                {"empleado_id": empleado.get("idempleado")},
                            ).mappings().fetchall()
                        ]

                    citas_hoy_ordenes = obtener_citas_programadas_hoy(conn, empleado.get("idempleado"))
                    citas_calendario = obtener_citas_calendario_ordenes(conn, mes_seleccionado, empleado.get("idempleado"))
                    citas_reprogramadas = obtener_citas_reprogramadas_ordenes(conn, mes_seleccionado, empleado.get("idempleado"))
                    panel_ordenes = organizar_ordenes(obtener_ordenes_mecanico(conn, empleado.get("idempleado")))
                else:
                    error_msg = "Tu usuario mecanico no esta enlazado a un empleado por correo."
    except Exception as e:
        error_msg = f"No se pudieron cargar las ordenes del mecanico: {e}"

    return templates.TemplateResponse(
        request=request,
        name="panel_mecanico.html",
        context={
            "usuario": usuario,
            "modo_mecanico": True,
            "empleado_actual": empleado,
            "ordenes": ordenes,
            "total_ordenes": len(ordenes),
            "total_diagnostico": sum(1 for o in ordenes if o.get("estado") == "diagnostico"),
            "total_reparacion": sum(1 for o in ordenes if o.get("estado") == "en_reparacion"),
            "total_facturadas": sum(1 for o in ordenes if o.get("estado") in {"facturada", "pagada", "entregada"}),
            "meses_ordenes": meses_ordenes,
            "mes_seleccionado": mes_seleccionado,
            "notificaciones": notificaciones,
            "citas_hoy_ordenes": citas_hoy_ordenes,
            "citas_calendario": citas_calendario,
            "citas_reprogramadas": citas_reprogramadas,
            "calendario_mes": construir_calendario_mes(mes_seleccionado, citas_calendario),
            **panel_ordenes,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


@app.get("/mecanico/ordenes/{orden_id}", response_class=HTMLResponse)
async def mecanico_orden_detalle(orden_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not (es_admin(usuario) or es_mecanico(usuario)):
        return redirigir_sin_permiso("/")

    with engine.connect() as conn:
        if not usuario_puede_gestionar_orden(conn, usuario, orden_id):
            return RedirectResponse(url="/mecanico?error=No tienes esta orden asignada", status_code=302)
    return await admin_orden_detalle(orden_id, request, access_token)


@app.get("/admin/ordenes", response_class=HTMLResponse)
async def admin_ordenes(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    ordenes = []
    total_diagnostico = 0
    total_reparacion = 0
    total_facturadas = 0
    meses_ordenes = []
    citas_hoy_ordenes = []
    citas_calendario = []
    citas_reprogramadas = []
    panel_ordenes = organizar_ordenes([])
    mes_seleccionado = request.query_params.get("mes")

    try:
        with engine.connect() as conn:
            meses_ordenes = obtener_meses_ordenes(conn)
            mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
            ordenes = obtener_ordenes_panel(conn, mes_seleccionado)
            citas_hoy_ordenes = obtener_citas_programadas_hoy(conn)
            citas_calendario = obtener_citas_calendario_ordenes(conn, mes_seleccionado)
            citas_reprogramadas = obtener_citas_reprogramadas_ordenes(conn, mes_seleccionado)
            panel_ordenes = organizar_ordenes(obtener_ordenes_panel(conn))
            total_diagnostico = conn.execute(
                text("SELECT COUNT(*) FROM dmi.orden_trabajo WHERE estado = 'diagnostico'")
            ).scalar() or 0
            total_reparacion = conn.execute(
                text("SELECT COUNT(*) FROM dmi.orden_trabajo WHERE estado = 'en_reparacion'")
            ).scalar() or 0
            total_facturadas = conn.execute(
                text("SELECT COUNT(*) FROM dmi.orden_trabajo WHERE estado IN ('facturada', 'pagada', 'entregada')")
            ).scalar() or 0
    except Exception as e:
        error_msg = f"No se pudieron cargar las ordenes: {e}"

    return templates.TemplateResponse(
        request=request,
        name="ordenes.html",
        context={
            "usuario": usuario,
            "ordenes": ordenes,
            "total_ordenes": len(ordenes),
            "total_diagnostico": total_diagnostico,
            "total_reparacion": total_reparacion,
            "total_facturadas": total_facturadas,
            "meses_ordenes": meses_ordenes,
            "mes_seleccionado": mes_seleccionado,
            "citas_hoy_ordenes": citas_hoy_ordenes,
            "citas_calendario": citas_calendario,
            "citas_reprogramadas": citas_reprogramadas,
            "calendario_mes": construir_calendario_mes(mes_seleccionado, citas_calendario),
            **panel_ordenes,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


@app.get("/admin/empleados/{empleado_id}/ordenes", response_class=HTMLResponse)
async def admin_ordenes_empleado(empleado_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")
    mes_seleccionado = request.query_params.get("mes")
    try:
        with engine.connect() as conn:
            pk = resolve_table_pk(conn, "empleados", "idempleado") or "idempleado"
            empleado = conn.execute(text(f"SELECT * FROM dmi.empleados WHERE {pk} = :id"), {"id": empleado_id}).mappings().fetchone()
            if not empleado:
                return RedirectResponse(url="/configuracion?error=Empleado no encontrado", status_code=302)
            meses_ordenes = obtener_meses_ordenes(conn, empleado_id)
            mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
            ordenes = obtener_ordenes_mecanico(conn, empleado_id, mes_seleccionado)
            citas_hoy_ordenes = obtener_citas_programadas_hoy(conn, empleado_id)
            citas_calendario = obtener_citas_calendario_ordenes(conn, mes_seleccionado, empleado_id)
            citas_reprogramadas = obtener_citas_reprogramadas_ordenes(conn, mes_seleccionado, empleado_id)
            panel_ordenes = organizar_ordenes(obtener_ordenes_mecanico(conn, empleado_id))
            nombre_empleado = " ".join(filter(None, [empleado.get("nombre") or empleado.get("nombres"), empleado.get("apellido") or empleado.get("apellidos")]))
        return templates.TemplateResponse(request=request, name="ordenes.html", context={
            "usuario": usuario, "ordenes": ordenes, "meses_ordenes": meses_ordenes,
            "mes_seleccionado": mes_seleccionado, "empleado_filtro": nombre_empleado or f"Empleado #{empleado_id}", "empleado_filtro_id": empleado_id,
            "citas_hoy_ordenes": citas_hoy_ordenes,
            "citas_calendario": citas_calendario,
            "citas_reprogramadas": citas_reprogramadas,
            "calendario_mes": construir_calendario_mes(mes_seleccionado, citas_calendario),
            **panel_ordenes,
            "total_ordenes": len(ordenes),
            "total_diagnostico": sum(1 for o in ordenes if o.get("estado") == "diagnostico"),
            "total_reparacion": sum(1 for o in ordenes if o.get("estado") == "en_reparacion"),
            "total_facturadas": sum(1 for o in ordenes if o.get("estado") in {"facturada", "pagada", "entregada"}),
            "success_msg": request.query_params.get("success"), "error": request.query_params.get("error"),
        })
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={quote(str(e))}", status_code=302)


@app.get("/admin/ordenes/{orden_id}", response_class=HTMLResponse)
async def admin_orden_detalle(orden_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    orden = None
    diagnostico = None
    servicios = []
    repuestos = []
    factura = None
    pagos = []
    cotizacion = None
    items_cotizacion = []
    productos_inventario = []
    metodos_pago = []

    try:
        with engine.connect() as conn:
            # Cargamos el resumen de la orden y, ademas, la informacion
            # que el cliente escribio al solicitar la cita.
            #
            # La vista v_ordenes_resumen no necesariamente incluye motivo_ingreso
            # ni observaciones_cliente. Por eso los obtenemos directamente de
            # orden_trabajo y, como respaldo para ordenes antiguas, de la cita.
            orden = conn.execute(
                text("""
                    SELECT
                        r.*,
                        COALESCE(
                            NULLIF(TRIM(ot.motivo_ingreso), ''),
                            NULLIF(TRIM(c.motivo), '')
                        ) AS motivo_ingreso,
                        COALESCE(
                            NULLIF(TRIM(ot.observaciones_cliente), ''),
                            NULLIF(TRIM(c.notas), '')
                        ) AS observaciones_cliente
                    FROM dmi.v_ordenes_resumen r
                    LEFT JOIN dmi.orden_trabajo ot
                        ON ot.idorden = r.idorden
                    LEFT JOIN dmi.citas c
                        ON c.idcita = ot.cita_id
                    WHERE r.idorden = :id
                    LIMIT 1
                """),
                {"id": orden_id},
            ).mappings().fetchone()
            if not orden:
                return RedirectResponse(url="/admin/ordenes?error=Orden no encontrada", status_code=302)

            diagnosticos = [dict(row) for row in conn.execute(
                text("SELECT * FROM dmi.diagnosticos WHERE orden_id = :id ORDER BY fecha_diagnostico DESC, iddiagnostico DESC"),
                {"id": orden_id},
            ).mappings().fetchall()]
            diagnostico = diagnosticos[0] if diagnosticos else None
            servicios = [dict(row) for row in conn.execute(
                text("SELECT * FROM dmi.detalle_servicios WHERE orden_id = :id ORDER BY iddetalle_servicio"),
                {"id": orden_id},
            ).mappings().fetchall()]
            repuestos = [dict(row) for row in conn.execute(
                text("SELECT * FROM dmi.detalle_repuestos WHERE orden_id = :id ORDER BY iddetalle_repuesto"),
                {"id": orden_id},
            ).mappings().fetchall()]
            cotizacion = obtener_cotizacion_activa(conn, orden_id)
            if cotizacion:
                cotizacion = dict(cotizacion)
                items_cotizacion = obtener_items_cotizacion(conn, cotizacion["idcotizacion"])
            factura = conn.execute(
                text("SELECT * FROM dmi.facturas WHERE orden_id = :id ORDER BY fecha_factura DESC LIMIT 1"),
                {"id": orden_id},
            ).mappings().fetchone()
            if factura:
                pagos = [dict(row) for row in conn.execute(
                    text("SELECT * FROM dmi.pagos WHERE factura_id = :id ORDER BY fecha_pago DESC"),
                    {"id": factura["idfactura"]},
                ).mappings().fetchall()]
            if table_exists(conn, "dmi", "inventario_catalogo"):
                productos_inventario = [dict(row) for row in conn.execute(
                    text("""
                        SELECT id, codigo, nombre, precio_venta, cantidad
                        FROM dmi.inventario_catalogo
                        WHERE COALESCE(activo, TRUE) = TRUE
                        ORDER BY nombre
                        LIMIT 300
                    """)
                ).mappings().fetchall()]
            if table_exists(conn, "dmi", "metodopago"):
                metodos_pago = [dict(row) for row in conn.execute(
                    text("SELECT idmetodopago, descripcionmpago FROM dmi.metodopago ORDER BY idmetodopago")
                ).mappings().fetchall()]
    except Exception as e:
        error_msg = f"No se pudo cargar la orden: {e}"

    return templates.TemplateResponse(
        request=request,
        name="ordenes.html",
        context={
            "usuario": usuario,
            "modo_mecanico": es_mecanico(usuario) and not es_admin(usuario),
            "ordenes": [dict(orden)] if orden else [],
            "orden_detalle": dict(orden) if orden else None,
            "diagnostico": dict(diagnostico) if diagnostico else None,
            "diagnosticos_orden": diagnosticos,
            "servicios_orden": servicios,
            "repuestos_orden": repuestos,
            "cotizacion_orden": cotizacion,
            "items_cotizacion": items_cotizacion,
            "factura_orden": dict(factura) if factura else None,
            "pagos_orden": pagos,
            "productos_inventario": productos_inventario,
            "metodos_pago": metodos_pago,
            "total_ordenes": 1 if orden else 0,
            "total_diagnostico": len(diagnosticos),
            "total_reparacion": 1 if orden and orden.get("estado") == "en_reparacion" else 0,
            "total_facturadas": 1 if factura else 0,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )



@app.post("/admin/ordenes/{orden_id}/estado")
async def actualizar_estado_orden(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None),
    estado: str = Form(...),
):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")

    estados_validos = {
        "abierta",
        "diagnostico",
        "cotizada",
        "aprobada",
        "en_reparacion",
        "finalizada",
        "facturada",
        "pagada",
        "entregada",
        "cancelada",
    }
    if estado not in estados_validos:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error=Estado no valido", status_code=302)

    try:
        with engine.connect() as conn:
            if estado in {"aprobada", "en_reparacion"}:
                aceptada = conn.execute(
                    text("SELECT 1 FROM dmi.cotizaciones WHERE orden_id = :id AND estado = 'aprobada' LIMIT 1"),
                    {"id": orden_id},
                ).scalar()
                if not aceptada:
                    return redirect_orden(usuario, orden_id, "La reparacion requiere la aceptacion del cliente", False)
            conn.execute(
                text("UPDATE dmi.orden_trabajo SET estado = :estado WHERE idorden = :id"),
                {"estado": estado, "id": orden_id},
            )
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Estado de orden actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)

@app.post("/admin/ordenes/{orden_id}/diagnostico")
async def guardar_diagnostico_orden(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None),
    diagnostico_tecnico: str = Form(...),
    recomendacion: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token, request)

    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")

    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.diagnosticos
                    (
                        orden_id,
                        diagnostico_tecnico,
                        recomendacion,
                        fecha_diagnostico,
                        estado
                    )
                    VALUES
                    (
                        :orden_id,
                        :diagnostico,
                        :recomendacion,
                        :fecha,
                        'registrado'
                    )
                """),
                {
                    "orden_id": orden_id,
                    "diagnostico": diagnostico_tecnico,
                    "recomendacion": recomendacion,
                    "fecha": datetime.now(),
                },
            )

            registrar_historial_orden(
                conn,
                orden_id,
                "diagnostico",
                f"Diagnostico agregado: {diagnostico_tecnico}",
                0,
            )

            conn.execute(
                text("""
                    UPDATE dmi.orden_trabajo
                    SET estado = 'diagnostico'
                    WHERE idorden = :id
                """),
                {"id": orden_id},
            )

            conn.commit()

        return RedirectResponse(
            url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Diagnostico agregado correctamente",
            status_code=302,
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}",
            status_code=302,
        )

@app.post("/admin/ordenes/{orden_id}/servicio")
async def agregar_servicio_orden(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None),
    descripcion: Optional[str] = Form(None),
    cantidad: float = Form(1),
    valor_unitario: float = Form(0),
):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        cantidad = float(cantidad or 1)
        valor_unitario = float(valor_unitario or 0)
        subtotal = cantidad * valor_unitario
        with engine.connect() as conn:
            orden = conn.execute(text("SELECT estado FROM dmi.orden_trabajo WHERE idorden = :id"), {"id": orden_id}).mappings().fetchone()
            if not orden or orden.get("estado") not in {"aprobada", "en_reparacion"}:
                return redirect_orden(usuario, orden_id, "El cliente debe aprobar la cotizacion antes de registrar la reparacion", False)
            insert_dynamic_returning(conn, "detalle_servicios", {
                "orden_id": orden_id,
                "descripcion": descripcion,
                "cantidad": cantidad,
                "valor_unitario": valor_unitario,
                "subtotal": subtotal,
                "estado": "registrado",
            })
            actualizar_totales_orden(conn, orden_id)
            update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "en_reparacion"})
            registrar_historial_orden(
                conn,
                orden_id,
                "servicio",
                f"Servicio realizado: {descripcion}",
                subtotal,
            )
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Servicio agregado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)


@app.post("/admin/ordenes/{orden_id}/repuesto")
async def agregar_repuesto_orden(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None),
    inventario_id: Optional[int] = Form(None),
    descripcion: Optional[str] = Form(None),
    cantidad: float = Form(1),
    valor_unitario: float = Form(0),
):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        cantidad = float(cantidad or 1)
        valor_unitario = float(valor_unitario or 0)
        with engine.connect() as conn:
            orden = conn.execute(text("SELECT estado FROM dmi.orden_trabajo WHERE idorden = :id"), {"id": orden_id}).mappings().fetchone()
            if not orden or orden.get("estado") not in {"aprobada", "en_reparacion"}:
                return redirect_orden(usuario, orden_id, "El cliente debe aprobar la cotizacion antes de usar repuestos", False)
            if inventario_id and table_exists(conn, "dmi", "inventario_catalogo"):
                producto = conn.execute(
                    text("SELECT id, nombre, codigo, precio_venta, cantidad FROM dmi.inventario_catalogo WHERE id = :id"),
                    {"id": inventario_id},
                ).mappings().fetchone()
                if producto:
                    descripcion = descripcion or producto.get("nombre") or producto.get("codigo")
                    valor_unitario = valor_unitario or float(producto.get("precio_venta") or 0)
                    conn.execute(
                        text("UPDATE dmi.inventario_catalogo SET cantidad = GREATEST(COALESCE(cantidad, 0) - :cantidad, 0) WHERE id = :id"),
                        {"cantidad": cantidad, "id": inventario_id},
                    )
            subtotal = cantidad * valor_unitario
            insert_dynamic_returning(conn, "detalle_repuestos", {
                "orden_id": orden_id,
                "inventario_id": inventario_id,
                "descripcion": descripcion or "Repuesto sin descripcion",
                "cantidad": cantidad,
                "valor_unitario": valor_unitario,
                "subtotal": subtotal,
                "consumido": True,
                "fecha_consumo": datetime.now(),
            })
            if table_exists(conn, "dmi", "movimientos_inventario"):
                insert_dynamic_returning(conn, "movimientos_inventario", {
                    "inventario_id": inventario_id,
                    "tipo_movimiento": "salida",
                    "tipo": "salida",
                    "cantidad": cantidad,
                    "descripcion": f"Consumo en orden {orden_id}",
                    "referencia": f"OT-{orden_id}",
                    "fecha_movimiento": datetime.now(),
                })
            actualizar_totales_orden(conn, orden_id)
            update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "en_reparacion"})
            registrar_historial_orden(
                conn,
                orden_id,
                "repuesto",
                f"Repuesto usado: {descripcion or 'Repuesto sin descripcion'}",
                subtotal,
            )
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Repuesto agregado e inventario actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)


@app.post("/admin/ordenes/{orden_id}/cotizacion/legacy")
async def generar_cotizacion_orden(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None)
):
    usuario = obtener_usuario(access_token, request)

    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")

    try:
        with engine.connect() as conn:

            # Obtener la orden
            orden = conn.execute(
                text("""
                    SELECT *
                    FROM dmi.orden_trabajo
                    WHERE idorden = :id
                """),
                {"id": orden_id},
            ).mappings().fetchone()

            if not orden:
                return RedirectResponse(
                    url=f"/admin/ordenes/{orden_id}?error=La orden no existe",
                    status_code=302,
                )

            cliente_id = orden["cliente_id"]

            total_servicios, total_repuestos, total_orden = actualizar_totales_orden(
                conn,
                orden_id,
            )

            codigo = generar_codigo_documento(
                conn,
                "cotizaciones",
                "codigo_cotizacion",
                "COT",
            )

            insert_dynamic_returning(
                conn,
                "cotizaciones",
                {
                    "cliente_id": cliente_id,
                    "codigo_cotizacion": codigo,
                    "orden_id": orden_id,
                    "fecha_cotizacion": datetime.now(),
                    "subtotal": total_orden,
                    "impuestos": 0,
                    "descuento": 0,
                    "total": total_orden,
                    "estado": "pendiente",
                },
            )

            update_dynamic(
                conn,
                "orden_trabajo",
                "idorden",
                orden_id,
                {
                    "estado": "cotizada"
                },
            )

            conn.commit()

        return RedirectResponse(
            url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"CotizaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n generada correctamente",
            status_code=302,
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}",
            status_code=302,
        )

@app.post("/admin/ordenes/{orden_id}/cotizacion/item")
async def agregar_item_cotizacion(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None),
    tipo: str = Form(...),
    descripcion: Optional[str] = Form(None),
    cantidad: float = Form(1),
    valor_unitario: float = Form(0),
    inventario_id: Optional[int] = Form(None),
):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        with engine.connect() as conn:
            orden = conn.execute(text("SELECT cliente_id, estado FROM dmi.orden_trabajo WHERE idorden = :id"), {"id": orden_id}).mappings().fetchone()
            if not orden:
                return redirect_orden(usuario, orden_id, "La orden no existe", False)
            if orden.get("estado") not in {"abierta", "diagnostico"}:
                return redirect_orden(usuario, orden_id, "La cotizacion ya no se puede modificar", False)
            cotizacion = obtener_o_crear_borrador_cotizacion(conn, orden_id, orden["cliente_id"])
            cantidad = float(cantidad or 1)
            valor_unitario = float(valor_unitario or 0)
            if tipo == "repuesto" and inventario_id:
                producto = conn.execute(
                    text("SELECT nombre, codigo, precio_venta FROM dmi.inventario_catalogo WHERE id = :id"),
                    {"id": inventario_id},
                ).mappings().fetchone()
                if producto:
                    descripcion = descripcion or producto.get("nombre") or producto.get("codigo")
                    valor_unitario = valor_unitario or float(producto.get("precio_venta") or 0)
            descripcion = (descripcion or "").strip()
            if tipo not in {"servicio", "repuesto"} or cantidad <= 0 or valor_unitario < 0:
                return redirect_orden(usuario, orden_id, "Datos de item no validos", False)
            if not descripcion:
                return redirect_orden(usuario, orden_id, "Escribe la descripcion del item", False)
            insert_dynamic_returning(conn, "cotizacion_detalles", {
                "cotizacion_id": cotizacion["idcotizacion"], "tipo": tipo, "inventario_id": inventario_id,
                "descripcion": descripcion, "cantidad": cantidad, "valor_unitario": valor_unitario,
                "subtotal": cantidad * valor_unitario,
            })
            actualizar_totales_cotizacion(conn, cotizacion["idcotizacion"])
            conn.commit()
        return redirect_orden(usuario, orden_id, "Item agregado a la cotizacion")
    except Exception as e:
        return redirect_orden(usuario, orden_id, str(e), False)


@app.post("/admin/ordenes/{orden_id}/cotizacion")
async def enviar_cotizacion_orden(orden_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        with engine.connect() as conn:
            diagnostico = conn.execute(text("SELECT 1 FROM dmi.diagnosticos WHERE orden_id = :id LIMIT 1"), {"id": orden_id}).scalar()
            cotizacion = obtener_cotizacion_activa(conn, orden_id)
            if not diagnostico:
                return redirect_orden(usuario, orden_id, "Registra el diagnostico antes de enviar la cotizacion", False)
            if not cotizacion or cotizacion.get("estado") != "pendiente" or cotizacion.get("enviado_en"):
                return redirect_orden(usuario, orden_id, "Primero crea una cotizacion antes de enviarla", False)
            if not obtener_items_cotizacion(conn, cotizacion["idcotizacion"]):
                return redirect_orden(usuario, orden_id, "Agrega al menos un servicio o repuesto", False)
            total = actualizar_totales_cotizacion(conn, cotizacion["idcotizacion"])
            update_dynamic(conn, "cotizaciones", "idcotizacion", cotizacion["idcotizacion"], {"estado": "pendiente", "enviado_en": datetime.now()})
            update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "cotizada"})
            registrar_historial_orden(conn, orden_id, "cotizacion_enviada", f"Cotizacion {cotizacion.get('codigo_cotizacion')} enviada al cliente", total)
            cliente_id = conn.execute(text("SELECT cliente_id FROM dmi.orden_trabajo WHERE idorden = :id"), {"id": orden_id}).scalar()
            notificar_cliente(conn, cliente_id, "Cotización disponible", f"La cotización {cotizacion.get('codigo_cotizacion')} está lista para tu revisión.", "cotizacion_enviada", "cotizacion", cotizacion["idcotizacion"])
            notificar_administradores(conn, "Cotización enviada", f"La cotización {cotizacion.get('codigo_cotizacion')} fue enviada al cliente.", "cotizacion_enviada", "cotizacion", cotizacion["idcotizacion"], "/admin/ordenes")
            conn.commit()
        return redirect_orden(usuario, orden_id, "Cotizacion enviada al cliente")
    except Exception as e:
        return redirect_orden(usuario, orden_id, str(e), False)


@app.post("/admin/ordenes/{orden_id}/factura")
async def generar_factura_orden(orden_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        with engine.connect() as conn:
            existente = obtener_factura_orden(conn, orden_id)
            if existente:
                return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"La orden ya tiene factura", status_code=302)
            orden = obtener_resumen_orden(conn, orden_id)
            if not orden:
                return RedirectResponse(url="/admin/ordenes?error=Orden no encontrada", status_code=302)
            cotizacion_aprobada = conn.execute(
                text("SELECT idcotizacion, total FROM dmi.cotizaciones WHERE orden_id = :id AND estado = 'aprobada' ORDER BY idcotizacion DESC LIMIT 1"),
                {"id": orden_id},
            ).mappings().fetchone()
            trabajos_reparacion = (
                conn.execute(text("SELECT COUNT(*) FROM dmi.detalle_servicios WHERE orden_id = :id"), {"id": orden_id}).scalar() or 0
            ) + (
                conn.execute(text("SELECT COUNT(*) FROM dmi.detalle_repuestos WHERE orden_id = :id"), {"id": orden_id}).scalar() or 0
            )
            items_cotizados = 0
            if cotizacion_aprobada:
                items_cotizados = conn.execute(
                    text("SELECT COUNT(*) FROM dmi.cotizacion_detalles WHERE cotizacion_id = :id"),
                    {"id": cotizacion_aprobada["idcotizacion"]},
                ).scalar() or 0
            # Los items aprobados de la cotizacion tambien son facturables, aun
            # cuando el mecanico no los haya repetido en detalle_servicios o
            # detalle_repuestos durante la reparacion.
            if not cotizacion_aprobada or not (trabajos_reparacion or items_cotizados):
                return redirect_orden(usuario, orden_id, "Para facturar primero debe existir una cotizacion aprobada con servicios o repuestos", False)
            total_servicios, total_repuestos, total_orden = actualizar_totales_orden(conn, orden_id)
            if total_orden <= 0 and cotizacion_aprobada:
                total_orden = float(cotizacion_aprobada.get("total") or 0)
            codigo = generar_codigo_documento(conn, "facturas", "codigo_factura", "FAC")
            factura_id = insert_dynamic_returning(conn, "facturas", {
                "codigo_factura": codigo,
                "orden_id": orden_id,
                "cliente_id": orden.get("cliente_id"),
                "fecha_factura": datetime.now(),
                "subtotal": total_orden,
                "impuestos": 0,
                "descuento": 0,
                "total": total_orden,
                "saldo": total_orden,
                "estado": "pendiente",
            }, "idfactura")
            update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "facturada", "fecha_finalizacion": datetime.now()})
            notificar_cliente(conn, orden.get("cliente_id"), "Factura disponible", f"Tu factura {codigo} fue generada por un total de ${total_orden:,.0f}.", "factura_generada", "factura", factura_id)
            notificar_administradores(conn, "Factura generada", f"Se generó la factura {codigo} para la orden {orden.get('codigo_orden') or '#' + str(orden_id)}.", "factura_generada", "factura", factura_id, "/admin/ordenes")
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Factura generada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)


@app.post("/admin/ordenes/{orden_id}/pago")
async def registrar_pago_orden(
    orden_id: int,
    request: Request,
    access_token: str = Cookie(None),
    valor: float = Form(...),
    metodopago_id: Optional[int] = Form(None),
    referencia: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        valor = float(valor or 0)
        with engine.connect() as conn:
            factura = obtener_factura_orden(conn, orden_id)
            if not factura:
                return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error=Primero genera la factura", status_code=302)
            codigo = generar_codigo_documento(conn, "pagos", "codigo_pago", "PAG")
            insert_dynamic_returning(conn, "pagos", {
                "codigo_pago": codigo,
                "factura_id": factura["idfactura"],
                "metodopago_id": metodopago_id,
                "fecha_pago": datetime.now(),
                "valor": valor,
                "referencia": referencia,
                "estado": "confirmado",
            })
            saldo_actual = float(factura.get("saldo") or factura.get("total") or 0)
            nuevo_saldo = max(saldo_actual - valor, 0)
            estado_factura = "pagada" if nuevo_saldo <= 0 else "parcial"
            update_dynamic(conn, "facturas", "idfactura", factura["idfactura"], {"saldo": nuevo_saldo, "estado": estado_factura})
            if estado_factura == "pagada":
                update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "pagada"})
            cliente_id = conn.execute(text("SELECT cliente_id FROM dmi.orden_trabajo WHERE idorden = :id"), {"id": orden_id}).scalar()
            notificar_cliente(conn, cliente_id, "Pago registrado", f"Registramos un pago de ${valor:,.0f} para tu factura {factura.get('codigo_factura')}.", "pago_registrado", "factura", factura["idfactura"])
            notificar_administradores(conn, "Pago registrado", f"Se registró un pago de ${valor:,.0f} para la factura {factura.get('codigo_factura')}.", "pago_registrado", "factura", factura["idfactura"], "/admin/ordenes")
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Pago registrado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)


@app.post("/admin/ordenes/{orden_id}/entrega")
async def entregar_vehiculo_orden(orden_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    with engine.connect() as permiso_conn:
        if not usuario_puede_gestionar_orden(permiso_conn, usuario, orden_id):
            return redirigir_sin_permiso("/")
    try:
        with engine.connect() as conn:
            orden = obtener_resumen_orden(conn, orden_id)
            factura = obtener_factura_orden(conn, orden_id)
            update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "entregada", "fecha_entrega": datetime.now()})
            if orden and table_exists(conn, "dmi", "historial_vehiculo"):
                insert_dynamic_returning(conn, "historial_vehiculo", {
                    "cliente_id": orden.get("cliente_id"),
                    "vehiculo_id": orden.get("idvehiculo"),
                    "orden_id": orden_id,
                    "factura_id": factura.get("idfactura") if factura else None,
                    "fecha_evento": datetime.now(),
                    "tipo_evento": "entrega",
                    "descripcion": f"Vehiculo entregado desde la orden {orden.get('codigo_orden')}",
                    "costo_total": orden.get("total_orden"),
                })
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Vehiculo entregado e historial generado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)
@app.post("/admin/ordenes/desde-cita/{cita_id}")
async def crear_orden_desde_cita(cita_id: int, request: Request, access_token: str = Cookie(None), empleado_id: Optional[int] = Form(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    try:
        with engine.connect() as conn:
            cita = conn.execute(
                text("""
                    SELECT
                        c.idcita,
                        c.vehiculos_idvehiculo,
                        c.fecha,
                        c.hora,
                        c.motivo,
                        c.notas,
                        COALESCE(c.estado, 'pendiente') AS estado,
                        u.idusuarios AS cliente_id,
                        u.oficina_id,
                        v.kilometraje_actual,
                        v.combustible
                    FROM dmi.citas c
                    JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    LEFT JOIN dmi.usuarios u ON u.idusuarios = v.cliente_id OR u.vehiculos_idvehiculo = v.idvehiculo
                    WHERE c.idcita = :id
                    ORDER BY u.idusuarios
                    LIMIT 1
                """),
                {"id": cita_id},
            ).mappings().fetchone()

            if not cita:
                return RedirectResponse(url="/admin/citas?error=Cita no encontrada", status_code=302)
            if not cita["cliente_id"]:
                return RedirectResponse(url="/admin/citas?error=La cita no tiene un cliente asociado", status_code=302)

            orden_existente = conn.execute(
                text("SELECT idorden FROM dmi.orden_trabajo WHERE cita_id = :id LIMIT 1"),
                {"id": cita_id},
            ).scalar()
            if orden_existente:
                return RedirectResponse(url=f"/admin/ordenes/{orden_existente}?success=Esta cita ya tiene orden de trabajo", status_code=302)

            codigo = generar_codigo_orden(conn)
            orden_payload = {
                "codigo_orden": codigo,
                "cita_id": cita_id,
                "cliente_id": cita["cliente_id"],
                "vehiculo_id": cita["vehiculos_idvehiculo"],
                "oficina_id": cita["oficina_id"],
                "kilometraje_ingreso": cita["kilometraje_actual"] or 0,
                "combustible_ingreso": cita["combustible"],
                "motivo_ingreso": cita["motivo"],
                "observaciones_cliente": cita["notas"],
                "estado": "abierta",
            }
            orden_cols = table_columns(conn, "dmi", "orden_trabajo")
            if empleado_id:
                if "empleado_id" in orden_cols:
                    orden_payload["empleado_id"] = empleado_id
                elif "mecanico_id" in orden_cols:
                    orden_payload["mecanico_id"] = empleado_id
                elif "empleados_idempleado" in orden_cols:
                    orden_payload["empleados_idempleado"] = empleado_id

            orden_id = insert_dynamic_returning(conn, "orden_trabajo", orden_payload, "idorden")

            conn.execute(
                text("UPDATE dmi.citas SET estado = 'confirmada' WHERE idcita = :id"),
                {"id": cita_id},
            )
            notificar_cliente(conn, cita["cliente_id"], "Orden de trabajo creada", f"Creamos la orden {codigo} para tu cita. El taller iniciará la revisión.", "orden_creada", "orden", orden_id)
            notificar_administradores(conn, "Nueva orden de trabajo", f"La cita #{cita_id} fue convertida en la orden {codigo}.", "orden_creada", "orden", orden_id, "/admin/ordenes")
            if empleado_id:
                crear_notificacion(conn, "Nueva orden asignada", f"Se te asignó la orden {codigo}.", "orden_asignada", "orden", orden_id, empleado_id=empleado_id, accion_url=f"/mecanico/ordenes/{orden_id}")
            conn.commit()

        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?success=Orden de trabajo creada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/citas?error={quote(str(e))}", status_code=302)

@app.get("/admin/inventario", response_class=HTMLResponse)
async def admin_inventario(
    request: Request,
    access_token: str = Cookie(None),
    q: str = "",
    categoria: str = "",
    estado: str = "",
    page: int = 1,
):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    productos = []
    categorias = []
    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    page = max(page, 1)
    per_page = 24
    offset = (page - 1) * per_page
    params = {
        "q": f"%{q.strip()}%",
        "categoria": categoria.strip(),
        "solo_activos": estado == "activos",
        "sin_stock": estado == "sin_stock",
        "limit": per_page,
        "offset": offset,
    }

    where = ["1 = 1"]
    if q.strip():
        where.append("(nombre ILIKE :q OR codigo ILIKE :q OR categoria ILIKE :q OR departamento ILIKE :q)")
    if categoria.strip():
        where.append("categoria = :categoria")
    if estado == "activos":
        where.append("activo = TRUE")
    elif estado == "inactivos":
        where.append("activo = FALSE")
    elif estado == "sin_stock":
        where.append("cantidad <= 0")
    elif estado == "stock_bajo":
        where.append("cantidad > 0 AND cantidad <= 2")

    try:
        with engine.connect() as conn:
            total_filtrado = conn.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM dmi.inventario_catalogo
                    WHERE {' AND '.join(where)}
                """),
                params,
            ).scalar() or 0

            productos = [dict(row) for row in conn.execute(
                text(f"""
                    SELECT *
                    FROM dmi.inventario_catalogo
                    WHERE {' AND '.join(where)}
                    ORDER BY nombre
                    LIMIT :limit OFFSET :offset
                """),
                params,
            ).mappings().fetchall()]

            categorias = [row[0] for row in conn.execute(
                text("""
                    SELECT DISTINCT categoria
                    FROM dmi.inventario_catalogo
                    WHERE categoria IS NOT NULL AND categoria <> ''
                    ORDER BY categoria
                """)
            ).fetchall()]

            # Las estadisticas superiores representan TODO el inventario,
            # no solamente los productos de la pagina actual.
            resumen_inventario = conn.execute(
                text("""
                    SELECT
                        COUNT(*) AS total_productos,
                        COALESCE(SUM(COALESCE(cantidad, 0)), 0) AS stock_total,
                        COUNT(*) FILTER (
                            WHERE COALESCE(cantidad, 0) <= 0
                        ) AS sin_stock,
                        COUNT(*) FILTER (
                            WHERE COALESCE(cantidad, 0) > 0
                              AND COALESCE(cantidad, 0) <= 2
                        ) AS stock_bajo,
                        COALESCE(
                            SUM(
                                COALESCE(precio_venta, 0)
                                * COALESCE(cantidad, 0)
                            ),
                            0
                        ) AS valor_total
                    FROM dmi.inventario_catalogo
                """)
            ).mappings().first() or {}

            total_productos = int(
                resumen_inventario.get("total_productos") or 0
            )
            stock_total = int(
                resumen_inventario.get("stock_total") or 0
            )
            sin_stock = int(
                resumen_inventario.get("sin_stock") or 0
            )
            stock_bajo = int(
                resumen_inventario.get("stock_bajo") or 0
            )
            valor_total = float(
                resumen_inventario.get("valor_total") or 0
            )
    except Exception as e:
        error_msg = f"No se pudo cargar inventario: {e}"
        total_filtrado = 0
        total_productos = 0
        stock_total = 0
        sin_stock = 0
        stock_bajo = 0
        valor_total = 0

    # La paginacion depende de los filtros aplicados a la tabla.
    total_pages = max((int(total_filtrado) + per_page - 1) // per_page, 1)
    if page > total_pages:
        page = total_pages
    base_params = []
    if q.strip():
        base_params.append(f"q={quote(q.strip())}")
    if categoria.strip():
        base_params.append(f"categoria={quote(categoria.strip())}")
    if estado.strip():
        base_params.append(f"estado={quote(estado.strip())}")
    page_query_base = "&".join(base_params)

    return templates.TemplateResponse(
        request=request,
        name="inventario.html",
        context={
            "usuario": usuario,
            "productos": productos,
            "categorias": categorias,
            "q": q,
            "categoria_actual": categoria,
            "estado_actual": estado,
            "total_productos": total_productos,
            "productos_pagina": len(productos),
            "stock_total": stock_total,
            "sin_stock": sin_stock,
            "stock_bajo": stock_bajo,
            "valor_total": valor_total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1,
            "next_page": page + 1,
            "page_query_base": page_query_base,
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


@app.post("/admin/inventario/nuevo")
async def admin_inventario_nuevo(
    request: Request,
    access_token: str = Cookie(None),
    nombre: str = Form(...),
    codigo: Optional[str] = Form(None),
    precio_costo: Optional[float] = Form(0),
    precio_venta: Optional[float] = Form(0),
    cantidad: Optional[int] = Form(0),
    categoria: Optional[str] = Form(None),
    departamento: Optional[str] = Form(None),
    imagen_url: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    try:
        with engine.connect() as conn:
            nuevo_producto = conn.execute(
                text("""
                    INSERT INTO dmi.inventario_catalogo
                    (id_original, codigo, nombre, precio_costo, precio_venta, cantidad, categoria, departamento, imagen_url, activo)
                    VALUES (
                        (SELECT COALESCE(MAX(id_original), 0) + 1 FROM dmi.inventario_catalogo),
                        :codigo, :nombre, :precio_costo, :precio_venta, :cantidad, :categoria, :departamento, :imagen_url, TRUE
                    )
                    RETURNING id, nombre, codigo, cantidad
                """),
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "precio_costo": precio_costo or 0,
                    "precio_venta": precio_venta or 0,
                    "cantidad": cantidad or 0,
                    "categoria": categoria,
                    "departamento": departamento,
                    "imagen_url": imagen_url,
                },
            ).mappings().fetchone()

            # Notificacion persistente para los administradores.
            # La campanita del panel ya consulta /api/notificaciones.
            if nuevo_producto:
                notificar_administradores(
                    conn,
                    "Nuevo producto en inventario",
                    f"Se agregó el producto '{nuevo_producto.get('nombre') or 'Sin nombre'}'"
                    f" (código: {nuevo_producto.get('codigo') or 'Sin código'})"
                    f" con {int(nuevo_producto.get('cantidad') or 0)} unidades.",
                    "inventario_creado",
                    "inventario",
                    nuevo_producto.get("id"),
                    "/admin/inventario",
                    usuario_actual=usuario,
                )

            conn.commit()
        return RedirectResponse(url="/admin/inventario?success=Producto creado y notificacion enviada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/inventario?error={quote(str(e))}", status_code=302)


@app.post("/admin/inventario/{producto_id}/actualizar")
async def admin_inventario_actualizar(
    producto_id: int,
    request: Request,
    access_token: str = Cookie(None),
    nombre: str = Form(...),
    codigo: Optional[str] = Form(None),
    precio_costo: Optional[float] = Form(0),
    precio_venta: Optional[float] = Form(0),
    cantidad: Optional[int] = Form(0),
    categoria: Optional[str] = Form(None),
    departamento: Optional[str] = Form(None),
    imagen_url: Optional[str] = Form(None),
    activo: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    try:
        with engine.connect() as conn:
            producto_actualizado = conn.execute(
                text("""
                    UPDATE dmi.inventario_catalogo SET
                        codigo = :codigo,
                        nombre = :nombre,
                        precio_costo = :precio_costo,
                        precio_venta = :precio_venta,
                        cantidad = :cantidad,
                        categoria = :categoria,
                        departamento = :departamento,
                        imagen_url = :imagen_url,
                        activo = :activo,
                        actualizado_en = NOW()
                    WHERE id = :id
                    RETURNING id, nombre, codigo, cantidad, activo
                """),
                {
                    "id": producto_id,
                    "codigo": codigo,
                    "nombre": nombre,
                    "precio_costo": precio_costo or 0,
                    "precio_venta": precio_venta or 0,
                    "cantidad": cantidad or 0,
                    "categoria": categoria,
                    "departamento": departamento,
                    "imagen_url": imagen_url,
                    "activo": activo == "on",
                },
            ).mappings().fetchone()

            if not producto_actualizado:
                return RedirectResponse(
                    url="/admin/inventario?error=Producto no encontrado",
                    status_code=302,
                )

            # Notificacion persistente para los administradores.
            # Indica que un producto existente fue editado.
            notificar_administradores(
                conn,
                "Inventario actualizado",
                f"Se editó el producto '{producto_actualizado.get('nombre') or 'Sin nombre'}'"
                f" (código: {producto_actualizado.get('codigo') or 'Sin código'})."
                f" Stock actual: {int(producto_actualizado.get('cantidad') or 0)} unidades.",
                "inventario_actualizado",
                "inventario",
                producto_actualizado.get("id"),
                "/admin/inventario",
                usuario_actual=usuario,
            )

            conn.commit()
        return RedirectResponse(url="/admin/inventario?success=Producto actualizado y notificacion enviada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/inventario?error={quote(str(e))}", status_code=302)



# ==================== REGISTRO USUARIO ====================
@app.post("/registro")
async def registro(
    email: str = Form(...),
    password: str = Form(...),
    nombre: str = Form(...),
    apellidos: str = Form(...),
    documento: str = Form(...),
    tipodedocumento: str = Form(...),
    fechadenacimiento: str = Form(...),
    telefono: str = Form(...),
    usuarionombre: str = Form(...),
):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return RedirectResponse(url="/?error=No se pudo registrar", status_code=302)

        supabase.schema("dmi").table("usuarios").insert(
            {
                "id": res.user.id,
                "usuarionombre": usuarionombre,
                "nombre": nombre,
                "apellidos": apellidos,
                "email": email,
                "documento": documento,
                "tipodedocumento": tipodedocumento,
                "fechadenacimiento": fechadenacimiento,
                "telefono": telefono,
                "rol": "usuario",   
            }
        ).execute()

        return RedirectResponse(url="/?success=Usuario registrado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


@app.post("/registro-react")
async def registro_react(request: Request):
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else dict(await request.form())
        email = body.get("email")
        password = body.get("password")
        nombre = body.get("nombre")
        apellidos = body.get("apellidos") or body.get("apellido") or ""
        documento = body.get("documento")
        documento_generado = not documento or str(documento).strip() in ("0", "")
        if documento_generado:
            documento = int(datetime.now().strftime("%m%d%H%M%S"))
        tipodedocumento = body.get("tipodedocumento") or body.get("tipoDocumento") or "CC"
        fechadenacimiento = body.get("fechadenacimiento") or body.get("fechaNacimiento") or "2000-01-01"
        telefono = body.get("telefono") or ""
        usuarionombre = body.get("usuarionombre") or body.get("nombreUsuario") or nombre

        required = {
            "email": email,
            "password": password,
            "nombre": nombre,
            "usuarionombre": usuarionombre,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            return JSONResponse({"error": f"Faltan campos obligatorios: {', '.join(missing)}"}, status_code=400)

        with engine.connect() as conn:
            existing_email = conn.execute(
                text("SELECT 1 FROM dmi.usuarios WHERE lower(email) = lower(:email) LIMIT 1"),
                {"email": email},
            ).first()
            if existing_email:
                return JSONResponse(
                    {"error": "Este correo ya esta registrado. Inicia sesion o usa otro correo."},
                    status_code=400,
                )

            if not documento_generado:
                existing_doc = conn.execute(
                    text("SELECT 1 FROM dmi.usuarios WHERE documento = :documento LIMIT 1"),
                    {"documento": documento},
                ).first()
                if existing_doc:
                    return JSONResponse(
                        {"error": "Este documento ya esta registrado. Inicia sesion o revisa los datos."},
                        status_code=400,
                    )
            else:
                while conn.execute(
                    text("SELECT 1 FROM dmi.usuarios WHERE documento = :documento LIMIT 1"),
                    {"documento": documento},
                ).first():
                    documento = int(documento) + 1

        # Estos datos se conservan temporalmente en Auth hasta que el PIN sea
        # confirmado; asi dmi.usuarios no recibe cuentas sin verificar.
        registration_metadata = {
            "usuarionombre": usuarionombre,
            "nombre": nombre,
            "apellidos": apellidos,
            "email": email,
            "documento": documento,
            "tipodedocumento": tipodedocumento,
            "fechadenacimiento": fechadenacimiento,
            "telefono": telefono,
            "rol": body.get("role") or body.get("rol") or "usuario",
        }

        try:
            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": registration_metadata},
            })
        except Exception as auth_error:
            auth_text = str(auth_error).lower()
            if (
                "already registered" in auth_text
                or "already exists" in auth_text
                or "user_exists" in auth_text
                or "user already registered" in auth_text
                or ("email" in auth_text and "exists" in auth_text)
            ):
                return JSONResponse(
                    {"error": "Este correo ya tiene una cuenta. Inicia sesion o recupera la contraseÃ±a."},
                    status_code=400,
                )
            raise auth_error

        if not res.user:
            return JSONResponse({"error": "No se pudo registrar el usuario. Intenta con otro correo."}, status_code=400)

        identities = getattr(res.user, "identities", None)
        if identities == []:
            return JSONResponse(
                {"error": "Este correo ya tiene una cuenta. Inicia sesion o usa otro correo."},
                status_code=400,
            )

        return JSONResponse({
            "success": True,
            "requiresVerification": True,
            "message": "Te enviamos un codigo de confirmacion a tu correo.",
        })
    except Exception as e:
        print("ERROR registro-react:", e)
        error_text = str(e).lower()
        if "rate limit" in error_text or "email rate limit" in error_text:
            return JSONResponse(
                {
                    "error": "Se alcanzo temporalmente el limite de correos de confirmacion. Espera unos minutos antes de solicitar otro codigo.",
                    "code": "EMAIL_RATE_LIMIT",
                },
                status_code=429,
            )
        if "usuarios_email" in error_text or ("email" in error_text and "duplicate" in error_text):
            return JSONResponse(
                {"error": "Este correo ya esta registrado. Inicia sesion o usa otro correo."},
                status_code=400,
            )
        if "usuarios_documento_key" in error_text or ("documento" in error_text and "duplicate" in error_text) or "duplicate key" in error_text:
            return JSONResponse(
                {"error": "Ya existe una cuenta registrada con esos datos. Revisa el correo o inicia sesion."},
                status_code=400,
            )
        return JSONResponse({"error": f"No se pudo registrar el usuario: {str(e)[:180]}"}, status_code=500)


@app.post("/registro-react/verificar")
async def verificar_registro_react(request: Request):
    """Confirma el PIN de Supabase y crea el perfil DMI solo despues del correo."""
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else dict(await request.form())
        email = str(body.get("email") or "").strip().lower()
        redirect_url = obtener_url_recuperacion_segura(str(body.get("redirect_url") or "").strip())
        pin = str(body.get("pin") or "").strip()

        if not email or not pin.isdigit() or len(pin) != 8:
            return JSONResponse({"error": "Ingresa el codigo de 8 digitos enviado a tu correo."}, status_code=400)

        verification = supabase.auth.verify_otp({
            "email": email,
            "token": pin,
            "type": "signup",
        })
        user = verification.user
        if not user:
            return JSONResponse({"error": "El codigo no es valido o ya vencio."}, status_code=400)

        metadata = getattr(user, "user_metadata", {}) or {}
        usuario_payload = {
            "id": user.id,
            "usuarionombre": metadata.get("usuarionombre") or email.split("@")[0],
            "nombre": metadata.get("nombre") or "",
            "apellidos": metadata.get("apellidos") or "",
            "email": email,
            "documento": metadata.get("documento"),
            "tipodedocumento": metadata.get("tipodedocumento") or "CC",
            "fechadenacimiento": metadata.get("fechadenacimiento") or "2000-01-01",
            "telefono": metadata.get("telefono") or "",
            "rol": metadata.get("rol") or "usuario",
        }

        # Un segundo envio del mismo PIN no crea registros duplicados.
        existing_profile = (
            supabase.schema("dmi").table("usuarios").select("idusuarios").eq("id", user.id).execute()
        )
        if not existing_profile.data:
            with engine.connect() as conn:
                existing_documento = conn.execute(
                    text("SELECT 1 FROM dmi.usuarios WHERE documento = :documento LIMIT 1"),
                    {"documento": usuario_payload["documento"]},
                ).first()
            if existing_documento:
                return JSONResponse({"error": "Ya existe una cuenta con ese documento."}, status_code=400)

            supabase.schema("dmi").table("usuarios").insert(usuario_payload).execute()

        return JSONResponse({"success": True, "message": "Correo confirmado y cuenta creada correctamente."})
    except Exception as e:
        print("ERROR registro-react/verificar:", e)
        return JSONResponse({"error": "El codigo no es valido, ya vencio o no se pudo confirmar la cuenta."}, status_code=400)


# ==================== LOGIN / LOGOUT ====================
@app.post("/password-recovery/request")
async def solicitar_recuperacion_password(request: Request):
    """Envia el correo de recuperacion sin revelar si una cuenta existe."""
    generic_response = {
        "success": True,
        "message": "Si el correo esta registrado, recibiras las instrucciones para restablecer tu contrasena.",
    }

    try:
        body = await request.json()
        email = str(body.get("email") or "").strip().lower()
        redirect_url = obtener_url_recuperacion_segura(
            str(body.get("redirect_url") or "").strip()
        )

        # La misma respuesta para correos invalidos, inexistentes o validos evita
        # que este endpoint se use para enumerar cuentas registradas.
        if not email or "@" not in email:
            return JSONResponse(generic_response)

        supabase.auth.reset_password_email(
            email,
            {"redirect_to": redirect_url},
        )
    except Exception as e:
        # No se revela si una cuenta existe, pero si se informa un problema global
        # de entrega (por ejemplo, el limite de correos del proyecto).
        print("ERROR password-recovery/request:", e)
        error_text = str(e).lower()
        if "rate limit" in error_text or "email rate" in error_text or "too many requests" in error_text:
            return JSONResponse(
                {
                    "error": "Se alcanzo temporalmente el limite de correos de recuperacion. Espera una hora antes de solicitar otro enlace.",
                    "code": "EMAIL_RATE_LIMIT",
                },
                status_code=429,
            )
        return JSONResponse(
            {
                "error": "No fue posible solicitar el correo de recuperacion. Revisa la configuracion de correo de Supabase e intentalo nuevamente.",
                "code": "PASSWORD_RECOVERY_UNAVAILABLE",
            },
            status_code=502,
        )

    return JSONResponse(generic_response)


@app.post("/password-recovery/reset")
async def restablecer_password(request: Request):
    """Actualiza la contrasena usando la sesion temporal del enlace de Supabase."""
    try:
        body = await request.json()
        access_token = str(body.get("access_token") or "").strip()
        refresh_token = str(body.get("refresh_token") or "").strip()
        password = str(body.get("password") or "")

        if not access_token or not refresh_token:
            return JSONResponse(
                {"error": "El enlace de recuperacion no es valido o ya vencio."},
                status_code=400,
            )

        if len(password) < 8:
            return JSONResponse(
                {"error": "La contrasena debe tener al menos 8 caracteres."},
                status_code=400,
            )

        recovery_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        recovery_client.auth.set_session(access_token, refresh_token)
        recovery_client.auth.update_user({"password": password})

        return JSONResponse({"success": True, "message": "Contrasena actualizada correctamente."})
    except Exception as e:
        print("ERROR password-recovery/reset:", e)
        return JSONResponse(
            {"error": "El enlace de recuperacion no es valido, ya vencio o ya fue utilizado."},
            status_code=400,
        )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.hostname
        or ""
    ).split(",")[0].strip()
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme

    if host in ("localhost", "127.0.0.1"):
        return RedirectResponse(url="http://localhost:3000/login", status_code=302)

    if host.endswith(".app.github.dev"):
        frontend_host = host.replace("-8000.app.github.dev", "-3000.app.github.dev")
        return RedirectResponse(url=f"{scheme}://{frontend_host}/login", status_code=302)

    return RedirectResponse(url="/", status_code=302)


@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not res.user:
            return RedirectResponse(url="/?error=Credenciales incorrectas", status_code=302)

        usuario_tmp = obtener_usuario(res.session.access_token)
        destino = "/mecanico?success=Inicio de sesion exitoso" if es_mecanico(usuario_tmp) else "/?success=Inicio de sesion exitoso"
        response = RedirectResponse(url=destino, status_code=302)
        response.set_cookie(
            key="access_token",
            value=res.session.access_token,
            httponly=True,
            samesite="none",
            secure=True,
        )
        return response
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)



@app.post("/login-react")
async def login_react(request: Request):
    try:
        body = await request.json()
        email = str(body.get("email") or "").strip().lower()
        password = str(body.get("password") or "")

        if not email or not password:
            return JSONResponse({"message": "Correo y contraseÃ±a son obligatorios"}, status_code=400)

        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password.strip()
        })

        if not res.user:
            return JSONResponse({"message": "Credenciales incorrectas"}, status_code=401)

        usuario = obtener_usuario(res.session.access_token)
        if not usuario:
            return JSONResponse(
                {"message": "Tu cuenta no tiene un perfil activo en DMI."},
                status_code=401,
            )

        response = JSONResponse({
            "access_token": res.session.access_token,
            "token": res.session.access_token,
            "role": usuario["rol"],
            "rol": usuario["rol"],
            "email": usuario["email"],
            "nombre": usuario["nombre"],
        })

        response.set_cookie(
            key="access_token",
            value=res.session.access_token,
            httponly=True,
            samesite="none",
            secure=True,
        )

        return response

    except Exception as e:
        error_text = str(e)
        if "Invalid login credentials" in error_text or "invalid login credentials" in error_text.lower():
            try:
                body = await request.json()
            except Exception:
                body = {}
            email = str(body.get("email") or "").strip().lower()
            existe_en_tablas = False
            try:
                with engine.connect() as conn:
                    if email and table_exists(conn, "dmi", "usuarios"):
                        existe_en_tablas = conn.execute(
                            text("SELECT 1 FROM dmi.usuarios WHERE lower(email) = :email LIMIT 1"),
                            {"email": email},
                        ).first() is not None
                    if not existe_en_tablas and email and table_exists(conn, "dmi", "empleados"):
                        cols = table_columns(conn, "dmi", "empleados")
                        email_col = "email" if "email" in cols else "correo" if "correo" in cols else None
                        if email_col:
                            existe_en_tablas = conn.execute(
                                text(f"SELECT 1 FROM dmi.empleados WHERE lower({email_col}) = :email LIMIT 1"),
                                {"email": email},
                            ).first() is not None
            except Exception:
                existe_en_tablas = False

            mensaje = "Correo o contraseÃ±a incorrectos"
            if existe_en_tablas:
                mensaje = "El correo existe en la base de datos, pero no coincide con Supabase Auth. Revisa la contraseÃ±a o crea la cuenta de acceso en Supabase Authentication."
            return JSONResponse({"message": mensaje}, status_code=401)

        print("ERROR login-react:", e)
        return JSONResponse(
            {"message": "Error al iniciar sesion", "detail": error_text},
            status_code=500
        )


@app.get("/api/auth/session")
async def validar_sesion_react(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not usuario:
        return JSONResponse(
            {"error": "Tu sesion ya no es valida o tu cuenta ya no existe."},
            status_code=401,
        )

    return JSONResponse({
        "email": usuario["email"],
        "role": usuario["rol"],
        "rol": usuario["rol"],
        "nombre": usuario["nombre"],
    })


@app.post("/logout")
async def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    response = RedirectResponse(
        url="/?success=SesiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n cerrada correctamente",
        status_code=302
    )

    response.delete_cookie("access_token", path="/", samesite="none", secure=True)
    return response


@app.get("/logout-login")
async def logout_login():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/", samesite="none", secure=True)
    return response


# ==================== PROMOVER A ADMIN ====================
@app.post("/admin/promover")
async def promover_admin(
    usuario_id: str = Form(...),
    secret: str = Form(...),
    access_token: str = Cookie(None),
):
    if secret != ADMIN_SECRET:
        return RedirectResponse(
            url="/?error=Clave secreta incorrecta",
            status_code=302
        )

    try:
        supabase.schema("dmi").table("usuarios") \
            .update({"rol": "admin"}) \
            .eq("id", usuario_id) \
            .execute()

        return RedirectResponse(
            url="/?success=Usuario promovido a administrador",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/?error={str(e)}",
            status_code=302
        )


# ==================== CREAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
@app.post("/vehiculo/nuevo")
async def crear_vehiculo(
    request: Request,
    access_token: str = Cookie(None),
    authorization: Optional[str] = Header(None),
    codigovehiculo: str = Form(...),
    placa: str = Form(...),
    marca: str = Form(...),
    tipovehiculos_idtipovehiculos: str = Form(...),
    descripcionvehiculo: Optional[str] = Form(None),
    motor: Optional[str] = Form(None),
    shadow_asientos: Optional[str] = Form(None),  
    cantidad_asientos: Optional[str] = Form(None),
    capacidad: Optional[str] = Form(None),
    modelo: Optional[str] = Form(None),
):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]

    usuario = obtener_usuario(access_token, request)

    if not usuario:
        if quiere_json(request):
            return JSONResponse(
                {"error": "Debes iniciar sesion"},
                status_code=401
            )

        return RedirectResponse(
            url="/?error=Debes iniciar sesion",
            status_code=302
        )
    try:
        with engine.connect() as conn:
            vehiculo_cols = table_columns(conn, "dmi", "vehiculos")
            usuario_id = usuario.get("idusuarios")

            # La placa es unica en Supabase. Si el usuario vuelve a enviar el
            # formulario por una recarga o doble clic, se reutiliza su vehiculo
            # existente y no se intenta crear un duplicado.
            placa_normalizada = (placa or "").strip().upper()
            existente = conn.execute(
                text("SELECT idvehiculo, cliente_id FROM dmi.vehiculos WHERE UPPER(placa) = :placa LIMIT 1"),
                {"placa": placa_normalizada},
            ).mappings().fetchone()
            if existente:
                pertenece_al_usuario = (
                    "cliente_id" not in vehiculo_cols
                    or existente.get("cliente_id") in (None, usuario_id)
                )
                if pertenece_al_usuario:
                    if "cliente_id" in vehiculo_cols and usuario_id and existente.get("cliente_id") is None:
                        conn.execute(
                            text("UPDATE dmi.vehiculos SET cliente_id = :cliente_id WHERE idvehiculo = :id"),
                            {"cliente_id": usuario_id, "id": existente["idvehiculo"]},
                        )
                    conn.execute(
                        text("UPDATE dmi.usuarios SET vehiculos_idvehiculo = COALESCE(vehiculos_idvehiculo, :vid) WHERE id = :uid"),
                        {"vid": existente["idvehiculo"], "uid": usuario["id"]},
                    )
                    conn.commit()
                    if quiere_json(request):
                        return JSONResponse({"success": True, "message": "Este vehiculo ya estaba registrado en tu cuenta.", "idvehiculo": existente["idvehiculo"]})
                    return RedirectResponse(url="/?success=Este vehiculo ya estaba registrado en tu cuenta", status_code=302)

                mensaje = "La placa ingresada ya esta registrada para otro usuario."
                if quiere_json(request):
                    return JSONResponse({"error": mensaje}, status_code=409)
                return RedirectResponse(url=f"/?error={quote(mensaje)}", status_code=302)

            if "cliente_id" in vehiculo_cols and usuario_id:
                total_vehiculos = conn.execute(
                    text("SELECT COUNT(*) FROM dmi.vehiculos WHERE cliente_id = :cliente_id"),
                    {"cliente_id": usuario_id},
                ).scalar() or 0
                if total_vehiculos >= 10:
                    mensaje = "Solo puedes registrar hasta 10 vehiculos en tu cuenta."
                    if quiere_json(request):
                        return JSONResponse({"error": mensaje}, status_code=400)
                    return RedirectResponse(url=f"/?error={mensaje}", status_code=302)

            payload = {
                "codigovehiculo": codigovehiculo,
                "descripcionvehiculo": descripcionvehiculo,
                "motor": motor,
                "cantidad_asientos": cantidad_asientos,
                "placa": placa_normalizada,
                "capacidad": capacidad,
                "marca": marca,
                "tipovehiculos_idtipovehiculos": tipovehiculos_idtipovehiculos,
                "modelo": modelo,
            }
            if "cliente_id" in vehiculo_cols and usuario_id:
                payload["cliente_id"] = usuario_id

            campos = [campo for campo in payload.keys() if campo in vehiculo_cols]
            columnas = ", ".join(campos)
            valores = ", ".join(f":{campo}" for campo in campos)
            result = conn.execute(
                text(f"INSERT INTO dmi.vehiculos ({columnas}) VALUES ({valores}) RETURNING idvehiculo"),
                {campo: payload[campo] for campo in campos},
            )
            nuevo_id = result.fetchone()[0]

            conn.execute(
                text("""
                    UPDATE dmi.usuarios
                    SET vehiculos_idvehiculo = COALESCE(vehiculos_idvehiculo, :vid)
                    WHERE id = :uid
                """),
                {"vid": nuevo_id, "uid": usuario["id"]},
            )
            conn.commit()

        if quiere_json(request):
            return JSONResponse({"success": True, "message": "Vehiculo creado correctamente", "idvehiculo": nuevo_id})

        return RedirectResponse(url="/?success=Vehiculo creado y asignado correctamente", status_code=302)
    except Exception as e:
        print("ERROR VEHICULO:", str(e))
        if quiere_json(request):
            return JSONResponse({"error": "No fue posible guardar el vehiculo. Revisa la placa e intentalo nuevamente."}, status_code=500)
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== FORMULARIO EDITAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
@app.get("/vehiculo/editar/{vehiculo_id}", response_class=HTMLResponse)
async def editar_vehiculo_form(
    request: Request, vehiculo_id: int, access_token: str = Cookie(None)
):
    usuario = obtener_usuario(access_token, request)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    vehicle_to_edit = None
    data = []
    tipos = []

    try:
        with engine.connect() as conn:
            data, tipos = obtener_datos_base(conn)
            result = conn.execute(
                text("SELECT * FROM dmi.vehiculos WHERE idvehiculo = :id"),
                {"id": vehiculo_id},
            )
            vehicle_to_edit = result.fetchone()
    except Exception as e:
        print("Error:", e)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data": data,
            "tipos": tipos,
            "usuario": usuario,
            "success_msg": None,
            "error": None,
            "vehicle_to_edit": vehicle_to_edit,
        },
    )


# ==================== ACTUALIZAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
@app.post("/vehiculo/editar/{vehiculo_id}")
async def actualizar_vehiculo(
    vehiculo_id: int,
    access_token: str = Cookie(None),
    codigovehiculo: str = Form(...),
    placa: str = Form(...),
    marca: str = Form(...),
    tipovehiculos_idtipovehiculos: str = Form(...),
    descripcionvehiculo: Optional[str] = Form(None),
    motor: Optional[str] = Form(None),
    cantidad_asientos: Optional[str] = Form(None),
    capacidad: Optional[str] = Form(None),
    modelo: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.vehiculos SET
                        codigovehiculo               = :codigovehiculo,
                        descripcionvehiculo          = :descripcionvehiculo,
                        motor                        = :motor,
                        cantidad_asientos            = :cantidad_asientos,
                        placa                        = :placa,
                        capacidad                    = :capacidad,
                        marca                        = :marca,
                        tipovehiculos_idtipovehiculos = :tipovehiculos_idtipovehiculos,
                        modelo                       = :modelo
                    WHERE idvehiculo = :idvehiculo
                """),
                {
                    "codigovehiculo": codigovehiculo,
                    "descripcionvehiculo": descripcionvehiculo,
                    "motor": motor,
                    "cantidad_asientos": cantidad_asientos,
                    "placa": placa,
                    "capacidad": capacidad,
                    "marca": marca,
                    "tipovehiculos_idtipovehiculos": tipovehiculos_idtipovehiculos,
                    "modelo": modelo,
                    "idvehiculo": vehiculo_id,
                },
            )
            conn.commit()

        return RedirectResponse(
            url="/?success=VehÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­culo actualizado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== ELIMINAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
@app.post("/vehiculo/eliminar/{vehiculo_id}")
async def eliminar_vehiculo(vehiculo_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    try:
        with engine.connect() as conn:
            conn.execute(
                text("DELETE FROM dmi.vehiculos WHERE idvehiculo = :id"),
                {"id": vehiculo_id},
            )
            conn.commit()

        return RedirectResponse(
            url="/?success=VehÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­culo eliminado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== PÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂGINA DE CITAS ====================
# ==================== PÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂGINA DE CITAS ====================
@app.get("/citas", response_class=HTMLResponse)
async def ver_citas(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    mes = request.query_params.get("mes")
    anio = request.query_params.get("anio")

    hoy = date.today()
    mes = int(mes) if mes else hoy.month
    anio = int(anio) if anio else hoy.year

    citas = []
    vehiculos = []
    todas_citas = []

    try:
        with engine.connect() as conn:
            vehiculos = conn.execute(
                text("SELECT idvehiculo, codigovehiculo, placa, marca FROM dmi.vehiculos ORDER BY marca")
            ).mappings().fetchall()

            vehiculos = [dict(v) for v in vehiculos]

            citas_raw = conn.execute(
                text("""
                    SELECT c.idcita, c.fecha, c.hora, c.motivo,
                        c.estado, c.notas,
                        v.placa, v.marca, v.codigovehiculo,
                        c.vehiculos_idvehiculo
                    FROM dmi.citas c
                    JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    WHERE EXTRACT(MONTH FROM c.fecha) = :mes
                    AND EXTRACT(YEAR FROM c.fecha) = :anio
                    ORDER BY c.fecha, c.hora
                """),
                {"mes": mes, "anio": anio},
            ).mappings().fetchall()

            citas = []

            for c in citas_raw:
                cita = dict(c)
                cita["fecha"] = str(cita["fecha"])
                cita["hora"] = str(cita["hora"])
                citas.append(cita)

            todas_raw = conn.execute(
                text("""
                    SELECT c.idcita, c.fecha, c.hora, c.motivo,
                           c.estado, c.notas,
                           v.placa, v.marca, v.codigovehiculo,
                           c.vehiculos_idvehiculo
                    FROM dmi.citas c
                    JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    ORDER BY c.fecha DESC, c.hora
                """)
            ).mappings().fetchall()

            for c in todas_raw:
                cita = dict(c)
                cita["fecha"] = str(cita["fecha"])
                cita["hora"] = str(cita["hora"])
                todas_citas.append(cita)

    except Exception as e:
        error_msg = str(e)

    return templates.TemplateResponse(
        request=request,
        name="citas.html",
        context={
            "usuario": usuario,
            "citas": citas,
            "vehiculos": vehiculos,
            "mes": mes,
            "anio": anio,
            "success_msg": success_msg,
            "error": error_msg,
            "todas_citas": todas_citas,
        },
    )


# ==================== CREAR CITA ====================
@app.post("/citas/nueva")
async def crear_cita(
    request: Request,
    access_token: str = Cookie(None),
    authorization: Optional[str] = Header(None),
    vehiculos_idvehiculo: Optional[str] = Form(None),
    fecha_cita: str = Form(...),
    hora_cita: str = Form(...),
    motivo: str = Form(...),
    observaciones: Optional[str] = Form(None),
    descripcion_vehiculo: Optional[str] = Form(None),
):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]

    usuario = obtener_usuario(access_token, request) if access_token else None

    try:
        # Validamos la fecha en el backend para que la regla de los dos meses
        # no pueda saltarse manipulando el calendario del navegador.
        fecha_cita_validada, hora_cita_validada = validar_fecha_hora_cita(fecha_cita, hora_cita)
        fecha_cita = fecha_cita_validada
        hora_cita = hora_cita_validada.strftime("%H:%M")

        notas = observaciones or ""

        descripcion_vehiculo = (descripcion_vehiculo or "").strip()

        if descripcion_vehiculo:
            notas = (
                f"Vehiculo descrito por el cliente: "
                f"{descripcion_vehiculo}\n{notas}"
            ).strip()

        with engine.connect() as conn:
            vehiculo_id = int(vehiculos_idvehiculo) if vehiculos_idvehiculo else None
            vehiculo_cols = table_columns(conn, "dmi", "vehiculos")
            usuario_id = usuario.get("idusuarios") if usuario else None

            if vehiculo_id and usuario_id:
                pertenece = conn.execute(
                    text("""
                        SELECT 1
                        FROM dmi.vehiculos v
                        LEFT JOIN dmi.usuarios u ON u.vehiculos_idvehiculo = v.idvehiculo
                        WHERE v.idvehiculo = :vehiculo_id
                        AND (
                            (:tiene_cliente = TRUE AND v.cliente_id = :usuario_id)
                            OR u.idusuarios = :usuario_id
                        )
                        LIMIT 1
                    """),
                    {
                        "vehiculo_id": vehiculo_id,
                        "usuario_id": usuario_id,
                        "tiene_cliente": "cliente_id" in vehiculo_cols,
                    },
                ).fetchone()
                if not pertenece:
                    return JSONResponse(
                        {"error": "El vehiculo seleccionado no pertenece a tu cuenta."},
                        status_code=403,
                    )

            if not vehiculo_id and usuario_id:
                # Si la pantalla se acaba de actualizar despues de registrar un
                # vehiculo, el selector puede llegar sin id. Recuperamos el
                # vehiculo ya asociado al cliente y evitamos crear un duplicado.
                filtros_vehiculo = []
                parametros_vehiculo = {"usuario_id": usuario_id}
                if "cliente_id" in vehiculo_cols:
                    filtros_vehiculo.append("v.cliente_id = :usuario_id")
                filtros_vehiculo.append("u.idusuarios = :usuario_id")
                activos_sql = " AND COALESCE(v.activo, TRUE) = TRUE" if "activo" in vehiculo_cols else ""
                vehiculos_cliente = conn.execute(
                    text(f"""
                        SELECT DISTINCT v.idvehiculo
                        FROM dmi.vehiculos v
                        LEFT JOIN dmi.usuarios u ON u.vehiculos_idvehiculo = v.idvehiculo
                        WHERE ({' OR '.join(filtros_vehiculo)}){activos_sql}
                        ORDER BY v.idvehiculo
                    """),
                    parametros_vehiculo,
                ).fetchall()

                if len(vehiculos_cliente) == 1:
                    vehiculo_id = vehiculos_cliente[0][0]
                elif len(vehiculos_cliente) > 1:
                    return JSONResponse(
                        {"error": "Selecciona uno de tus vehiculos registrados antes de agendar la cita."},
                        status_code=400,
                    )

            if not vehiculo_id:
                # Las citas de un usuario siempre deben usar un vehiculo de su
                # garaje. No se crean vehiculos automaticos para evitar placas
                # repetidas y registros sin propietario.
                if usuario_id:
                    return JSONResponse(
                        {"error": "No encontramos el vehiculo seleccionado. Actualiza la pagina y selecciona tu vehiculo nuevamente."},
                        status_code=400,
                    )
                tipo_row = conn.execute(
                    text(
                        "SELECT idtipovehiculos "
                        "FROM dmi.tipovehiculos "
                        "ORDER BY idtipovehiculos LIMIT 1"
                    )
                ).fetchone()

                if not tipo_row:
                    return JSONResponse(
                        {"error": "No hay tipos de vehiculo configurados"},
                        status_code=400
                    )

                auto_code = f"AUTO{datetime.utcnow().strftime('%m%d%H%M%S%f')[:12]}"

                result = conn.execute(
                    text("""
                        INSERT INTO dmi.vehiculos
                            (
                                codigovehiculo,
                                descripcionvehiculo,
                                motor,
                                cantidad_asientos,
                                placa,
                                capacidad,
                                marca,
                                tipovehiculos_idtipovehiculos,
                                modelo
                            )
                        VALUES
                            (
                                :codigo,
                                :descripcion,
                                :motor,
                                :asientos,
                                :placa,
                                :capacidad,
                                :marca,
                                :tipo,
                                :modelo
                            )
                        RETURNING idvehiculo
                    """),
                    {
                        "codigo": auto_code,
                        "descripcion": descripcion_vehiculo or "Vehiculo descrito por el cliente",
                        "motor": "POR DEFINIR",
                        "asientos": 0,
                        "placa": auto_code[-10:],
                        "capacidad": 0,
                        "marca": "POR DEFINIR",
                        "tipo": tipo_row[0],
                        "modelo": "POR DEFINIR",
                    },
                )

                vehiculo_id = result.fetchone()[0]

                if usuario_id and "cliente_id" in vehiculo_cols:
                    conn.execute(
                        text("UPDATE dmi.vehiculos SET cliente_id = :cliente_id WHERE idvehiculo = :vehiculo_id"),
                        {"cliente_id": usuario_id, "vehiculo_id": vehiculo_id},
                    )

                if usuario:
                    conn.execute(
                        text(
                            "UPDATE dmi.usuarios "
                            "SET vehiculos_idvehiculo = COALESCE(vehiculos_idvehiculo, :vid) "
                            "WHERE id = :uid"
                        ),
                        {
                            "vid": vehiculo_id,
                            "uid": usuario["id"]
                        },
                    )

            cita_creada = conn.execute(
                text("""
                    INSERT INTO dmi.citas
                        (
                            vehiculos_idvehiculo,
                            fecha,
                            hora,
                            motivo,
                            notas,
                            estado
                        )
                    VALUES
                        (
                            :vehiculo,
                            CAST(:fecha AS date),
                            :hora,
                            :motivo,
                            :obs,
                            'pendiente'
                        )
                    RETURNING idcita
                """),
                {
                    "vehiculo": vehiculo_id,
                    "fecha": fecha_cita,
                    "hora": hora_cita,
                    "motivo": motivo,
                    "obs": notas,
                },
            )

            cita_id = cita_creada.scalar()
            notificar_administradores(
                conn, "Nueva cita agendada",
                f"Se creó una cita para el {fecha_cita} a las {hora_cita}: {motivo}.",
                "cita_creada", "cita", cita_id, "/admin/citas",
            )
            correo_cliente = str(usuario.get("email") or "").strip()
            if correo_cliente:
                mensaje_correo = f"Tu cita fue agendada para el {fecha_cita} a las {hora_cita}. Servicio: {motivo}."
                enviar_correo_transaccional(
                    correo_cliente, "DMI | Cita agendada",
                    "<h2>DISOL MOTORS</h2><p>" + html.escape(mensaje_correo) + "</p>",
                    "cita_agendada", usuario.get("idusuarios") or usuario.get("id"), "cita", cita_id,
                )
            conn.commit()

        if quiere_json(request):
            return JSONResponse(
                {
                    "success": True,
                    "message": "Cita agendada correctamente"
                }
            )

        return RedirectResponse(
            url="/admin/citas?success=Cita agendada correctamente",
            status_code=302
        )

    except Exception as e:
        if quiere_json(request):
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )

        return RedirectResponse(
            url=f"/citas?error={str(e)}",
            status_code=302
        )
# ==================== GESTION SEGURA DE CITAS ====================
def usuario_puede_gestionar_cita(conn, usuario: Optional[dict], cita_id: int) -> bool:
    """Autoriza solo al propietario de la cita o a un administrador."""
    if es_admin(usuario):
        return True
    if not usuario or not usuario.get("idusuarios"):
        return False

    return conn.execute(
        text("""
            SELECT 1
            FROM dmi.citas c
            JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
            LEFT JOIN dmi.usuarios u ON u.vehiculos_idvehiculo = v.idvehiculo
            WHERE c.idcita = :cita_id
              AND (v.cliente_id = :usuario_id OR u.idusuarios = :usuario_id)
            LIMIT 1
        """),
        {"cita_id": cita_id, "usuario_id": usuario["idusuarios"]},
    ).scalar() is not None


def obtener_cita_para_gestion(conn, cita_id: int) -> Optional[dict]:
    row = conn.execute(
        text("""
            SELECT idcita, fecha, hora, motivo, notas, estado, vehiculos_idvehiculo
            FROM dmi.citas
            WHERE idcita = :cita_id
        """),
        {"cita_id": cita_id},
    ).mappings().fetchone()
    return dict(row) if row else None


def registrar_historial_cita(conn, cita_id: int, evento: str, usuario: Optional[dict], motivo: str = None,
                             datos_anteriores: Optional[dict] = None, datos_nuevos: Optional[dict] = None):
    if not table_exists(conn, "dmi", "historial_citas"):
        return
    conn.execute(
        text("""
            INSERT INTO dmi.historial_citas
                (cita_id, tipo_evento, actor_usuario_id, actor_email, motivo, datos_anteriores, datos_nuevos)
            VALUES
                (:cita_id, :evento, :actor_usuario_id, :actor_email, :motivo,
                 CAST(:datos_anteriores AS jsonb), CAST(:datos_nuevos AS jsonb))
        """),
        {
            "cita_id": cita_id,
            "evento": evento,
            "actor_usuario_id": usuario.get("idusuarios") if usuario else None,
            "actor_email": usuario.get("email") if usuario else None,
            "motivo": motivo,
            "datos_anteriores": json.dumps(datos_anteriores or {}, default=str),
            "datos_nuevos": json.dumps(datos_nuevos or {}, default=str),
        },
    )


def crear_notificacion(conn, titulo: str, mensaje: str, tipo: str, referencia_tipo: str = None,
                       referencia_id: int = None, usuario_id: int = None, empleado_id: int = None,
                       accion_url: str = None):
    """Registra una notificacion persistente para una cuenta o empleado."""
    if not table_exists(conn, "dmi", "notificaciones") or (not usuario_id and not empleado_id):
        return
    insert_dynamic_returning(conn, "notificaciones", {
        "usuario_id": usuario_id, "empleado_id": empleado_id, "tipo": tipo,
        "titulo": titulo[:180], "mensaje": mensaje, "referencia_tipo": referencia_tipo,
        "referencia_id": referencia_id, "accion_url": accion_url,
    })


def notificar_administradores(conn, titulo: str, mensaje: str, tipo: str,
                              referencia_tipo: str = None, referencia_id: int = None,
                              accion_url: str = "/", usuario_actual: Optional[dict] = None):
    """Entrega un evento operativo a los administradores.

    Ademas de buscar todos los usuarios con rol ``admin``, incluye de forma
    explicita al administrador que esta ejecutando la accion. Esto evita que
    una diferencia en el valor almacenado del rol impida que la notificacion
    del inventario llegue a la cuenta que hizo el cambio.
    """
    administradores = conn.execute(text("""
        SELECT idusuarios
        FROM dmi.usuarios
        WHERE lower(trim(COALESCE(rol, 'usuario'))) IN ('admin', 'administrador')
    """)).scalars().all()

    ids_admin = {int(admin_id) for admin_id in administradores if admin_id is not None}

    if usuario_actual and usuario_actual.get("idusuarios"):
        ids_admin.add(int(usuario_actual["idusuarios"]))

    for admin_id in ids_admin:
        crear_notificacion(
            conn,
            titulo,
            mensaje,
            tipo,
            referencia_tipo,
            referencia_id,
            admin_id,
            accion_url=accion_url,
        )

    print(
        f"[NOTIFICACION] tipo={tipo} titulo={titulo!r} "
        f"destinatarios={sorted(ids_admin)} referencia={referencia_tipo}:{referencia_id}"
    )


def notificar_cliente(conn, cliente_id: Optional[int], titulo: str, mensaje: str, tipo: str,
                      referencia_tipo: str = None, referencia_id: int = None,
                      accion_url: str = "/mi-cuenta"):
    if cliente_id:
        crear_notificacion(conn, titulo, mensaje, tipo, referencia_tipo, referencia_id,
                            cliente_id, accion_url=accion_url)


def registrar_correo(conn, destinatario: str, tipo: str, asunto: str, estado: str,
                     usuario_id: Optional[int] = None, referencia_tipo: str = None,
                     referencia_id: Optional[int] = None, error_detalle: str = None,
                     proveedor_mensaje_id: str = None):
    """Audita cada intento de envío sin guardar contraseñas ni contenido privado."""
    if not table_exists(conn, "dmi", "correos_enviados"):
        return None
    return insert_dynamic_returning(conn, "correos_enviados", {
        "usuario_id": usuario_id, "destinatario": destinatario, "tipo": tipo,
        "asunto": asunto, "estado": estado, "referencia_tipo": referencia_tipo,
        "referencia_id": referencia_id, "error_detalle": error_detalle,
        "proveedor_mensaje_id": proveedor_mensaje_id,
        "enviado_en": datetime.now() if estado == "enviado" else None,
    }, "idcorreo")


def enviar_correo_transaccional(destinatario: str, asunto: str, contenido_html: str, tipo: str,
                                usuario_id: Optional[int] = None, referencia_tipo: str = None,
                                referencia_id: Optional[int] = None) -> bool:
    """Envía correo por SMTP y conserva resultado en dmi.correos_enviados.

    Si aún no hay credenciales configuradas, no simula un envío: deja el evento
    como pendiente para que el administrador pueda identificarlo.
    """
    if not destinatario:
        return False
    asunto = str(asunto)[:255]
    try:
        if not (SMTP_USERNAME and SMTP_PASSWORD and EMAIL_FROM):
            with engine.connect() as conn:
                registrar_correo(conn, destinatario, tipo, asunto, "pendiente", usuario_id,
                                 referencia_tipo, referencia_id,
                                 "Falta configurar SMTP_USERNAME, SMTP_PASSWORD y EMAIL_FROM.")
                conn.commit()
            return False

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = EMAIL_FROM
        mensaje["To"] = destinatario
        mensaje.set_content("Consulta este mensaje desde un cliente compatible con HTML.")
        mensaje.add_alternative(contenido_html, subtype="html")
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=20) as smtp:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(mensaje)
        with engine.connect() as conn:
            registrar_correo(conn, destinatario, tipo, asunto, "enviado", usuario_id,
                             referencia_tipo, referencia_id)
            conn.commit()
        return True
    except Exception as error:
        print("ERROR enviar_correo_transaccional:", error)
        try:
            with engine.connect() as conn:
                registrar_correo(conn, destinatario, tipo, asunto, "fallido", usuario_id,
                                 referencia_tipo, referencia_id, str(error)[:2000])
                conn.commit()
        except Exception as audit_error:
            print("ERROR registrar_correo_fallido:", audit_error)
        return False


def notificar_evento_cita(conn, cita_id: int, usuario: Optional[dict], tipo: str, mensaje_cliente: str, mensaje_admin: str):
    cliente = conn.execute(text("""
        SELECT COALESCE(v.cliente_id, u.idusuarios) AS cliente_id, u.email
        FROM dmi.citas c JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
        LEFT JOIN dmi.usuarios u ON u.vehiculos_idvehiculo = v.idvehiculo
        WHERE c.idcita = :cita_id LIMIT 1
    """), {"cita_id": cita_id}).mappings().fetchone()
    cliente_id = cliente.get("cliente_id") if cliente else None
    titulo = "Cita reprogramada" if tipo == "cita_reprogramada" else "Cita cancelada"
    if cliente_id:
        crear_notificacion(conn, titulo, mensaje_cliente, tipo, "cita", cita_id, cliente_id, accion_url="/mi-cuenta")
    if cliente and cliente.get("email"):
        enviar_correo_transaccional(
            cliente["email"], "DMI | " + titulo,
            "<h2>DISOL MOTORS</h2><p>" + html.escape(mensaje_cliente) + "</p>",
            tipo, cliente_id, "cita", cita_id,
        )
    notificar_administradores(conn, titulo, mensaje_admin, tipo, "cita", cita_id, "/admin/citas")


def enviar_correo_solicitud_reprogramacion(conn, cita_id: int, usuario_id: Optional[int], fecha: str, hora: str):
    """Confirma por correo que el cambio quedó pendiente de aprobación."""
    email = conn.execute(text("SELECT email FROM dmi.usuarios WHERE idusuarios = :id"), {"id": usuario_id}).scalar()
    if email:
        mensaje = "Recibimos tu solicitud para reprogramar la cita #" + str(cita_id) + " para " + fecha + " a las " + hora + ". Te avisaremos cuando el administrador la apruebe."
        enviar_correo_transaccional(
            email, "DMI | Solicitud de reprogramación recibida",
            "<h2>DISOL MOTORS</h2><p>" + html.escape(mensaje) + "</p>",
            "solicitud_reprogramacion", usuario_id, "cita", cita_id,
        )


def notificar_mecanico_cita_reprogramada(conn, cita_id: int, fecha: str, hora: str):
    """Avisa al técnico asignado con la fecha vigente que quedó en la cita."""
    orden_col = empleado_orden_column(conn)
    if not orden_col:
        return
    empleado_id = conn.execute(text(f"""
        SELECT ot.{orden_col}
        FROM dmi.orden_trabajo ot
        WHERE ot.cita_id = :cita_id AND ot.{orden_col} IS NOT NULL
        ORDER BY ot.idorden DESC LIMIT 1
    """), {"cita_id": cita_id}).scalar()
    if empleado_id:
        crear_notificacion(
            conn, "Cita reprogramada", "La cita #" + str(cita_id) + " fue aprobada para " + fecha + " a las " + hora + ".",
            "cita_reprogramada", "cita", cita_id, empleado_id=empleado_id, accion_url="/mecanico",
        )


def fecha_maxima_cita(desde: Optional[date] = None, meses: int = 2) -> date:
    """Devuelve la fecha limite permitida para agendar/reprogramar una cita.

    La regla de DMI es permitir citas desde hoy hasta dos meses hacia adelante.
    Se calculan meses calendario (por ejemplo, 24/08 -> 24/10) y se ajusta al
    ultimo dia disponible cuando el mes destino no tiene ese dia.
    """
    base = desde or datetime.now(ZoneInfo("America/Bogota")).date()
    total_meses = base.month - 1 + meses
    anio = base.year + total_meses // 12
    mes = total_meses % 12 + 1
    dia = min(base.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def validar_fecha_hora_cita(fecha_cita: str, hora_cita: str) -> tuple[date, time]:
    try:
        fecha = datetime.strptime(str(fecha_cita), "%Y-%m-%d").date()
        hora = datetime.strptime(str(hora_cita), "%H:%M").time()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Selecciona una fecha y una hora validas.")

    hoy = datetime.now(ZoneInfo("America/Bogota")).date()
    limite = fecha_maxima_cita(hoy, 2)

    if fecha < hoy:
        raise HTTPException(status_code=400, detail="No puedes agendar una cita en una fecha pasada.")
    if fecha > limite:
        raise HTTPException(
            status_code=400,
            detail=f"Solo puedes agendar una cita hasta dos meses hacia adelante. La fecha maxima permitida es {limite.strftime('%d/%m/%Y')}."
        )

    return fecha, hora


@app.put("/api/citas/{cita_id}/reprogramar")
async def reprogramar_cita(cita_id: int, request: Request, access_token: str = Cookie(None), authorization: Optional[str] = Header(None)):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]
    usuario = obtener_usuario(access_token, request)
    if not usuario:
        return JSONResponse({"error": "Debes iniciar sesion para reprogramar una cita."}, status_code=401)

    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else dict(await request.form())
        fecha, hora = validar_fecha_hora_cita(body.get("fecha_cita"), body.get("hora_cita"))
        motivo = str(body.get("motivo") or "").strip()[:1000] or None

        with engine.connect() as conn:
            if not usuario_puede_gestionar_cita(conn, usuario, cita_id):
                return JSONResponse({"error": "No tienes permiso para modificar esta cita."}, status_code=403)
            cita = obtener_cita_para_gestion(conn, cita_id)
            if not cita:
                return JSONResponse({"error": "La cita no existe."}, status_code=404)
            if str(cita.get("estado") or "").lower() in {"cancelada", "cancelado", "completada"}:
                return JSONResponse({"error": "Esta cita ya no puede reprogramarse."}, status_code=400)

            ocupada = conn.execute(
                text("""
                    SELECT 1 FROM dmi.citas
                    WHERE vehiculos_idvehiculo = :vehiculo_id
                      AND fecha = :fecha AND hora = :hora AND idcita <> :cita_id
                      AND lower(COALESCE(estado, 'pendiente')) NOT IN ('cancelada', 'cancelado')
                    LIMIT 1
                """),
                {"vehiculo_id": cita["vehiculos_idvehiculo"], "fecha": fecha, "hora": hora, "cita_id": cita_id},
            ).scalar()
            if ocupada:
                return JSONResponse({"error": "Ya tienes una cita activa para esa fecha y hora."}, status_code=409)

            # El cliente propone el cambio; solamente un administrador puede
            # confirmar y aplicar la nueva fecha sobre la cita original.
            if not es_admin(usuario):
                if not table_exists(conn, "dmi", "solicitudes_reprogramacion"):
                    return JSONResponse({"error": "Falta ejecutar la migracion de solicitudes de reprogramacion."}, status_code=503)
                conn.execute(text("""
                    UPDATE dmi.solicitudes_reprogramacion
                    SET estado = 'reemplazada', resuelta_en = now()
                    WHERE cita_id = :cita_id AND estado = 'pendiente'
                """), {"cita_id": cita_id})
                solicitud_id = conn.execute(text("""
                    INSERT INTO dmi.solicitudes_reprogramacion
                        (cita_id, solicitante_usuario_id, fecha_solicitada, hora_solicitada, motivo)
                    VALUES (:cita_id, :usuario_id, :fecha, :hora, :motivo)
                    RETURNING idsolicitud_reprogramacion
                """), {
                    "cita_id": cita_id, "usuario_id": usuario.get("idusuarios"),
                    "fecha": fecha, "hora": hora, "motivo": motivo,
                }).scalar()
                anteriores = {"fecha": str(cita.get("fecha")), "hora": str(cita.get("hora")), "estado": cita.get("estado")}
                nuevos = {"fecha_solicitada": str(fecha), "hora_solicitada": hora.strftime("%H:%M"), "motivo": motivo, "estado": "pendiente"}
                registrar_historial_cita(conn, cita_id, "reprogramacion_solicitada", usuario, motivo, anteriores, nuevos)
                notificar_administradores(
                    conn, "Solicitud de reprogramacion",
                    "Un cliente solicita mover la cita #" + str(cita_id) + " para " + str(fecha) + " a las " + hora.strftime("%H:%M") + ".",
                    "solicitud_reprogramacion", "solicitud_reprogramacion", solicitud_id, "/admin/citas",
                )
                enviar_correo_solicitud_reprogramacion(conn, cita_id, usuario.get("idusuarios"), str(fecha), hora.strftime("%H:%M"))
                conn.commit()
                return JSONResponse({
                    "success": True,
                    "message": "Solicitud enviada al administrador. Tu cita sigue pendiente hasta su aprobacion.",
                    "solicitud": {"idsolicitud_reprogramacion": solicitud_id, **nuevos},
                })

            anteriores = {"fecha": str(cita.get("fecha")), "hora": str(cita.get("hora")), "estado": cita.get("estado")}
            # Algunas bases ya desplegadas validan el campo estado con una lista
            # antigua que no incluye "reprogramada". El historial conserva el
            # evento real sin romper una cita confirmada o pendiente existente.
            estado_resultante = cita.get("estado") or "pendiente"
            cita_actualizada = conn.execute(
                text("""
                    UPDATE dmi.citas
                    SET fecha = :fecha, hora = :hora,
                        reprogramada_en = now(), reprogramada_por_usuario_id = :usuario_id
                    WHERE idcita = :cita_id
                    RETURNING fecha, hora, estado, reprogramada_en
                """),
                {"fecha": fecha, "hora": hora, "usuario_id": usuario.get("idusuarios"), "cita_id": cita_id},
            ).mappings().fetchone()
            if not cita_actualizada:
                return JSONResponse({"error": "La cita no pudo actualizarse."}, status_code=404)

            # Respondemos exactamente lo que PostgreSQL dejó guardado para que la
            # tarjeta del cliente no se quede mostrando una fecha anterior.
            nuevos = {
                "fecha": str(cita_actualizada["fecha"]),
                "hora": str(cita_actualizada["hora"]),
                "estado": cita_actualizada["estado"] or estado_resultante,
                "reprogramada_en": str(cita_actualizada["reprogramada_en"]),
            }
            registrar_historial_cita(conn, cita_id, "cita_reprogramada", usuario, motivo, anteriores, nuevos)
            notificar_evento_cita(conn, cita_id, usuario, "cita_reprogramada",
                                  "Tu cita fue reprogramada para " + str(fecha) + " a las " + hora.strftime("%H:%M") + ".",
                                  "Una cita fue reprogramada para " + str(fecha) + " a las " + hora.strftime("%H:%M") + ".")
            conn.commit()

        return JSONResponse({"success": True, "message": "Tu cita fue reprogramada correctamente.", "cita": {"idcita": cita_id, **nuevos}})
    except HTTPException as exc:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    except Exception as e:
        print("ERROR reprogramar_cita:", e)
        return JSONResponse({"error": "No fue posible reprogramar la cita. Intenta nuevamente."}, status_code=500)


@app.get("/api/solicitudes-reprogramacion/{solicitud_id}")
async def obtener_solicitud_reprogramacion(solicitud_id: int, request: Request, access_token: str = Cookie(None), authorization: Optional[str] = Header(None)):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]
    usuario = obtener_usuario(access_token, request)
    if not usuario or not es_admin(usuario):
        return JSONResponse({"error": "Solo un administrador puede revisar esta solicitud."}, status_code=403)
    try:
        with engine.connect() as conn:
            solicitud = conn.execute(text("""
                SELECT sr.*, c.fecha AS fecha_actual, c.hora AS hora_actual, c.motivo AS servicio_cita,
                       c.estado AS estado_cita, v.placa, v.marca, v.modelo,
                       CONCAT_WS(' ', u.nombre, u.apellidos) AS cliente_nombre, u.email AS cliente_email
                FROM dmi.solicitudes_reprogramacion sr
                JOIN dmi.citas c ON c.idcita = sr.cita_id
                LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                LEFT JOIN dmi.usuarios u ON u.idusuarios = sr.solicitante_usuario_id
                WHERE sr.idsolicitud_reprogramacion = :solicitud_id
            """), {"solicitud_id": solicitud_id}).mappings().fetchone()
            if not solicitud:
                return JSONResponse({"error": "La solicitud no existe."}, status_code=404)
            datos = dict(solicitud)
            for campo in ("fecha_actual", "hora_actual", "fecha_solicitada", "hora_solicitada", "creado_en", "resuelta_en"):
                if datos.get(campo) is not None:
                    datos[campo] = str(datos[campo])
            return JSONResponse({"solicitud": datos})
    except Exception as e:
        print("ERROR obtener_solicitud_reprogramacion:", e)
        return JSONResponse({"error": "No fue posible cargar la solicitud."}, status_code=500)


@app.get("/api/notificaciones/{notificacion_id}/solicitud-reprogramacion")
async def solicitud_desde_notificacion(notificacion_id: int, request: Request, access_token: str = Cookie(None), authorization: Optional[str] = Header(None)):
    """Obtiene la solicitud vinculada a una alerta, también para alertas creadas antes de la referencia nueva."""
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]
    usuario = obtener_usuario(access_token, request)
    if not usuario or not es_admin(usuario):
        return JSONResponse({"error": "Solo un administrador puede revisar esta solicitud."}, status_code=403)
    try:
        with engine.connect() as conn:
            notificacion = conn.execute(text("""
                SELECT referencia_tipo, referencia_id, titulo, mensaje
                FROM dmi.notificaciones WHERE idnotificacion = :notificacion_id
            """), {"notificacion_id": notificacion_id}).mappings().fetchone()
            if not notificacion:
                return JSONResponse({"error": "La notificación no existe."}, status_code=404)
            solicitud_id = notificacion.get("referencia_id") if notificacion.get("referencia_tipo") == "solicitud_reprogramacion" else None
            if not solicitud_id:
                coincidencia = re.search(r"cita\s*#(\d+)", str(notificacion.get("mensaje") or ""), re.IGNORECASE)
                if coincidencia:
                    solicitud_id = conn.execute(text("""
                        SELECT idsolicitud_reprogramacion FROM dmi.solicitudes_reprogramacion
                        WHERE cita_id = :cita_id AND estado = 'pendiente'
                        ORDER BY creado_en DESC LIMIT 1
                    """), {"cita_id": int(coincidencia.group(1))}).scalar()
            if not solicitud_id:
                return JSONResponse({"error": "Esta notificación no tiene una solicitud pendiente asociada."}, status_code=404)
            return JSONResponse({"solicitud_id": solicitud_id})
    except Exception as e:
        print("ERROR solicitud_desde_notificacion:", e)
        return JSONResponse({"error": "No fue posible abrir la solicitud."}, status_code=500)


@app.post("/api/solicitudes-reprogramacion/{solicitud_id}/aprobar")
async def aprobar_solicitud_reprogramacion(solicitud_id: int, request: Request, access_token: str = Cookie(None), authorization: Optional[str] = Header(None)):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]
    usuario = obtener_usuario(access_token, request)
    if not usuario or not es_admin(usuario):
        return JSONResponse({"error": "Solo un administrador puede aprobar esta solicitud."}, status_code=403)
    try:
        with engine.connect() as conn:
            solicitud = conn.execute(text("""
                SELECT * FROM dmi.solicitudes_reprogramacion
                WHERE idsolicitud_reprogramacion = :solicitud_id
            """), {"solicitud_id": solicitud_id}).mappings().fetchone()
            if not solicitud:
                return JSONResponse({"error": "La solicitud no existe."}, status_code=404)
            if solicitud.get("estado") != "pendiente":
                return JSONResponse({"error": "Esta solicitud ya fue resuelta."}, status_code=400)
            cita = obtener_cita_para_gestion(conn, solicitud["cita_id"])
            if not cita or str(cita.get("estado") or "").lower() in {"cancelada", "cancelado", "completada"}:
                return JSONResponse({"error": "La cita ya no puede reprogramarse."}, status_code=400)

            ocupada = conn.execute(text("""
                SELECT 1 FROM dmi.citas
                WHERE vehiculos_idvehiculo = :vehiculo_id
                  AND fecha = :fecha AND hora = :hora AND idcita <> :cita_id
                  AND lower(COALESCE(estado, 'pendiente')) NOT IN ('cancelada', 'cancelado')
                LIMIT 1
            """), {
                "vehiculo_id": cita["vehiculos_idvehiculo"], "fecha": solicitud["fecha_solicitada"],
                "hora": solicitud["hora_solicitada"], "cita_id": solicitud["cita_id"],
            }).scalar()
            if ocupada:
                return JSONResponse({"error": "La fecha y hora solicitadas ya no están disponibles."}, status_code=409)

            cita_actualizada = conn.execute(text("""
                UPDATE dmi.citas
                SET fecha = :fecha, hora = :hora, reprogramada_en = now(),
                    reprogramada_por_usuario_id = :administrador_id
                WHERE idcita = :cita_id
                RETURNING fecha, hora, estado, reprogramada_en
            """), {
                "fecha": solicitud["fecha_solicitada"], "hora": solicitud["hora_solicitada"],
                "administrador_id": usuario.get("idusuarios"), "cita_id": solicitud["cita_id"],
            }).mappings().fetchone()
            conn.execute(text("""
                UPDATE dmi.solicitudes_reprogramacion
                SET estado = 'aprobada', administrador_usuario_id = :administrador_id, resuelta_en = now()
                WHERE idsolicitud_reprogramacion = :solicitud_id
            """), {"administrador_id": usuario.get("idusuarios"), "solicitud_id": solicitud_id})

            anteriores = {"fecha": str(cita.get("fecha")), "hora": str(cita.get("hora")), "estado": cita.get("estado")}
            nuevos = {
                "fecha": str(cita_actualizada["fecha"]), "hora": str(cita_actualizada["hora"]),
                "estado": cita_actualizada["estado"] or "pendiente",
                "reprogramada_en": str(cita_actualizada["reprogramada_en"]),
            }
            registrar_historial_cita(conn, solicitud["cita_id"], "reprogramacion_aprobada", usuario, solicitud.get("motivo"), anteriores, nuevos)
            notificar_evento_cita(
                conn, solicitud["cita_id"], usuario, "cita_reprogramada",
                "Tu solicitud fue aprobada. Tu cita quedó para " + nuevos["fecha"] + " a las " + nuevos["hora"] + ".",
                "Se aprobó la reprogramación de la cita #" + str(solicitud["cita_id"]) + ".",
            )
            notificar_mecanico_cita_reprogramada(conn, solicitud["cita_id"], nuevos["fecha"], nuevos["hora"])
            conn.commit()
            return JSONResponse({"success": True, "message": "Reprogramación aprobada. La cita fue actualizada.", "cita": {"idcita": solicitud["cita_id"], **nuevos}})
    except Exception as e:
        print("ERROR aprobar_solicitud_reprogramacion:", e)
        return JSONResponse({"error": "No fue posible aprobar la solicitud."}, status_code=500)


@app.post("/api/citas/{cita_id}/cancelar")
async def cancelar_cita(cita_id: int, request: Request, access_token: str = Cookie(None), authorization: Optional[str] = Header(None)):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]
    usuario = obtener_usuario(access_token, request)
    if not usuario:
        return JSONResponse({"error": "Debes iniciar sesion para cancelar una cita."}, status_code=401)

    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else dict(await request.form())
        motivo = str(body.get("motivo") or "").strip()[:1000] or None
        with engine.connect() as conn:
            if not usuario_puede_gestionar_cita(conn, usuario, cita_id):
                return JSONResponse({"error": "No tienes permiso para cancelar esta cita."}, status_code=403)
            cita = obtener_cita_para_gestion(conn, cita_id)
            if not cita:
                return JSONResponse({"error": "La cita no existe."}, status_code=404)
            estado = str(cita.get("estado") or "").lower()
            if estado in {"cancelada", "cancelado"}:
                return JSONResponse({"error": "Esta cita ya fue cancelada."}, status_code=400)
            if estado == "completada":
                return JSONResponse({"error": "Una cita completada no puede cancelarse."}, status_code=400)

            conn.execute(
                text("""
                    UPDATE dmi.citas
                    SET estado = 'cancelada', cancelada_en = now(),
                        cancelada_por_usuario_id = :usuario_id, motivo_cancelacion = :motivo
                    WHERE idcita = :cita_id
                """),
                {"usuario_id": usuario.get("idusuarios"), "motivo": motivo, "cita_id": cita_id},
            )
            registrar_historial_cita(
                conn, cita_id, "cita_cancelada", usuario, motivo,
                {"fecha": str(cita.get("fecha")), "hora": str(cita.get("hora")), "estado": cita.get("estado")},
                {"estado": "cancelada"},
            )
            notificar_evento_cita(conn, cita_id, usuario, "cita_cancelada",
                                  "Tu cita fue cancelada. Conservamos el registro en tu historial.",
                                  "Una cita fue cancelada y permanece disponible en el historial.")
            conn.commit()

        return JSONResponse({"success": True, "message": "Tu cita fue cancelada. Conservamos el registro en tu historial."})
    except Exception as e:
        print("ERROR cancelar_cita:", e)
        return JSONResponse({"error": "No fue posible cancelar la cita. Intenta nuevamente."}, status_code=500)


# Ruta anterior: se conserva por compatibilidad, pero ya no borra datos.
@app.post("/citas/eliminar/{cita_id}")
async def eliminar_cita(cita_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/citas")
    return await cancelar_cita(cita_id, request, access_token)


@app.get("/api/notificaciones")
async def listar_notificaciones(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not usuario:
        return JSONResponse({"error": "Debes iniciar sesion."}, status_code=401)
    try:
        with engine.connect() as conn:
            filtros, params = [], {}
            if usuario.get("idusuarios"):
                filtros.append("usuario_id = :usuario_id")
                params["usuario_id"] = usuario["idusuarios"]
            empleado = obtener_empleado_actual(conn, usuario) if es_mecanico(usuario) else None
            if empleado:
                filtros.append("empleado_id = :empleado_id")
                params["empleado_id"] = empleado["idempleado"]
            if not filtros:
                return JSONResponse({"notificaciones": [], "no_leidas": 0})
            where = " OR ".join(filtros)
            filas = conn.execute(text(f"SELECT * FROM dmi.notificaciones WHERE {where} ORDER BY creado_en DESC LIMIT 80"), params).mappings().fetchall()
            datos = [{**dict(fila), "creado_en": str(fila.get("creado_en") or ""), "fecha_lectura": str(fila.get("fecha_lectura") or "")} for fila in filas]
            return JSONResponse({"notificaciones": datos, "no_leidas": sum(1 for fila in datos if not fila.get("leida"))})
    except Exception as e:
        print("ERROR listar_notificaciones:", e)
        return JSONResponse({"error": "No fue posible cargar las notificaciones."}, status_code=500)


@app.post("/api/notificaciones/{notificacion_id}/leer")
async def marcar_notificacion_leida(notificacion_id: int, request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not usuario:
        return JSONResponse({"error": "No tienes permiso."}, status_code=403)
    with engine.connect() as conn:
        filtros, params = [], {"id": notificacion_id}
        if usuario.get("idusuarios"):
            filtros.append("usuario_id = :usuario_id")
            params["usuario_id"] = usuario["idusuarios"]
        empleado = obtener_empleado_actual(conn, usuario) if es_mecanico(usuario) else None
        if empleado:
            filtros.append("empleado_id = :empleado_id")
            params["empleado_id"] = empleado["idempleado"]
        if not filtros:
            return JSONResponse({"error": "No tienes permiso."}, status_code=403)
        conn.execute(text(f"UPDATE dmi.notificaciones SET leida = TRUE, fecha_lectura = COALESCE(fecha_lectura, now()) WHERE idnotificacion = :id AND ({' OR '.join(filtros)})"), params)
        conn.commit()
    return JSONResponse({"success": True})


# ==================== CAMBIAR ESTADO CITA ====================
@app.post("/citas/estado/{cita_id}")
async def cambiar_estado_cita(
    cita_id: int,
    access_token: str = Cookie(None),
    estado: str = Form(...),
):
    if not access_token:
        return RedirectResponse(
            url="/citas?error=Debes iniciar sesion",
            status_code=302
        )

    usuario = obtener_usuario(access_token)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE dmi.citas "
                    "SET estado = :estado "
                    "WHERE idcita = :id"
                ),
                {
                    "estado": estado,
                    "id": cita_id
                },
            )

            conn.commit()

        return RedirectResponse(
            url="/citas?success=Estado actualizado",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/citas?error={str(e)}",
            status_code=302
        )


@app.post("/api/citas/{cita_id}/factura-servicio")
async def guardar_factura_servicio(
    cita_id: int,
    request: Request,
    access_token: str = Cookie(None),
):
    usuario = obtener_usuario(access_token, request)

    if not es_admin(usuario):
        return JSONResponse(
            {"error": "No tienes permiso para facturar servicios"},
            status_code=403
        )

    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)

        costo = float(body.get("costo") or 0)

        concepto = (
            body.get("concepto") or
            "Servicio tÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©cnico automotriz"
        ).strip()

        if costo <= 0:
            return JSONResponse(
                {"error": "Ingresa un costo vÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido para la factura"},
                status_code=400
            )

        factura_linea = (
            f"\n[FAC_SERVICIO] fecha={datetime.now().isoformat(timespec='seconds')}; "
            f"concepto={concepto}; costo={costo}; "
            f"admin={usuario.get('nombre', 'admin')}"
        )

        with engine.connect() as conn:

            row = conn.execute(
                text("""
                    SELECT 
                        c.idcita,
                        c.fecha,
                        c.hora,
                        c.motivo,
                        c.estado,
                        c.reprogramada_en,
                        c.notas,
                        v.placa,
                        v.marca,
                        v.modelo,
                        v.codigovehiculo,
                        u.nombre,
                        u.apellidos,
                        u.usuarionombre,
                        u.telefono,
                        u.email,
                        u.documento
                    FROM dmi.citas c
                    LEFT JOIN dmi.vehiculos v
                        ON v.idvehiculo = c.vehiculos_idvehiculo
                    LEFT JOIN dmi.usuarios u
                        ON u.vehiculos_idvehiculo = c.vehiculos_idvehiculo
                    WHERE c.idcita = :id
                """),
                {"id": cita_id},
            ).mappings().first()

            if not row:
                return JSONResponse(
                    {"error": "No se encontrÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ la cita"},
                    status_code=404
                )

            notas = (
                f"{row.get('notas') or ''}"
                f"{factura_linea}"
            ).strip()

            conn.execute(
                text("""
                    UPDATE dmi.citas
                    SET estado = 'completada',
                        notas = :notas
                    WHERE idcita = :id
                """),
                {
                    "notas": notas,
                    "id": cita_id
                },
            )

            conn.commit()

        cita = {}

        for key, value in dict(row).items():
            cita[key] = (
                str(value)
                if isinstance(value, (date, datetime, time, Decimal, UUID))
                else value
            )

        cita["estado"] = "completada"
        cita["notas"] = notas
        cita["costo_facturado"] = costo
        cita["concepto_facturado"] = concepto
        cita["facturada_por"] = usuario.get("nombre", "admin")

        return JSONResponse(
            {
                "success": True,
                "cita": cita
            }
        )

    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )
# ==================== EDITAR ROL DE USUARIO (solo admin) ====================
@app.post("/usuario/rol/{usuario_id}")
async def cambiar_rol_usuario(
    usuario_id: int,
    access_token: str = Cookie(None),
    rol: str = Form(...),
):
    usuario = obtener_usuario(access_token)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    if rol not in ("admin", "usuario", "mecanico"):
        return RedirectResponse(
            url="/?error=Rol invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido",
            status_code=302
        )

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE dmi.usuarios "
                    "SET rol = :rol "
                    "WHERE idusuarios = :id"
                ),
                {
                    "rol": rol,
                    "id": usuario_id
                },
            )

            conn.commit()

        return RedirectResponse(
            url="/?success=Rol actualizado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/?error={str(e)}",
            status_code=302
        )


# ==================== ELIMINAR USUARIO (solo admin) ====================
@app.post("/usuario/eliminar/{usuario_id}")
async def eliminar_usuario(
    usuario_id: int,
    access_token: str = Cookie(None)
):
    usuario = obtener_usuario(access_token)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    if not supabase_admin:
        return RedirectResponse(
            url="/?error=No%20esta%20configurada%20la%20clave%20administrativa%20de%20Supabase",
            status_code=302,
        )

    try:
        with engine.connect() as conn:
            target_user = conn.execute(
                text("SELECT id FROM dmi.usuarios WHERE idusuarios = :id LIMIT 1"),
                {"id": usuario_id},
            ).mappings().fetchone()

        if not target_user or not target_user.get("id"):
            return RedirectResponse(
                url="/?error=Usuario%20no%20encontrado",
                status_code=302,
            )

        auth_user_id = str(target_user["id"])
        supabase_admin.auth.admin.delete_user(auth_user_id)

        with engine.begin() as conn:
            deleted = conn.execute(
                text("DELETE FROM dmi.usuarios WHERE idusuarios = :id"),
                {"id": usuario_id},
            )
            if not deleted.rowcount:
                raise RuntimeError("No se pudo eliminar el perfil DMI del usuario")

        return RedirectResponse(
            url="/?success=Usuario eliminado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/?error={str(e)}",
            status_code=302
        )

    # ==================== API BOT DISOL MOTORS ====================

class BotBuscarClienteRequest(BaseModel):
    tipoDocumento: str
    numeroDocumento: str


@app.post("/api/bot/buscar-cliente")
async def bot_buscar_cliente(
    datos: BotBuscarClienteRequest,
    x_bot_key: Optional[str] = Header(None),
):
    """
    Endpoint utilizado exclusivamente por el asistente de DISOL MOTORS.
    Busca un cliente por tipo y número de documento y devuelve sus vehículos.
    """

    bot_api_key = os.getenv("BOT_API_KEY")

    # Protegemos el endpoint para evitar consultas públicas de clientes.
    if not bot_api_key:
        return JSONResponse(
            {"error": "BOT_API_KEY no está configurada en el servidor."},
            status_code=503,
        )

    if x_bot_key != bot_api_key:
        return JSONResponse(
            {"error": "No autorizado."},
            status_code=401,
        )

    tipo_documento = str(datos.tipoDocumento or "").strip()
    numero_documento = str(datos.numeroDocumento or "").strip()

    if not tipo_documento or not numero_documento:
        return JSONResponse(
            {"error": "Tipo y número de documento son obligatorios."},
            status_code=400,
        )

    # Convertimos lo que selecciona el usuario en Botpress
    # al valor que normalmente manejamos en la base de datos.
    mapa_tipos_documento = {
        "Cédula de ciudadanía": "CC",
        "Cedula de ciudadania": "CC",
        "CC": "CC",

        "Cédula de extranjería": "CE",
        "Cedula de extranjeria": "CE",
        "CE": "CE",

        "Pasaporte": "PAS",
        "PAS": "PAS",
    }

    tipo_bd = mapa_tipos_documento.get(
        tipo_documento,
        tipo_documento
    )

    try:
        with engine.connect() as conn:

            # -------------------------------------------------
            # 1. BUSCAR CLIENTE
            # -------------------------------------------------

            cliente = conn.execute(
                text("""
                    SELECT
                        idusuarios,
                        id,
                        nombre,
                        apellidos,
                        documento,
                        tipodedocumento,
                        email,
                        telefono,
                        usuarionombre,
                        vehiculos_idvehiculo
                    FROM dmi.usuarios
                    WHERE documento::text = :documento
                      AND (
                            UPPER(TRIM(COALESCE(tipodedocumento, ''))) = UPPER(:tipo)
                            OR UPPER(TRIM(COALESCE(tipodedocumento, ''))) = UPPER(:tipo_original)
                          )
                    LIMIT 1
                """),
                {
                    "documento": numero_documento,
                    "tipo": tipo_bd,
                    "tipo_original": tipo_documento,
                },
            ).mappings().fetchone()

            # -------------------------------------------------
            # 2. SI NO EXISTE
            # -------------------------------------------------

            if not cliente:
                return JSONResponse({
                    "encontrado": False,
                    "cliente": None,
                    "vehiculos": [],
                    "message": "No encontramos un cliente con esos datos."
                })

            cliente = dict(cliente)

            # -------------------------------------------------
            # 3. BUSCAR VEHÍCULOS
            # -------------------------------------------------

            vehiculo_columnas = table_columns(
                conn,
                "dmi",
                "vehiculos"
            )

            condiciones = []
            parametros = {
                "cliente_id": cliente["idusuarios"]
            }

            # Relación moderna
            if "cliente_id" in vehiculo_columnas:
                condiciones.append(
                    "v.cliente_id = :cliente_id"
                )

            # Relación antigua que también utiliza tu sistema
            if cliente.get("vehiculos_idvehiculo"):
                condiciones.append(
                    "v.idvehiculo = :vehiculo_principal"
                )
                parametros["vehiculo_principal"] = (
                    cliente["vehiculos_idvehiculo"]
                )

            vehiculos = []

            if condiciones:
                vehiculos = [
                    dict(row)
                    for row in conn.execute(
                        text(f"""
                            SELECT DISTINCT
                                v.idvehiculo,
                                v.placa,
                                v.marca,
                                v.modelo,
                                v.codigovehiculo
                            FROM dmi.vehiculos v
                            WHERE {" OR ".join(condiciones)}
                            ORDER BY v.idvehiculo
                        """),
                        parametros,
                    ).mappings().fetchall()
                ]

            # -------------------------------------------------
            # 4. RESPUESTA PARA BOTPRESS
            # -------------------------------------------------

            return JSONResponse({
                "encontrado": True,
                "cliente": {
                    "idusuarios": cliente.get("idusuarios"),
                    "nombre": cliente.get("nombre"),
                    "apellidos": cliente.get("apellidos"),
                    "documento": str(cliente.get("documento") or ""),
                    "tipoDocumento": cliente.get("tipodedocumento"),
                    "email": cliente.get("email"),
                    "telefono": cliente.get("telefono"),
                },
                "vehiculos": vehiculos,
                "message": "Cliente encontrado correctamente."
            })

    except Exception as e:
        print("ERROR bot_buscar_cliente:", e)

        return JSONResponse(
            {
                "error": "No fue posible consultar la información del cliente."
            },
            status_code=500,
        )
# ===== API JSON PARA REACT =====
@app.get("/api/vehiculos")
async def api_vehiculos(request: Request, access_token: str = Cookie(None)):
    if not obtener_usuario(access_token, request):
        return JSONResponse({"error": "Debes iniciar sesion"}, status_code=401)
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.vehiculos ORDER BY idvehiculo")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/usuarios")
async def api_usuarios(request: Request, access_token: str = Cookie(None)):
    if not es_admin(obtener_usuario(access_token, request)):
        return JSONResponse({"error": "No tienes permiso"}, status_code=401)
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    idusuarios,
                    id,
                    nombre,
                    apellidos,
                    documento,
                    tipodedocumento,
                    email,
                    telefono,
                    usuarionombre,
                    fechadenacimiento::text AS fechadenacimiento,
                    rol,
                    vehiculos_idvehiculo
                FROM dmi.usuarios
                ORDER BY idusuarios
            """)).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/citas")
async def api_citas(request: Request, access_token: str = Cookie(None)):
    """Entrega citas con tipos compatibles con JSON para el calendario React."""
    if not obtener_usuario(access_token, request):
        return JSONResponse({"error": "Debes iniciar sesion"}, status_code=401)
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    c.idcita,
                    c.vehiculos_idvehiculo,
                    c.fecha,
                    c.hora,
                    COALESCE(c.motivo, '') AS motivo,
                    COALESCE(c.estado, 'pendiente') AS estado,
                    COALESCE(c.notas, '') AS notas,
                    COALESCE(v.placa, '') AS placa,
                    COALESCE(v.marca, '') AS marca,
                    COALESCE(v.codigovehiculo, '') AS codigovehiculo
                FROM dmi.citas c
                LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                ORDER BY c.fecha DESC, c.hora DESC, c.idcita DESC
            """)).mappings().fetchall()
            result = [
                {
                    **dict(r),
                    "fecha": str(r.get("fecha") or ""),
                    "hora": str(r.get("hora") or ""),
                }
                for r in data
            ]
            return JSONResponse(content=result)
    except Exception as e:
        print("ERROR api/citas:", repr(e))
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/pedidos-catalogo/{pedido_id}/actualizar")
async def actualizar_pedido_catalogo(pedido_id: int, request: Request, access_token: str = Cookie(None)):
    """El administrador gestiona el avance y las novedades de pedidos web."""
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")

    form = await request.form()
    estado = str(form.get("estado") or "").strip().lower()
    novedad = str(form.get("novedad") or "").strip()[:1000]
    repartidor_nombre = str(form.get("repartidor_nombre") or "").strip()[:160]
    repartidor_telefono = str(form.get("repartidor_telefono") or "").strip()[:50]
    estados_permitidos = {"pedido_aceptado", "enviado", "en_camino", "entregado", "pendiente_transferencia", "pendiente_pago_wompi", "cancelado"}
    if estado not in estados_permitidos:
        return RedirectResponse(url="/configuracion?error=Estado+de+pedido+no+valido#pedidos", status_code=303)
    try:
        with engine.connect() as conn:
            if not table_exists(conn, "public", "pedidos"):
                return RedirectResponse(url="/configuracion?error=No+hay+pedidos+de+catalogo#pedidos", status_code=303)
            # Compatibilidad con pedidos creados antes de activar el reparto.
            for sentencia in (
                "ADD COLUMN IF NOT EXISTS departamento text", "ADD COLUMN IF NOT EXISTS barrio text",
                "ADD COLUMN IF NOT EXISTS codigo_postal text", "ADD COLUMN IF NOT EXISTS referencia_envio text",
                "ADD COLUMN IF NOT EXISTS repartidor_nombre text", "ADD COLUMN IF NOT EXISTS repartidor_telefono text",
                "ADD COLUMN IF NOT EXISTS orden_envio varchar(60)", "ADD COLUMN IF NOT EXISTS token_repartidor varchar(80)",
                "ADD COLUMN IF NOT EXISTS ruta_google_maps text", "ADD COLUMN IF NOT EXISTS latitud_repartidor numeric(10,7)",
                "ADD COLUMN IF NOT EXISTS longitud_repartidor numeric(10,7)", "ADD COLUMN IF NOT EXISTS ubicacion_actualizada_en timestamptz",
            ):
                conn.execute(text(f"ALTER TABLE public.pedidos {sentencia}"))
            pedido = conn.execute(text("SELECT * FROM public.pedidos WHERE id = :id"), {"id": pedido_id}).mappings().fetchone()
            if not pedido:
                return RedirectResponse(url="/configuracion?error=Pedido+no+encontrado#pedidos", status_code=303)
            # El punto de partida de cada reparto es siempre el local DMI
            # publicado en la página de Contacto.
            origen_local = "Carrera 2a B, Soacha, Cundinamarca, Colombia"
            destino = ", ".join(str(parte).strip() for parte in (pedido.get("direccion"), pedido.get("barrio"), pedido.get("ciudad"), pedido.get("departamento"), "Colombia") if parte and str(parte).strip())
            orden_envio = pedido.get("orden_envio")
            token_repartidor = pedido.get("token_repartidor")
            ruta_google_maps = pedido.get("ruta_google_maps")
            if repartidor_nombre and repartidor_telefono:
                orden_envio = orden_envio or f"ENV-{datetime.now().strftime('%Y%m%d')}-{pedido_id:05d}"
                token_repartidor = token_repartidor or uuid4().hex
                ruta_google_maps = f"https://www.google.com/maps/dir/?api=1&origin={quote_plus(origen_local)}&destination={quote_plus(destino)}&travelmode=driving" if destino else None
            resultado = conn.execute(
                text("""UPDATE public.pedidos SET estado=:estado, novedad=:novedad,
                    repartidor_nombre=:repartidor_nombre, repartidor_telefono=:repartidor_telefono,
                    orden_envio=:orden_envio, token_repartidor=:token_repartidor,
                    ruta_google_maps=:ruta_google_maps WHERE id=:id"""),
                {"estado": estado, "novedad": novedad or None, "id": pedido_id, "repartidor_nombre": repartidor_nombre or None,
                 "repartidor_telefono": repartidor_telefono or None, "orden_envio": orden_envio,
                 "token_repartidor": token_repartidor, "ruta_google_maps": ruta_google_maps},
            )
            if resultado.rowcount == 0:
                return RedirectResponse(url="/configuracion?error=Pedido+no+encontrado#pedidos", status_code=303)
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Pedido+actualizado#pedidos", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/configuracion?error=" + quote(str(e)) + "#pedidos", status_code=303)


def _pedido_repartidor_valido(conn, pedido_id: int, token: str):
    if not token:
        return None
    return conn.execute(text("SELECT * FROM public.pedidos WHERE id=:id AND token_repartidor=:token AND activo=TRUE"), {"id": pedido_id, "token": token}).mappings().fetchone()


def _ficha_orden_envio(pedido: dict, iniciar_endpoint: str, ubicacion_endpoint: str):
    """HTML autocontenido: evita errores por rutas o plantillas faltantes."""
    seguro = lambda valor: html.escape(str(valor or ""))
    direccion = ", ".join(str(parte).strip() for parte in (pedido.get("direccion"), pedido.get("barrio"), pedido.get("ciudad"), pedido.get("departamento")) if parte)
    referencia = pedido.get("referencia_envio")
    ruta = pedido.get("ruta_google_maps")
    boton_ruta = ("<a class='button alt' target='_blank' rel='noopener' href='" + seguro(ruta) + "'>ABRIR RUTA EN GOOGLE MAPS</a>") if ruta else ""
    bloque_referencia = ("<div class='field wide'><span>REFERENCIA</span><strong>" + seguro(referencia) + "</strong></div>") if referencia else ""
    return """<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Orden de envío | DMI</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:24px;display:grid;place-items:center;background:radial-gradient(circle at 20% 15%,#351019 0,transparent 34%),#07080c;color:#f6f7fa;font-family:Arial,sans-serif}.card{width:min(680px,100%);padding:clamp(24px,5vw,45px);border:1px solid #ff3158;background:linear-gradient(135deg,rgba(35,10,17,.96),rgba(13,17,25,.98));box-shadow:0 20px 60px #000}.eyebrow{color:#ff5271;letter-spacing:3px;font-size:11px;font-weight:700}.brand{font-size:clamp(34px,7vw,54px);margin:8px 0 4px}.brand b{color:#ff3158}.sub{color:#b6bac5;margin:0 0 28px}.code{display:inline-block;border:1px solid #ff3158;padding:8px 12px;font-weight:bold;margin-bottom:20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{padding:14px;border:1px solid #3b414d;background:rgba(255,255,255,.035)}.field span{display:block;color:#ff6983;font-size:10px;letter-spacing:1.6px;margin-bottom:7px}.wide{grid-column:1/-1}.actions{display:grid;gap:12px;margin-top:26px}.button{border:1px solid #ff3158;background:#ff3158;color:#fff;text-decoration:none;text-align:center;padding:15px 18px;font-weight:800;letter-spacing:.7px;cursor:pointer}.button.alt{background:transparent}.note{font-size:12px;color:#aeb4c0;line-height:1.45;margin:18px 0 0}.status{font-size:13px;color:#86ebb0;min-height:20px}@media(max-width:540px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}}</style></head><body><main class='card'><div class='eyebrow'>DMI / ORDEN DE REPARTO</div><h1 class='brand'>ENVIAR <b>PEDIDO</b></h1><p class='sub'>Abre la ruta, inicia el reparto y permite la ubicación para que el cliente pueda seguir el pedido.</p><div class='code'>""" + seguro(pedido.get("orden_envio") or f"ENV-{pedido.get('id')}") + """</div><section class='grid'><div class='field'><span>CLIENTE</span><strong>""" + seguro(pedido.get("nombre")) + """</strong></div><div class='field'><span>TELÉFONO</span><strong>""" + seguro(pedido.get("telefono")) + """</strong></div><div class='field wide'><span>DIRECCIÓN DE ENTREGA</span><strong>""" + seguro(direccion) + """</strong></div>""" + bloque_referencia + """</section><div class='actions'>""" + boton_ruta + """<button class='button' id='iniciar' type='button'>INICIAR REPARTO Y COMPARTIR UBICACIÓN</button><div id='estado' class='status'></div></div><p class='note'>Mantén esta página abierta y permite la ubicación mientras realizas el envío.</p></main><script>const iniciarEndpoint=""" + json.dumps(iniciar_endpoint) + """,ubicacionEndpoint=""" + json.dumps(ubicacion_endpoint) + """,estado=document.getElementById('estado');let activo=false;async function enviar(pos){const{latitude:a,longitude:b}=pos.coords;try{await fetch(ubicacionEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitud:a,longitud:b})})}catch(_){}}document.getElementById('iniciar').addEventListener('click',async()=>{const b=document.getElementById('iniciar');b.disabled=true;try{await fetch(iniciarEndpoint,{method:'POST'});if(!navigator.geolocation){estado.textContent='Este dispositivo no permite compartir ubicación.';return}if(!activo){activo=true;navigator.geolocation.watchPosition(enviar,()=>{estado.textContent='No pudimos obtener la ubicación. Revisa los permisos.'},{enableHighAccuracy:true,maximumAge:30000,timeout:15000})}estado.textContent='Reparto iniciado. Tu ubicación se está compartiendo con el cliente.'}catch(_){estado.textContent='No fue posible iniciar el reparto. Intenta nuevamente.';b.disabled=false}});</script></body></html>"""


@app.get("/api/repartidor/envio/{pedido_id}", response_class=HTMLResponse)
async def orden_envio_repartidor(pedido_id: int, request: Request, token: str = ""):
    try:
        with engine.connect() as conn:
            pedido = _pedido_repartidor_valido(conn, pedido_id, token)
        if not pedido:
            raise HTTPException(status_code=404, detail="La orden de envio no existe o el enlace no es valido")
        return HTMLResponse(_ficha_orden_envio(dict(pedido), f"/api/repartidor/envios/{pedido_id}/iniciar?token={quote(token)}", f"/api/repartidor/envios/{pedido_id}/ubicacion?token={quote(token)}"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="No fue posible abrir la orden de envio") from e


@app.post("/api/repartidor/envios/{pedido_id}/iniciar")
async def iniciar_envio_repartidor(pedido_id: int, request: Request, token: str = ""):
    try:
        with engine.connect() as conn:
            if not _pedido_repartidor_valido(conn, pedido_id, token):
                return JSONResponse({"error": "Enlace de reparto no valido"}, status_code=404)
            conn.execute(text("""UPDATE public.pedidos SET estado=CASE WHEN estado IN ('entregado','cancelado') THEN estado ELSE 'en_camino' END,
                novedad=CASE WHEN estado IN ('entregado','cancelado') THEN novedad ELSE 'Tu pedido esta en camino con el repartidor asignado.' END WHERE id=:id"""), {"id": pedido_id})
            conn.commit()
        return JSONResponse({"ok": True})
    except Exception:
        return JSONResponse({"error": "No fue posible iniciar el envio"}, status_code=500)


@app.post("/api/repartidor/envios/{pedido_id}/ubicacion")
async def actualizar_ubicacion_repartidor(pedido_id: int, request: Request, token: str = ""):
    try:
        datos = await request.json()
        latitud, longitud = float(datos.get("latitud")), float(datos.get("longitud"))
        if not (-90 <= latitud <= 90 and -180 <= longitud <= 180):
            return JSONResponse({"error": "Ubicacion no valida"}, status_code=400)
        with engine.connect() as conn:
            if not _pedido_repartidor_valido(conn, pedido_id, token):
                return JSONResponse({"error": "Enlace de reparto no valido"}, status_code=404)
            conn.execute(text("""UPDATE public.pedidos SET latitud_repartidor=:latitud, longitud_repartidor=:longitud,
                ubicacion_actualizada_en=NOW(), estado=CASE WHEN estado IN ('entregado','cancelado') THEN estado ELSE 'en_camino' END WHERE id=:id"""), {"id": pedido_id, "latitud": latitud, "longitud": longitud})
            conn.commit()
        return JSONResponse({"ok": True})
    except (TypeError, ValueError):
        return JSONResponse({"error": "Ubicacion no valida"}, status_code=400)
    except Exception:
        return JSONResponse({"error": "No fue posible actualizar la ubicacion"}, status_code=500)


#  GET /configuracion 
@app.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")

    error_msg   = request.query_params.get("error")
    success_msg = request.query_params.get("success")

    ctx = {
        "usuario":          usuario,
        "error":            error_msg,
        "success_msg":      success_msg,
        "ciudades":         [],
        "tipovehiculos":    [],
        "metodospago":      [],
        "productosprecios": [],
        "serviciosprecios": [],
        "inventario":       [],
        "oficinas":         [],
        "servicios":        [],
        "tiporeparacion":   [],
        "pedidos":          [],
        "pedidos_catalogo": [],
        "productos":        [],
        "movimientos":      [],
        "usuarios_desactivados": [],
        "empleados":        [],
    }

    try:
        with engine.connect() as conn:
            load_errors = []

            def fetch(query, label="datos"):
                try:
                    return [dict(r) for r in conn.execute(text(query)).mappings().fetchall()]
                except Exception as e:
                    load_errors.append(f"{label}: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    return []

            try:
                asegurar_servicios_base(conn)
            except Exception as e:
                load_errors.append("servicios base: " + str(e))
                conn.rollback()
            ctx["ciudades"]         = fetch("SELECT * FROM dmi.ciudades ORDER BY idciudades", "ciudades")
            ctx["tipovehiculos"]    = fetch("SELECT * FROM dmi.tipovehiculos ORDER BY idtipovehiculos", "tipos de vehiculo")
            ctx["metodospago"]      = fetch("SELECT * FROM dmi.metodopago ORDER BY idmetodopago", "metodos de pago")
            ctx["productosprecios"] = fetch("""
                SELECT
                    id AS idproductoprecio,
                    codigo AS codigoproductoprecio,
                    nombre AS descripcionprprecio,
                    precio_venta AS valor
                FROM dmi.inventario_catalogo
                WHERE COALESCE(activo, TRUE) = TRUE
                ORDER BY nombre
            """, "precios producto desde catalogo")
            ctx["serviciosprecios"] = []
            ctx["inventario"]       = fetch("""
                SELECT
                    id AS idinventario,
                    codigo AS codigoinventario,
                    nombre AS descripcioninventario,
                    nombre AS "Descripciontario",
                    cantidad,
                    precio_costo AS costo_unitario,
                    'UND' AS unidad_medida,
                    CASE WHEN COALESCE(activo, TRUE) THEN 'activo' ELSE 'desactivado' END AS estado
                FROM dmi.inventario_catalogo
                WHERE COALESCE(activo, TRUE) = TRUE
                ORDER BY nombre
            """, "inventario desde catalogo")
            ctx["oficinas"] = fetch("""
                SELECT
                    o.*,
                    c.descripcion_ciudad,
                    c.codigo_ciudad,
                    i.codigo AS codigoinventario,
                    i.nombre AS descripcioninventario
                FROM dmi.oficinas o
                LEFT JOIN dmi.ciudades c ON c.idciudades = o.ciudades_idciudades
                LEFT JOIN dmi.inventario_catalogo i ON i.id = o.inventario_idinventario
                ORDER BY o.idoficinas
            """, "oficinas")
            ctx["servicios"] = fetch("""
                SELECT
                    s.*,
                    NULL::varchar AS descripcionserviciosprecio,
                    NULL::varchar AS precioserviciosprecio,
                    pe.codigopedido
                FROM dmi.servicios s
                LEFT JOIN dmi.pedido pe ON pe.idpedido = s.pedido_idpedido
                ORDER BY s.idservicios
            """, "servicios")
            ctx["tiporeparacion"] = fetch("""
                SELECT
                    tr.*,
                    s.descripcionservicio,
                    pe.codigopedido
                FROM dmi.tiporeparacion tr
                LEFT JOIN dmi.servicios s ON s.idservicios = tr.servicios_idservicios
                LEFT JOIN dmi.pedido pe ON pe.idpedido = tr.pedido_idpedido
                ORDER BY tr.idtiporeparacion
            """, "tipos reparacion")
            ctx["pedidos"]          = fetch("SELECT * FROM dmi.pedido ORDER BY idpedido DESC LIMIT 50", "pedidos")
            if table_exists(conn, "public", "pedidos"):
                ctx["pedidos_catalogo"] = fetch("""
                    SELECT p.*, u.nombre AS cliente_nombre
                    FROM public.pedidos p
                    LEFT JOIN dmi.usuarios u ON u.idusuarios = p.usuarios_idusuarios
                    ORDER BY p.created_at DESC, p.id DESC
                    LIMIT 100
                """, "pedidos de catalogo")
            ctx["productos"]        = fetch("""
                SELECT
                    id AS idproductos,
                    codigo AS codigoproductos,
                    nombre AS descripcionproductos,
                    precio_venta AS descripcionprprecio,
                    precio_venta AS valor_precio,
                    NULL::varchar AS codigopedido,
                    NULL::int AS pedido_idpedido,
                    id AS productoprecio_idproductoprecio
                FROM dmi.inventario_catalogo
                WHERE COALESCE(activo, TRUE) = TRUE
                ORDER BY nombre
                LIMIT 100
            """, "productos desde catalogo")
            ctx["movimientos"] = fetch("""
                SELECT m.*, i.codigo AS codigoinventario, i.nombre AS descripcioninventario 
                FROM dmi.movimientos_inventario m
                LEFT JOIN dmi.inventario_catalogo i ON i.id = m.inventario_id
                ORDER BY m.fecha DESC 
                LIMIT 50
            """, "movimientos")
            ctx["metodopago"] = ctx["metodospago"]
            ctx["serviciosprecio"] = ctx["serviciosprecios"]
            ctx["productoprecio"] = ctx["productosprecios"]
            ctx["movimientos_inventario"] = ctx["movimientos"]
            ctx["vehiculos"] = fetch("SELECT * FROM dmi.vehiculos ORDER BY idvehiculo", "vehiculos")
            usuario_columnas = table_columns(conn, "dmi", "usuarios")
            usuarios_extra_select = []
            usuarios_extra_select.append("estado" if "estado" in usuario_columnas else "NULL::varchar AS estado")
            usuarios_extra_select.append("activo" if "activo" in usuario_columnas else "NULL::boolean AS activo")
            usuarios_base_select = f"""
                SELECT
                    idusuarios,
                    id,
                    nombre,
                    apellidos,
                    documento,
                    tipodedocumento,
                    email,
                    telefono,
                    usuarionombre,
                    fechadenacimiento::text AS fechadenacimiento,
                    rol,
                    vehiculos_idvehiculo,
                    {', '.join(usuarios_extra_select)}
                FROM dmi.usuarios
            """
            if "activo" in usuario_columnas:
                ctx["usuarios"] = fetch(usuarios_base_select + " WHERE COALESCE(activo, TRUE) = TRUE ORDER BY idusuarios", "usuarios")
                ctx["usuarios_desactivados"] = fetch(usuarios_base_select + " WHERE activo = FALSE ORDER BY idusuarios DESC", "usuarios desactivados")
            elif "estado" in usuario_columnas:
                ctx["usuarios"] = fetch(usuarios_base_select + " WHERE COALESCE(lower(estado), 'activo') NOT IN ('desactivado', 'inactivo', 'inactive') ORDER BY idusuarios", "usuarios")
                ctx["usuarios_desactivados"] = fetch(usuarios_base_select + " WHERE lower(COALESCE(estado, '')) IN ('desactivado', 'inactivo', 'inactive') ORDER BY idusuarios DESC", "usuarios desactivados")
            else:
                ctx["usuarios"] = fetch(usuarios_base_select + " ORDER BY idusuarios", "usuarios")
                ctx["usuarios_desactivados"] = []
            if table_exists(conn, "dmi", "empleados"):
                empleados_cols = table_columns(conn, "dmi", "empleados")
                empleado_pk = resolve_table_pk(conn, "empleados", "idempleado") or "id"

                def emp_expr(alias, candidates, sql_type="varchar"):
                    for col in candidates:
                        if col in empleados_cols:
                            return f"{col} AS {alias}"
                    return f"NULL::{sql_type} AS {alias}"

                empleados_select = f"""
                    SELECT
                        {empleado_pk} AS idempleado,
                        {emp_expr('codigo_empleado', ['codigo_empleado', 'codigoempleado', 'codigo'])},
                        {emp_expr('nombre', ['nombre', 'nombres'])},
                        {emp_expr('apellido', ['apellido', 'apellidos'])},
                        {emp_expr('documento', ['documento', 'numero_documento', 'cedula'])},
                        {emp_expr('telefono', ['telefono', 'celular'])},
                        {emp_expr('email', ['email', 'correo'])},
                        {emp_expr('rol', ['rol', 'cargo', 'tipo'])},
                        {emp_expr('estado', ['estado'])},
                        {emp_expr('activo', ['activo'], 'boolean')}
                    FROM dmi.empleados
                """
                if "activo" in empleados_cols:
                    empleados_select += " WHERE COALESCE(activo, TRUE) = TRUE"
                elif "estado" in empleados_cols:
                    empleados_select += " WHERE COALESCE(lower(estado), 'activo') NOT IN ('desactivado', 'inactivo', 'inactive')"
                ctx["empleados"] = fetch(empleados_select + f" ORDER BY {empleado_pk}", "empleados")

            ctx["citas"] = fetch("SELECT * FROM dmi.citas ORDER BY idcita DESC", "citas")

            if load_errors and not ctx["error"]:
                ctx["error"] = "Algunas secciones no cargaron: " + " | ".join(load_errors[:3])

    except Exception as e:
        ctx["error"] = str(e)
        
    return templates.TemplateResponse(
        request=request,
        name="configuracion.html",
        context=ctx,
    )

#========================= INVENTARIO ======================================
@app.get("/api/inventario")
async def api_inventario():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    id AS idinventario,
                    codigo AS codigoinventario,
                    nombre AS descripcioninventario,
                    nombre AS "Descripciontario",
                    cantidad,
                    precio_costo AS costo_unitario,
                    'UND' AS unidad_medida,
                    CASE WHEN COALESCE(activo, TRUE) THEN 'activo' ELSE 'desactivado' END AS estado
                FROM dmi.inventario_catalogo
                WHERE COALESCE(activo, TRUE) = TRUE
                ORDER BY nombre
            """)).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/catalogo-productos")
async def api_catalogo_productos():
    try:
        with engine.connect() as conn:
            if not table_exists(conn, "dmi", "inventario_catalogo"):
                return JSONResponse([])

            rows = conn.execute(text("""
                SELECT
                    id,
                    id_original,
                    codigo,
                    nombre,
                    precio_costo,
                    precio_venta,
                    cantidad,
                    categoria,
                    departamento,
                    imagen_url,
                    activo
                FROM dmi.inventario_catalogo
                WHERE COALESCE(activo, TRUE) = TRUE
                ORDER BY nombre
                LIMIT 1000
            """)).mappings().fetchall()

            productos = []
            for row in rows:
                item = dict(row)
                productos.append({
                    "id": item.get("id") or item.get("id_original"),
                    "codigo": item.get("codigo") or "",
                    "nombre": item.get("nombre") or "Producto sin nombre",
                    "precioCosto": float(item.get("precio_costo") or 0),
                    "precioVenta": float(item.get("precio_venta") or 0),
                    "inventario": int(item.get("cantidad") or 0),
                    "categoria": item.get("categoria") or "General",
                    "departamento": item.get("departamento") or "",
                    "image": item.get("imagen_url") or "",
                    "imagen_url": item.get("imagen_url") or "",
                    "activo": bool(item.get("activo", True)),
                })

            return JSONResponse(productos)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.put("/api/catalogo-productos/{producto_id}")
async def api_actualizar_catalogo_producto(producto_id: int, payload: dict):
    try:
        with engine.begin() as conn:
            if not table_exists(conn, "dmi", "inventario_catalogo"):
                return JSONResponse({"error": "No existe la tabla inventario_catalogo"}, status_code=404)

            conn.execute(text("""
                UPDATE dmi.inventario_catalogo
                SET
                    codigo = :codigo,
                    nombre = :nombre,
                    precio_costo = :precio_costo,
                    precio_venta = :precio_venta,
                    cantidad = :cantidad,
                    categoria = :categoria,
                    departamento = :departamento,
                    imagen_url = :imagen_url
                WHERE id = :id
                   OR id_original = :id
            """), {
                "id": producto_id,
                "codigo": payload.get("codigo") or "",
                "nombre": payload.get("nombre") or "Producto sin nombre",
                "precio_costo": payload.get("precioCosto") or payload.get("precio_costo") or 0,
                "precio_venta": payload.get("precioVenta") or payload.get("precio_venta") or 0,
                "cantidad": payload.get("inventario") or payload.get("cantidad") or 0,
                "categoria": payload.get("categoria") or "General",
                "departamento": payload.get("departamento") or "",
                "imagen_url": payload.get("image") or payload.get("imagen_url") or "",
            })

            row = conn.execute(text("""
                SELECT
                    id,
                    id_original,
                    codigo,
                    nombre,
                    precio_costo,
                    precio_venta,
                    cantidad,
                    categoria,
                    departamento,
                    imagen_url,
                    activo
                FROM dmi.inventario_catalogo
                WHERE id = :id
                   OR id_original = :id
                LIMIT 1
            """), {"id": producto_id}).mappings().first()

            if not row:
                return JSONResponse({"error": "Producto no encontrado"}, status_code=404)

            item = dict(row)
            return JSONResponse({
                "id": item.get("id") or item.get("id_original"),
                "codigo": item.get("codigo") or "",
                "nombre": item.get("nombre") or "Producto sin nombre",
                "precioCosto": float(item.get("precio_costo") or 0),
                "precioVenta": float(item.get("precio_venta") or 0),
                "inventario": int(item.get("cantidad") or 0),
                "categoria": item.get("categoria") or "General",
                "departamento": item.get("departamento") or "",
                "image": item.get("imagen_url") or "",
                "imagen_url": item.get("imagen_url") or "",
                "activo": bool(item.get("activo", True)),
            })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
#=========================== MOVIMIENTOS INVENTARIO =============================
@app.get("/api/movimientos_inventario")
async def api_movimientos():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT m.*, i.codigo AS codigoinventario 
                FROM dmi.movimientos_inventario m
                LEFT JOIN dmi.inventario_catalogo i ON i.id = m.inventario_id
                ORDER BY m.fecha DESC LIMIT 50
            """)).mappings().fetchall()
            result = []
            for r in data:
                row = dict(r)
                if row.get("fecha"): row["fecha"] = str(row["fecha"])
                result.append(row)
            return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
#====================== TIPO VEHICULO ============================
@app.get("/api/tipo_vehiculo")
async def api_tipo_vehiculo():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    idtipovehiculos,
                    idtipovehiculos as id,
                    codigotipovehiculos,
                    vehiculo,
                    vehiculo as nombre
                FROM dmi.tipovehiculos
                ORDER BY idtipovehiculos
            """)).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/tipovehiculos")
async def api_tipovehiculos():
    return await api_tipo_vehiculo()

@app.post("/api/tipovehiculos/nuevo")
async def api_crear_tipo_vehiculo(request: Request):
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            nombre = (body.get("vehiculo") or body.get("nombre") or "").strip()
        else:
            form = await request.form()
            nombre = (form.get("vehiculo") or form.get("nombre") or "").strip()

        if not nombre:
            return JSONResponse({"error": "Escribe el tipo de vehiculo"}, status_code=400)

        codigo_base = "".join(ch for ch in nombre.upper() if ch.isalnum())[:12] or "TIPO"
        codigo = f"TV-{codigo_base}-{datetime.utcnow().strftime('%H%M%S%f')[:8]}"

        with engine.connect() as conn:
            existente = conn.execute(
                text("""
                    SELECT idtipovehiculos, codigotipovehiculos, vehiculo
                    FROM dmi.tipovehiculos
                    WHERE lower(vehiculo) = lower(:nombre)
                    LIMIT 1
                """),
                {"nombre": nombre},
            ).mappings().fetchone()

            if existente:
                return JSONResponse(dict(existente))

            result = conn.execute(
                text("""
                    INSERT INTO dmi.tipovehiculos (codigotipovehiculos, vehiculo)
                    VALUES (:codigo, :vehiculo)
                    RETURNING idtipovehiculos, codigotipovehiculos, vehiculo
                """),
                {"codigo": codigo, "vehiculo": nombre},
            ).mappings().fetchone()
            conn.commit()

            return JSONResponse(dict(result))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

#===================== PRECIOS PRODUCTO =========================
@app.get("/api/precios_producto")
async def api_precios_producto():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    id,
                    codigo AS codigoproductoprecio,
                    nombre AS descripcionprprecio,
                    precio_venta AS precio
                FROM dmi.inventario_catalogo
                WHERE COALESCE(activo, TRUE) = TRUE
                ORDER BY nombre
            """)).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

#===================== SERVICIOS PRECIO ========================
@app.get("/api/servicios")
async def api_servicios():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    s.idservicios,
                    s.codigoservicio,
                    s.descripcionservicio,
                    s.pedido_idpedido,
                    NULL::int AS serviciosprecio_idserviciosprecio,
                    NULL::varchar AS descripcionserviciosprecio,
                    NULL::varchar AS precioserviciosprecio,
                    pe.codigopedido
                FROM dmi.servicios s
                LEFT JOIN dmi.pedido pe ON pe.idpedido = s.pedido_idpedido
                ORDER BY s.idservicios
            """)).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/precios_servicio")
async def api_precios_servicio():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT
                    idservicios AS id,
                    codigoservicio AS codigoserviciosprecio,
                    descripcionservicio AS descripcionserviciosprecio,
                    NULL::varchar AS precio
                FROM dmi.servicios
                ORDER BY idservicios
            """)).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
#===================== TIPOS DE REPARACION =====================
@app.get("/api/tipo_reparacion")
async def api_tipo_reparacion():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT idtiporeparacion as id, codigotiporeparacion, descripciontiporeparacion as nombre FROM dmi.tiporeparacion ORDER BY idtiporeparacion")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

#======================= METODOS DE PAGO ======================
@app.get("/api/metodos_pago")
async def api_metodos_pago():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT idmetodopago as id, codigompago, descripcionmpago as nombre FROM dmi.metodopago ORDER BY idmetodopago")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/config/ciudades/nueva")
async def crear_ciudad(
    access_token: str = Cookie(None),
    codigo_ciudad: str = Form(...),
    descripcion_ciudad: str = Form(...),
    codigo_postal: str = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.ciudades (codigo_ciudad, descripcion_ciudad, codigo_postal)
                    VALUES (:codigo, :descripcion, :postal)
                """),
                {"codigo": codigo_ciudad, "descripcion": descripcion_ciudad, "postal": codigo_postal}
            )
            conn.commit()
        return config_redirect("ciudades", "Ciudad creada con exito")
    except Exception as e:
        return config_redirect("ciudades", str(e), False)


@app.post("/config/metodopago/nuevo")
async def config_crear_metodo_pago(
    access_token: str = Cookie(None),
    codigompago: str = Form(...),
    descripcionmpago: str = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO dmi.metodopago (codigompago, descripcionmpago) VALUES (:codigo, :descripcion)"),
                {"codigo": codigompago, "descripcion": descripcionmpago},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Metodo de pago creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/config/tipovehiculos/nuevo")
async def config_crear_tipo_vehiculo(
    access_token: str = Cookie(None),
    codigotipovehiculos: str = Form(...),
    vehiculo: str = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO dmi.tipovehiculos (codigotipovehiculos, vehiculo) VALUES (:codigo, :vehiculo)"),
                {"codigo": codigotipovehiculos, "vehiculo": vehiculo},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo de vehiculo creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/config/vehiculos/nuevo")
async def config_crear_vehiculo(
    access_token: str = Cookie(None),
    codigovehiculo: str = Form(...),
    descripcionvehiculo: str = Form(...),
    motor: str = Form(...),
    cantidad_asientos: str = Form(...),
    placa: str = Form(...),
    capacidad: str = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    tipovehiculos_idtipovehiculos: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.vehiculos
                    (codigovehiculo, descripcionvehiculo, motor, cantidad_asientos, placa, capacidad, marca, modelo, tipovehiculos_idtipovehiculos)
                    VALUES
                    (:codigo, :descripcion, :motor, :asientos, :placa, :capacidad, :marca, :modelo, :tipo)
                """),
                {
                    "codigo": codigovehiculo,
                    "descripcion": descripcionvehiculo,
                    "motor": motor,
                    "asientos": cantidad_asientos,
                    "placa": placa,
                    "capacidad": capacidad,
                    "marca": marca,
                    "modelo": modelo,
                    "tipo": tipovehiculos_idtipovehiculos,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Vehiculo creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/config/citas/nueva")
async def config_crear_cita(
    access_token: str = Cookie(None),
    vehiculos_idvehiculo: int = Form(...),
    fecha: str = Form(...),
    hora: str = Form(...),
    motivo: str = Form(...),
    estado: str = Form("pendiente"),
    notas: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.citas (vehiculos_idvehiculo, fecha, hora, motivo, estado, notas)
                    VALUES (:vehiculo, CAST(:fecha AS date), :hora, :motivo, :estado, :notas)
                """),
                {"vehiculo": vehiculos_idvehiculo, "fecha": fecha, "hora": hora, "motivo": motivo, "estado": estado, "notas": notas},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Cita creada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/config/inventario/nuevo")
async def config_crear_inventario(
    access_token: str = Cookie(None),
    codigoinventario: str = Form(...),
    descripcioninventario: str = Form(...),
    pedido_idpedido: Optional[int] = Form(None),
    cantidad: Optional[float] = Form(0),
    costo_unitario: Optional[float] = Form(None),
    unidad_medida: Optional[str] = Form("UND"),
    estado: Optional[str] = Form("activo"),
    oficinas_idoficinas: Optional[int] = Form(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.inventario_catalogo
                    (codigo, nombre, precio_costo, precio_venta, cantidad, categoria, departamento, activo)
                    VALUES (:codigo, :descripcion, COALESCE(:costo, 0), COALESCE(:costo, 0), COALESCE(:cantidad, 0), 'General', COALESCE(:unidad, 'UND'), COALESCE(:estado, 'activo') <> 'desactivado')
                """),
                {
                    "codigo": codigoinventario,
                    "descripcion": descripcioninventario,
                    "pedido": pedido_idpedido,
                    "cantidad": cantidad,
                    "costo": costo_unitario,
                    "unidad": unidad_medida,
                    "estado": estado,
                    "oficina": oficinas_idoficinas,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Inventario creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/admin/inventario-catalogo/{producto_id}/actualizar")
async def actualizar_inventario_catalogo(
    producto_id: int,
    request: Request,
    access_token: str = Cookie(None),
    nombre: str = Form(...),
    codigo: Optional[str] = Form(None),
    precio_costo: Optional[float] = Form(0),
    precio_venta: Optional[float] = Form(0),
    cantidad: Optional[int] = Form(0),
    categoria: Optional[str] = Form(None),
    departamento: Optional[str] = Form(None),
    imagen_url: Optional[str] = Form(None),
    activo: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/")

    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.inventario_catalogo SET
                        codigo = :codigo,
                        nombre = :nombre,
                        precio_costo = :precio_costo,
                        precio_venta = :precio_venta,
                        cantidad = :cantidad,
                        categoria = :categoria,
                        departamento = :departamento,
                        imagen_url = :imagen_url,
                        activo = :activo,
                        actualizado_en = NOW()
                    WHERE id = :id
                """),
                {
                    "id": producto_id,
                    "codigo": codigo,
                    "nombre": nombre,
                    "precio_costo": precio_costo or 0,
                    "precio_venta": precio_venta or 0,
                    "cantidad": cantidad or 0,
                    "categoria": categoria,
                    "departamento": departamento,
                    "imagen_url": imagen_url,
                    "activo": activo == "on",
                },
            )
            conn.commit()
        return RedirectResponse(url="/admin/inventario?success=Inventario actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/inventario?error={quote(str(e))}", status_code=302)


@app.post("/config/usuarios/nuevo")
async def config_crear_usuario(
    email: str = Form(...),
    password: str = Form(...),
    nombre: str = Form(...),
    apellidos: str = Form(...),
    documento: str = Form(...),
    tipodedocumento: str = Form(...),
    fechadenacimiento: str = Form(...),
    telefono: str = Form(...),
    usuarionombre: str = Form(...),
    rol: str = Form("usuario"),
    access_token: str = Cookie(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return RedirectResponse(url="/configuracion?error=No se pudo crear usuario", status_code=302)
        supabase.schema("dmi").table("usuarios").insert({
            "id": res.user.id,
            "usuarionombre": usuarionombre,
            "nombre": nombre,
            "apellidos": apellidos,
            "email": email,
            "documento": documento,
            "tipodedocumento": tipodedocumento,
            "fechadenacimiento": fechadenacimiento,
            "telefono": telefono,
            "rol": rol,
        }).execute()
        return RedirectResponse(url="/configuracion?success=Usuario creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


CONFIG_TABLES = {
    "ciudades": {
        "table": "ciudades",
        "pk": "idciudades",
        "fields": ["codigo_ciudad", "descripcion_ciudad", "codigo_postal"],
    },
    "oficinas": {
        "table": "oficinas",
        "pk": "idoficinas",
        "fields": ["codigo_oficina", "direccion", "telefono_oficina", "descripcionof", "ciudades_idciudades", "inventario_idinventario"],
    },
    "metodopago": {
        "table": "metodopago",
        "pk": "idmetodopago",
        "fields": ["codigompago", "descripcionmpago"],
    },
    "inventario": {
        "table": "inventario",
        "pk": "idinventario",
        "fields": ["codigoinventario", "descripcioninventario", "pedido_idpedido", "cantidad", "costo_unitario", "unidad_medida", "estado", "oficinas_idoficinas"],
    },
    "movimientos": {
        "table": "movimientos_inventario",
        "pk": "idmovimiento",
        "fields": ["inventario_id", "tipo_movimiento", "cantidad", "costo_unitario", "valor_total", "motivo", "referencia_id", "usuario_id"],
    },
    "vehiculos": {
        "table": "vehiculos",
        "pk": "idvehiculo",
        "fields": ["codigovehiculo", "descripcionvehiculo", "motor", "cantidad_asientos", "placa", "capacidad", "marca", "modelo", "tipovehiculos_idtipovehiculos"],
    },
    "tipovehiculos": {
        "table": "tipovehiculos",
        "pk": "idtipovehiculos",
        "fields": ["codigotipovehiculos", "vehiculo"],
    },
    "servicios": {
        "table": "servicios",
        "pk": "idservicios",
        "fields": ["codigoservicio", "descripcionservicio", "pedido_idpedido", "serviciosprecio_idserviciosprecio"],
    },
    "tiporeparacion": {
        "table": "tiporeparacion",
        "pk": "idtiporeparacion",
        "fields": ["codigotiporeparacion", "descripciontiporeparacion", "servicios_idservicios", "pedido_idpedido"],
    },
    "productos": {
        "table": "productos",
        "pk": "idproductos",
        "fields": ["codigoproductos", "descripcionproductos", "productoprecio_idproductoprecio", "pedido_idpedido"],
    },
    "serviciosprecio": {
        "table": "serviciosprecio",
        "pk": "idserviciosprecio",
        "fields": ["codigoserviciosprecio", "descripcionserviciosprecio", "precioserviciosprecio"],
    },
    "productoprecio": {
        "table": "productoprecio",
        "pk": "idproductoprecio",
        "fields": ["codigoproductoprecio", "descripcionprprecio", "valor"],
    },
    "empleados": {
        "table": "empleados",
        "pk": "idempleado",
        "fields": [
            "codigo_empleado", "codigoempleado", "codigo",
            "nombre", "nombres", "apellido", "apellidos",
            "documento", "numero_documento", "cedula",
            "telefono", "celular", "email", "correo",
            "rol", "cargo", "tipo", "especialidad", "estado", "activo"
        ],
    },
    "usuarios": {
        "table": "usuarios",
        "pk": "idusuarios",
        "fields": ["nombre", "apellidos", "documento", "tipodedocumento", "email", "telefono", "usuarionombre", "fechadenacimiento", "rol"],
        "select": """
            SELECT
                idusuarios,
                id,
                nombre,
                apellidos,
                documento,
                tipodedocumento,
                email,
                telefono,
                usuarionombre,
                fechadenacimiento::text AS fechadenacimiento,
                rol,
                vehiculos_idvehiculo
            FROM dmi.usuarios
            WHERE idusuarios = :id
        """,
    },
    "citas": {
        "table": "citas",
        "pk": "idcita",
        "fields": ["vehiculos_idvehiculo", "fecha", "hora", "motivo", "estado", "notas"],
    },
    "pedidos": {
        "table": "pedido",
        "pk": "idpedido",
        "fields": ["fecha", "codigopedido", "metodopago_idmetodopago", "fecha_cita", "estado", "descripcion", "oficinas_idoficinas"],
    },
}


def config_user_or_redirect(access_token: str):
    usuario = obtener_usuario(access_token)
    return usuario if es_admin(usuario) else None


def normalize_config_value(value):
    if value == "":
        return None
    return value


def json_safe(value):
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def json_row(row):
    return {key: json_safe(value) for key, value in dict(row).items()}


def table_exists(conn, schema: str, table: str) -> bool:
    return conn.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema AND table_name = :table
            )
        """),
        {"schema": schema, "table": table},
    ).scalar()


def table_columns(conn, schema: str, table: str) -> set:
    rows = conn.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
        """),
        {"schema": schema, "table": table},
    ).fetchall()
    return {row[0] for row in rows}


def resolve_table_pk(conn, table: str, preferred: str = None) -> Optional[str]:
    cols = table_columns(conn, "dmi", table)
    base = table[:-1] if table.endswith("s") else table
    candidates = [preferred, f"id{base}", f"id{table}", "id"]
    for candidate in candidates:
        if candidate and candidate in cols:
            return candidate
    return preferred if preferred in cols else None


def query_rows(conn, sql: str, params: dict = None) -> list:
    return [json_row(row) for row in conn.execute(text(sql), params or {}).mappings().fetchall()]


def normalize_cart_items(value):
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return []
    if isinstance(value, dict):
        for key in ("productos", "items", "carrito", "cart"):
            if isinstance(value.get(key), list):
                return value.get(key)
        return [value]
    if isinstance(value, list):
        return value
    return []


def config_redirect(entity: str, message: str, ok: bool = True):
    key = "success" if ok else "error"
    return RedirectResponse(url=f"/configuracion?{key}={quote(str(message))}#{entity}", status_code=302)


@app.get("/admin/usuario/{usuario_id}/ficha")
async def admin_usuario_ficha(usuario_id: int, request: Request, access_token: str = Cookie(None)):
    usuario_actual = obtener_usuario(access_token, request)
    if not es_admin(usuario_actual):
        return JSONResponse({"error": "No tienes permiso"}, status_code=403)

    try:
        with engine.connect() as conn:
            usuario = conn.execute(
                text("""
                    SELECT
                        idusuarios,
                        id,
                        nombre,
                        apellidos,
                        documento,
                        tipodedocumento,
                        email,
                        telefono,
                        usuarionombre,
                        fechadenacimiento::text AS fechadenacimiento,
                        COALESCE(rol, 'usuario') AS rol,
                        vehiculos_idvehiculo
                    FROM dmi.usuarios
                    WHERE idusuarios = :id
                """),
                {"id": usuario_id},
            ).mappings().fetchone()

            if not usuario:
                return JSONResponse({"error": "Usuario no encontrado"}, status_code=404)

            usuario = json_row(usuario)
            vehiculo_id = usuario.get("vehiculos_idvehiculo")
            vehiculo_columnas = table_columns(conn, "dmi", "vehiculos") if table_exists(conn, "dmi", "vehiculos") else set()

            vehiculos = []
            vehiculo_where = []
            vehiculo_params = {}
            if "cliente_id" in vehiculo_columnas:
                vehiculo_where.append("v.cliente_id = :usuario_id")
                vehiculo_params["usuario_id"] = usuario_id
            if vehiculo_id:
                vehiculo_where.append("v.idvehiculo = :vehiculo_id")
                vehiculo_params["vehiculo_id"] = vehiculo_id

            if vehiculo_where:
                vehiculos = query_rows(
                    conn,
                    f"""
                    SELECT DISTINCT
                        v.idvehiculo,
                        v.codigovehiculo,
                        v.descripcionvehiculo,
                        v.motor,
                        v.cantidad_asientos,
                        v.placa,
                        v.capacidad,
                        v.marca,
                        v.modelo,
                        tv.vehiculo AS tipo_vehiculo
                    FROM dmi.vehiculos v
                    LEFT JOIN dmi.tipovehiculos tv ON tv.idtipovehiculos = v.tipovehiculos_idtipovehiculos
                    WHERE {' OR '.join(vehiculo_where)}
                    ORDER BY v.idvehiculo
                    """,
                    vehiculo_params,
                )

            citas = []
            vehiculo_ids = [v.get("idvehiculo") for v in vehiculos if v.get("idvehiculo")]
            if vehiculo_ids:
                cita_placeholders = ", ".join(f":vehiculo_{idx}" for idx, _ in enumerate(vehiculo_ids))
                cita_params = {f"vehiculo_{idx}": value for idx, value in enumerate(vehiculo_ids)}
                citas = query_rows(
                    conn,
                    f"""
                    SELECT
                        c.idcita,
                        c.fecha,
                        c.hora,
                        c.motivo,
                        c.estado,
                        c.reprogramada_en,
                        c.notas,
                        v.placa,
                        COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo
                    FROM dmi.citas c
                    LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    WHERE c.vehiculos_idvehiculo IN ({cita_placeholders})
                    ORDER BY c.fecha DESC, c.hora DESC
                    """,
                    cita_params,
                )

            pedidos = []
            pagos = []
            productos = []
            notas = []

            if table_exists(conn, "dmi", "pedido"):
                pedido_columns = table_columns(conn, "dmi", "pedido")
                pedido_where = None
                pedido_params = {}

                if "usuarios_idusuarios" in pedido_columns:
                    pedido_where = "p.usuarios_idusuarios = :usuario_id"
                    pedido_params["usuario_id"] = usuario_id
                elif "usuario_id" in pedido_columns and usuario.get("id"):
                    pedido_where = "p.usuario_id = :auth_id"
                    pedido_params["auth_id"] = usuario.get("id")
                elif "email" in pedido_columns and usuario.get("email"):
                    pedido_where = "LOWER(p.email) = LOWER(:email)"
                    pedido_params["email"] = usuario.get("email")

                if pedido_where:
                    pedidos = query_rows(
                        conn,
                        f"""
                        SELECT
                            p.*,
                            mp.descripcionmpago AS metodo_pago
                        FROM dmi.pedido p
                        LEFT JOIN dmi.metodopago mp ON mp.idmetodopago = p.metodopago_idmetodopago
                        WHERE {pedido_where}
                        ORDER BY p.idpedido DESC
                        """,
                        pedido_params,
                    )
                else:
                    notas.append("Los pedidos de configuracion no tienen una columna que los conecte con usuarios.")

            if table_exists(conn, "public", "pedidos"):
                checkout_columns = table_columns(conn, "public", "pedidos")
                if ("usuarios_idusuarios" in checkout_columns or "email" in checkout_columns) and (usuario.get("idusuarios") or usuario.get("email")):
                    order_column = "id" if "id" in checkout_columns else "created_at" if "created_at" in checkout_columns else None
                    order_sql = f"ORDER BY {order_column} DESC" if order_column else ""
                    cart_field = next((field for field in ("productos", "items", "carrito", "cart") if field in checkout_columns), None)
                    checkout_where, checkout_params = [], {}
                    if "usuarios_idusuarios" in checkout_columns and usuario.get("idusuarios"):
                        checkout_where.append("usuarios_idusuarios = :usuario_id")
                        checkout_params["usuario_id"] = usuario.get("idusuarios")
                    if "email" in checkout_columns and usuario.get("email"):
                        checkout_where.append("LOWER(email) = LOWER(:email)")
                        checkout_params["email"] = usuario.get("email")
                    public_pedidos = query_rows(
                        conn,
                        f"""
                        SELECT *
                        FROM public.pedidos
                        WHERE {' OR '.join(checkout_where)}
                        {order_sql}
                        """,
                        checkout_params,
                    )
                    if cart_field:
                        for pedido in public_pedidos:
                            for item in normalize_cart_items(pedido.get(cart_field)):
                                if not isinstance(item, dict):
                                    item = {"nombre": item}
                                productos.append({
                                    "codigoproductos": item.get("codigo") or item.get("codigoproductos") or item.get("id"),
                                    "descripcionproductos": item.get("nombre") or item.get("descripcion") or item.get("descripcionproductos"),
                                    "valor_precio": item.get("precioVenta") or item.get("precio") or item.get("valor"),
                                    "pedido_idpedido": pedido.get("id") or pedido.get("codigopedido"),
                                })
                    pedidos.extend(public_pedidos)

            pagos = [
                {
                    "id": pedido.get("idpedido") or pedido.get("id"),
                    "codigo": pedido.get("codigopedido") or pedido.get("codigo") or pedido.get("id"),
                    "metodo": pedido.get("metodo_pago") or pedido.get("metodo_pago_id") or pedido.get("metodopago_idmetodopago"),
                    "estado": pedido.get("estado") or "registrado",
                    "total": pedido.get("total"),
                    "fecha": pedido.get("fecha") or pedido.get("created_at"),
                }
                for pedido in pedidos
            ]

            dmi_pedido_ids = [pedido.get("idpedido") for pedido in pedidos if pedido.get("idpedido")]
            if dmi_pedido_ids and table_exists(conn, "dmi", "productos"):
                placeholders = ", ".join(f":pedido_{idx}" for idx, _ in enumerate(dmi_pedido_ids))
                params = {f"pedido_{idx}": value for idx, value in enumerate(dmi_pedido_ids)}
                productos.extend(
                    query_rows(
                        conn,
                        f"""
                        SELECT
                            p.idproductos,
                            p.codigoproductos,
                            p.descripcionproductos,
                            p.pedido_idpedido,
                            pp.descripcionprprecio,
                            pp.valor AS valor_precio
                        FROM dmi.productos p
                        LEFT JOIN dmi.productoprecio pp ON pp.idproductoprecio = p.productoprecio_idproductoprecio
                        WHERE p.pedido_idpedido IN ({placeholders})
                        ORDER BY p.idproductos
                        """,
                        params,
                    )
                )

            if not productos:
                notas.append("El carrito actual se guarda en la pantalla del cliente; solo aparecera aqui cuando el pedido guarde sus productos en la base de datos.")

            facturas = []
            if table_exists(conn, "dmi", "facturas"):
                factura_columns = table_columns(conn, "dmi", "facturas")
                factura_where = None
                factura_params = {}
                if "cliente_id" in factura_columns:
                    factura_where = "f.cliente_id = :usuario_id"
                    factura_params["usuario_id"] = usuario_id
                elif "usuario_id" in factura_columns and usuario.get("id"):
                    factura_where = "f.usuario_id = :auth_id"
                    factura_params["auth_id"] = usuario.get("id")
                if factura_where:
                    facturas = query_rows(conn, f"SELECT f.* FROM dmi.facturas f WHERE {factura_where} ORDER BY f.idfactura DESC", factura_params)

            historial = []
            if table_exists(conn, "dmi", "historial_vehiculo") and vehiculo_ids:
                historial_placeholders = ", ".join(f":historial_vehiculo_{idx}" for idx, _ in enumerate(vehiculo_ids))
                historial_params = {f"historial_vehiculo_{idx}": value for idx, value in enumerate(vehiculo_ids)}
                historial = query_rows(
                    conn,
                    f"""
                    SELECT h.*, v.placa, COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo
                    FROM dmi.historial_vehiculo h
                    LEFT JOIN dmi.vehiculos v ON v.idvehiculo = h.vehiculo_id
                    WHERE h.vehiculo_id IN ({historial_placeholders})
                    ORDER BY h.idhistorial DESC
                    """,
                    historial_params,
                )

            return JSONResponse({
                "usuario": usuario,
                "vehiculos": vehiculos,
                "citas": citas,
                "pedidos": pedidos,
                "pagos": pagos,
                "productos": productos,
                "facturas": facturas,
                "historial": historial,
                "notas": notas,
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/checkout/pedidos")
async def registrar_pedido_checkout(request: Request, access_token: str = Cookie(None)):
    """Guarda la compra en Supabase y la enlaza al usuario autenticado."""
    usuario_actual = obtener_usuario(access_token, request)
    if not usuario_actual:
        return JSONResponse({"error": "Debes iniciar sesion para confirmar una compra"}, status_code=401)

    try:
        body = await request.json()
        items = body.get("items") or []
        datos = body.get("datos") or {}
        if not isinstance(items, list) or not items:
            return JSONResponse({"error": "El carrito no tiene productos"}, status_code=400)
        campos_envio = ("nombre", "telefono", "email", "direccion", "ciudad", "departamento", "barrio")
        if not isinstance(datos, dict) or any(not str(datos.get(campo) or "").strip() for campo in campos_envio):
            return JSONResponse({"error": "Completa los datos de contacto y la direccion de envio"}, status_code=400)

        productos, total_calculado = [], 0.0
        for item in items:
            if not isinstance(item, dict):
                continue
            cantidad = int(item.get("quantity") or item.get("cantidad") or 1)
            precio = float(item.get("precioVenta") or item.get("precio") or item.get("valor") or 0)
            if cantidad < 1 or precio < 0:
                return JSONResponse({"error": "Hay un producto con cantidad o precio no valido"}, status_code=400)
            productos.append({
                "id": item.get("id"),
                "codigo": item.get("codigo") or item.get("codigoproductos"),
                "nombre": item.get("nombre") or item.get("descripcion") or item.get("descripcionproductos") or "Producto DMI",
                "precio": precio,
                "cantidad": cantidad,
            })
            total_calculado += precio * cantidad

        if not productos:
            return JSONResponse({"error": "No se encontraron productos validos en el carrito"}, status_code=400)

        with engine.connect() as conn:
            usuario_cols = table_columns(conn, "dmi", "usuarios")
            campos_usuario = ["idusuarios", "email"] + [campo for campo in ("activo", "estado") if campo in usuario_cols]
            usuario = conn.execute(
                text(f"SELECT {', '.join(campos_usuario)} FROM dmi.usuarios WHERE id::text = :auth_id"),
                {"auth_id": usuario_actual.get("id")},
            ).mappings().fetchone()
            if not usuario:
                return JSONResponse({"error": "No encontramos tu perfil de cliente"}, status_code=404)
            if usuario.get("activo") is False or str(usuario.get("estado") or "").lower() in {"desactivado", "inactivo", "inactive"}:
                return JSONResponse({"error": "Esta cuenta esta desactivada y no puede realizar compras"}, status_code=403)
            # Algunas instalaciones antiguas de DMI no tenian esta tabla.
            # Se crea de manera compatible antes de registrar la primera compra.
            if not table_exists(conn, "public", "pedidos"):
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS public.pedidos (
                        id BIGSERIAL PRIMARY KEY,
                        nombre TEXT,
                        telefono TEXT,
                        email TEXT,
                        direccion TEXT,
                        ciudad TEXT,
                        departamento TEXT,
                        barrio TEXT,
                        codigo_postal TEXT,
                        referencia_envio TEXT,
                        metodo_pago TEXT,
                        total NUMERIC(14,2) NOT NULL DEFAULT 0,
                        productos JSONB NOT NULL DEFAULT '[]'::jsonb,
                        usuarios_idusuarios INTEGER,
                        activo BOOLEAN NOT NULL DEFAULT TRUE,
                        estado VARCHAR(30) NOT NULL DEFAULT 'pendiente',
                        codigo_pedido VARCHAR(50),
                        tipo_pago VARCHAR(40) NOT NULL DEFAULT 'contra_entrega',
                        novedad TEXT,
                        repartidor_nombre TEXT,
                        repartidor_telefono TEXT,
                        orden_envio VARCHAR(60),
                        token_repartidor VARCHAR(80),
                        ruta_google_maps TEXT,
                        latitud_repartidor NUMERIC(10,7),
                        longitud_repartidor NUMERIC(10,7),
                        ubicacion_actualizada_en TIMESTAMPTZ,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))

            # La relacion permite que compras y productos aparezcan en la ficha
            # administrativa y se inactiven junto con el cliente si es necesario.
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS usuarios_idusuarios integer"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS activo boolean DEFAULT TRUE"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS estado varchar DEFAULT 'pendiente'"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS codigo_pedido varchar(50)"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS tipo_pago varchar(40) DEFAULT 'contra_entrega'"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS novedad text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS departamento text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS barrio text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS codigo_postal text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS referencia_envio text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS repartidor_nombre text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS repartidor_telefono text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS orden_envio varchar(60)"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS token_repartidor varchar(80)"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS ruta_google_maps text"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS latitud_repartidor numeric(10,7)"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS longitud_repartidor numeric(10,7)"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS ubicacion_actualizada_en timestamptz"))
            columnas = table_columns(conn, "public", "pedidos")
            tipo_pago = str(datos.get("tipoPago") or datos.get("tipo_pago") or "contra_entrega").strip().lower()
            if tipo_pago not in {"contra_entrega", "transferencia", "wompi"}:
                return JSONResponse({"error": "Selecciona una forma de pago valida"}, status_code=400)
            estado_pedido = {
                "contra_entrega": "pedido_aceptado",
                "transferencia": "pendiente_transferencia",
                "wompi": "pendiente_pago_wompi",
            }[tipo_pago]
            codigo_pedido = f"PED-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 1000000:06d}"
            valores = {
                "nombre": datos.get("nombre"), "telefono": datos.get("telefono"),
                "email": usuario.get("email") or datos.get("email"), "direccion": datos.get("direccion"),
                "ciudad": datos.get("ciudad"), "departamento": datos.get("departamento"), "barrio": datos.get("barrio"),
                "codigo_postal": datos.get("codigoPostal"), "referencia_envio": datos.get("referenciaEnvio"),
                "metodo_pago": datos.get("metodoPago") or datos.get("metodo_pago"),
                "total": total_calculado, "productos": json.dumps(productos),
                "usuarios_idusuarios": usuario.get("idusuarios"), "activo": True, "estado": estado_pedido,
                "codigo_pedido": codigo_pedido, "tipo_pago": tipo_pago,
                "novedad": "Pedido recibido. Estamos validando la disponibilidad de los productos.",
            }
            campos = [campo for campo in valores if campo in columnas]
            if not campos:
                return JSONResponse({"error": "La tabla de pedidos no tiene campos compatibles"}, status_code=500)
            id_column = "id" if "id" in columnas else ("idpedido" if "idpedido" in columnas else None)
            returning = f" RETURNING {id_column}" if id_column else ""
            resultado = conn.execute(
                text(f"INSERT INTO public.pedidos ({', '.join(campos)}) VALUES ({', '.join(':' + campo for campo in campos)}){returning}"),
                {campo: valores[campo] for campo in campos},
            )
            pedido_id = resultado.scalar() if id_column else None
            conn.commit()
        return JSONResponse({
            "ok": True,
            "pedido_id": pedido_id,
            "codigo_pedido": codigo_pedido,
            "total": total_calculado,
            "estado": estado_pedido,
            # Enlace temporal hasta terminar el Checkout dinamico por pedido.
            "checkout_url": WOMPI_PAYMENT_LINK if tipo_pago == "wompi" else None,
        })
    except (TypeError, ValueError):
        return JSONResponse({"error": "Revisa las cantidades y precios del carrito"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/mi-garage/cotizaciones/{cotizacion_id}/respuesta")
async def responder_cotizacion_cliente(cotizacion_id: int, request: Request, access_token: str = Cookie(None)):
    usuario_actual = obtener_usuario(access_token, request)
    if not usuario_actual:
        return JSONResponse({"error": "Debes iniciar sesion"}, status_code=401)
    try:
        body = await request.json()
        respuesta = str(body.get("respuesta") or "").strip().lower()
        if respuesta not in {"aceptada", "rechazada"}:
            return JSONResponse({"error": "Respuesta no valida"}, status_code=400)
        with engine.connect() as conn:
            usuario = conn.execute(
                text("SELECT idusuarios FROM dmi.usuarios WHERE id::text = :auth_id"),
                {"auth_id": usuario_actual["id"]},
            ).mappings().fetchone()
            if not usuario:
                return JSONResponse({"error": "Usuario no encontrado"}, status_code=404)
            cotizacion = conn.execute(
                text("SELECT * FROM dmi.cotizaciones WHERE idcotizacion = :id AND cliente_id = :cliente_id"),
                {"id": cotizacion_id, "cliente_id": usuario["idusuarios"]},
            ).mappings().fetchone()
            if not cotizacion:
                return JSONResponse({"error": "Cotizacion no encontrada"}, status_code=404)
            if cotizacion.get("estado") != "pendiente":
                return JSONResponse({"error": "Esta cotizacion ya fue respondida"}, status_code=409)
            estado_cotizacion = "aprobada" if respuesta == "aceptada" else "rechazada"
            update_dynamic(conn, "cotizaciones", "idcotizacion", cotizacion_id, {
                "estado": estado_cotizacion, "respuesta_cliente": respuesta, "respondido_en": datetime.now(),
            })
            nuevo_estado = "aprobada" if respuesta == "aceptada" else "cancelada"
            update_dynamic(conn, "orden_trabajo", "idorden", cotizacion["orden_id"], {"estado": nuevo_estado})
            registrar_historial_orden(
                conn, cotizacion["orden_id"], "cotizacion_" + respuesta,
                "Cliente " + ("acepto" if respuesta == "aceptada" else "rechazo") + f" la cotizacion {cotizacion.get('codigo_cotizacion')}",
                float(cotizacion.get("total") or 0),
            )
            conn.commit()
        return JSONResponse({"ok": True, "estado": respuesta})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/mi-garage/facturas/{factura_id}/pago")
async def preparar_pago_factura_cliente(factura_id: int, request: Request, access_token: str = Cookie(None)):
    """Valida una factura del cliente y prepara los datos que usara Wompi.

    No cambia saldo ni estado: esos valores solo se actualizaran desde el
    webhook verificado de Wompi cuando el pago sea realmente aprobado.
    """
    usuario_actual = obtener_usuario(access_token, request)
    if not usuario_actual:
        return JSONResponse({"error": "Debes iniciar sesion para pagar una factura"}, status_code=401)

    try:
        body = await request.json()
        metodo_pago = str(body.get("metodo_pago") or "Wompi").strip()[:60]
        with engine.connect() as conn:
            usuario = conn.execute(
                text("SELECT idusuarios FROM dmi.usuarios WHERE id::text = :auth_id"),
                {"auth_id": usuario_actual["id"]},
            ).mappings().fetchone()
            if not usuario:
                return JSONResponse({"error": "Usuario no encontrado"}, status_code=404)

            factura = conn.execute(
                text("""
                    SELECT idfactura, codigo_factura, total, saldo, estado
                    FROM dmi.facturas
                    WHERE idfactura = :factura_id AND cliente_id = :cliente_id
                """),
                {"factura_id": factura_id, "cliente_id": usuario["idusuarios"]},
            ).mappings().fetchone()
            if not factura:
                return JSONResponse({"error": "Factura no encontrada"}, status_code=404)

            saldo = float(factura.get("saldo") if factura.get("saldo") is not None else factura.get("total") or 0)
            estado = str(factura.get("estado") or "").lower()
            if estado in {"pagada", "cancelada"} or saldo <= 0:
                return JSONResponse({"error": "Esta factura no tiene un saldo pendiente"}, status_code=409)

        # Esta referencia se utilizara en el Checkout Web dinamico de Wompi.
        # Un link fijo de Wompi genera su propia referencia y no puede asociarse
        # de forma segura a una factura concreta.
        referencia = f"DMI-FACTURA-{factura_id}-{int(datetime.now().timestamp())}"
        return JSONResponse({
            "ok": True,
            "checkout_url": WOMPI_PAYMENT_LINK,
            "payment_intent": {
                "referencia": referencia,
                "monto_en_centavos": int(round(saldo * 100)),
                "moneda": "COP",
                "metodo_seleccionado": metodo_pago,
                "factura": factura.get("codigo_factura"),
            },
            "estado": "pendiente_wompi",
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def wompi_propiedad(data: dict, ruta: str):
    """Obtiene una propiedad anidada que Wompi indique en signature.properties."""
    valor = data
    partes = str(ruta or "").split(".")
    if partes and partes[0] == "data":
        partes = partes[1:]
    for parte in partes:
        if not isinstance(valor, dict):
            return ""
        valor = valor.get(parte)
    return "" if valor is None else str(valor)


@app.post("/api/wompi/webhook")
async def recibir_evento_wompi(request: Request):
    """Confirma pagos de Wompi solo despues de validar su firma criptografica."""
    if not WOMPI_EVENTS_SECRET:
        return JSONResponse({"error": "Falta configurar WOMPI_EVENTS_SECRET"}, status_code=503)

    try:
        evento = await request.json()
        firma = evento.get("signature") or {}
        propiedades = firma.get("properties") or []
        checksum_recibido = request.headers.get("X-Event-Checksum") or firma.get("checksum")
        texto_firma = "".join(wompi_propiedad(evento.get("data") or {}, campo) for campo in propiedades)
        texto_firma += str(evento.get("timestamp") or "") + WOMPI_EVENTS_SECRET
        checksum_esperado = hashlib.sha256(texto_firma.encode("utf-8")).hexdigest()
        if not checksum_recibido or checksum_esperado.lower() != str(checksum_recibido).lower():
            return JSONResponse({"error": "Firma de Wompi invalida"}, status_code=401)

        if evento.get("event") != "transaction.updated":
            return JSONResponse({"ok": True, "ignored": True})

        datos = evento.get("data") or {}
        transaccion = datos.get("transaction") or datos
        if str(transaccion.get("status") or "").upper() != "APPROVED":
            return JSONResponse({"ok": True, "estado": transaccion.get("status")})

        referencia = str(transaccion.get("reference") or "")
        partes = referencia.split("-")
        if len(partes) < 4 or partes[0] != "DMI" or partes[1] != "FACTURA":
            # Los links fijos tienen una referencia propia de Wompi. No se les
            # asigna una factura para impedir acreditar un pago equivocado.
            return JSONResponse({"ok": True, "ignored": True, "reason": "Referencia no asociada a DMI"})

        factura_id = int(partes[2])
        valor_pagado = float(transaccion.get("amount_in_cents") or 0) / 100
        if valor_pagado <= 0:
            return JSONResponse({"error": "Monto de transaccion invalido"}, status_code=400)

        with engine.connect() as conn:
            factura = conn.execute(text("SELECT * FROM dmi.facturas WHERE idfactura = :id"), {"id": factura_id}).mappings().fetchone()
            if not factura:
                return JSONResponse({"error": "Factura no encontrada"}, status_code=404)

            transaccion_id = str(transaccion.get("id") or referencia)
            ya_registrado = conn.execute(text("SELECT 1 FROM dmi.pagos WHERE referencia = :referencia LIMIT 1"), {"referencia": transaccion_id}).fetchone()
            if ya_registrado:
                return JSONResponse({"ok": True, "duplicado": True})

            saldo = float(factura.get("saldo") if factura.get("saldo") is not None else factura.get("total") or 0)
            nuevo_saldo = max(0, saldo - valor_pagado)
            estado_factura = "pagada" if nuevo_saldo == 0 else "parcial"
            metodo = str(transaccion.get("payment_method_type") or "Wompi")
            metodo_row = conn.execute(text("SELECT idmetodopago FROM dmi.metodopago WHERE LOWER(descripcionmpago) = LOWER(:metodo) LIMIT 1"), {"metodo": metodo}).mappings().fetchone()
            pago_data = {
                "codigo_pago": generar_codigo_documento(conn, "pagos", "codigo_pago", "PAG"),
                "factura_id": factura_id,
                "fecha_pago": datetime.now(),
                "valor": valor_pagado,
                "referencia": transaccion_id,
                "estado": "confirmado",
            }
            if metodo_row:
                pago_data["metodopago_id"] = metodo_row["idmetodopago"]
            insert_dynamic_returning(conn, "pagos", pago_data, "idpago")
            update_dynamic(conn, "facturas", "idfactura", factura_id, {"saldo": nuevo_saldo, "estado": estado_factura})
            if estado_factura == "pagada" and factura.get("orden_id"):
                update_dynamic(conn, "orden_trabajo", "idorden", factura["orden_id"], {"estado": "pagada"})
                registrar_historial_orden(conn, factura["orden_id"], "pago_confirmado", f"Pago Wompi aprobado para la factura {factura.get('codigo_factura')}", valor_pagado, factura_id)
            conn.commit()
        return JSONResponse({"ok": True, "factura_id": factura_id, "estado_factura": estado_factura})
    except ValueError:
        return JSONResponse({"error": "Referencia de factura invalida"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/mi-garage")
async def api_mi_garage(request: Request, access_token: str = Cookie(None)):
    usuario_actual = obtener_usuario(access_token, request)
    if not usuario_actual:
        return JSONResponse({"error": "Debes iniciar sesion"}, status_code=401)

    progreso_por_estado = {
        "abierta": 10,
        "diagnostico": 25,
        "cotizada": 40,
        "aprobada": 50,
        "en_reparacion": 70,
        "finalizada": 85,
        "facturada": 90,
        "pagada": 96,
        "entregada": 100,
        "cancelada": 0,
    }

    etiqueta_por_estado = {
        "abierta": "Orden abierta",
        "diagnostico": "En diagnostico",
        "cotizada": "Cotizacion lista",
        "aprobada": "Cotizacion aprobada",
        "en_reparacion": "En reparacion",
        "finalizada": "Trabajo finalizado",
        "facturada": "Facturada",
        "pagada": "Pagada",
        "entregada": "Vehiculo entregado",
        "cancelada": "Cancelada",
    }

    try:
        with engine.connect() as conn:
            usuario = conn.execute(
                text("""
                    SELECT
                        idusuarios,
                        id,
                        nombre,
                        apellidos,
                        documento,
                        tipodedocumento,
                        email,
                        telefono,
                        usuarionombre,
                        fechadenacimiento::text AS fechadenacimiento,
                        COALESCE(rol, 'usuario') AS rol,
                        vehiculos_idvehiculo
                    FROM dmi.usuarios
                    WHERE id::text = :auth_id
                """),
                {"auth_id": usuario_actual["id"]},
            ).mappings().fetchone()

            if not usuario:
                return JSONResponse({"error": "Usuario no encontrado"}, status_code=404)

            usuario = json_row(usuario)
            usuario_id = usuario.get("idusuarios")
            vehiculo_legacy_id = usuario.get("vehiculos_idvehiculo")

            vehiculos = query_rows(
                conn,
                """
                SELECT
                    v.idvehiculo,
                    v.codigovehiculo,
                    v.descripcionvehiculo,
                    v.motor,
                    v.cantidad_asientos,
                    v.placa,
                    v.capacidad,
                    v.marca,
                    v.modelo,
                    v.vin,
                    v.kilometraje_actual,
                    v.combustible,
                    v.estado,
                    tv.vehiculo AS tipo_vehiculo
                FROM dmi.vehiculos v
                LEFT JOIN dmi.tipovehiculos tv ON tv.idtipovehiculos = v.tipovehiculos_idtipovehiculos
                WHERE v.cliente_id = :usuario_id OR v.idvehiculo = :vehiculo_legacy_id
                ORDER BY v.idvehiculo DESC
                """,
                {"usuario_id": usuario_id, "vehiculo_legacy_id": vehiculo_legacy_id},
            )

            citas = query_rows(
                conn,
                """
                SELECT
                    c.idcita,
                    c.fecha,
                    c.hora,
                    c.motivo,
                    c.estado,
                    c.notas,
                    v.idvehiculo,
                    v.placa,
                    COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo
                FROM dmi.citas c
                LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                WHERE v.cliente_id = :usuario_id OR c.vehiculos_idvehiculo = :vehiculo_legacy_id
                ORDER BY c.fecha DESC, c.hora DESC
                """,
                {"usuario_id": usuario_id, "vehiculo_legacy_id": vehiculo_legacy_id},
            )

            ordenes = query_rows(
                conn,
                """
                SELECT
                    ot.idorden,
                    ot.codigo_orden,
                    ot.cita_id,
                    ot.cliente_id,
                    ot.vehiculo_id,
                    ot.estado,
                    ot.prioridad,
                    ot.fecha_apertura,
                    ot.fecha_inicio,
                    ot.fecha_finalizacion,
                    ot.fecha_entrega,
                    ot.motivo_ingreso,
                    ot.observaciones_cliente,
                    ot.total_servicios,
                    ot.total_repuestos,
                    ot.total_orden,
                    v.placa,
                    v.marca,
                    v.modelo,
                    v.codigovehiculo,
                    v.kilometraje_actual,
                    v.combustible
                FROM dmi.orden_trabajo ot
                LEFT JOIN dmi.vehiculos v ON v.idvehiculo = ot.vehiculo_id
                WHERE ot.cliente_id = :usuario_id
                ORDER BY ot.fecha_apertura DESC, ot.idorden DESC
                """,
                {"usuario_id": usuario_id},
            )

            for orden in ordenes:
                estado = str(orden.get("estado") or "abierta")
                orden["progreso"] = progreso_por_estado.get(estado, 10)
                orden["estado_label"] = etiqueta_por_estado.get(estado, estado)

            diagnosticos_orden = query_rows(
                conn,
                """
                SELECT
                    d.iddiagnostico,
                    d.orden_id,
                    d.diagnostico_tecnico,
                    d.recomendacion,
                    d.fecha_diagnostico,
                    d.estado
                FROM dmi.diagnosticos d
                JOIN dmi.orden_trabajo ot ON ot.idorden = d.orden_id
                WHERE ot.cliente_id = :usuario_id
                ORDER BY d.fecha_diagnostico DESC, d.iddiagnostico DESC
                """,
                {"usuario_id": usuario_id},
            )

            servicios_orden = query_rows(
                conn,
                """
                SELECT
                    ds.iddetalle_servicio,
                    ds.orden_id,
                    ds.servicio_id,
                    ds.descripcion,
                    ds.cantidad,
                    ds.valor_unitario,
                    ds.subtotal,
                    ds.estado,
                    ds.fecha_inicio,
                    ds.fecha_fin,
                    s.codigoservicio,
                    s.descripcionservicio
                FROM dmi.detalle_servicios ds
                LEFT JOIN dmi.servicios s ON s.idservicios = ds.servicio_id
                JOIN dmi.orden_trabajo ot ON ot.idorden = ds.orden_id
                WHERE ot.cliente_id = :usuario_id
                ORDER BY ds.iddetalle_servicio DESC
                """,
                {"usuario_id": usuario_id},
            )

            repuestos_orden = query_rows(
                conn,
                """
                SELECT
                    dr.iddetalle_repuesto,
                    dr.orden_id,
                    dr.producto_id,
                    dr.inventario_id,
                    dr.descripcion,
                    dr.cantidad,
                    dr.valor_unitario,
                    dr.subtotal,
                    dr.consumido,
                    dr.fecha_consumo,
                    p.codigo AS codigoproductos,
                    p.nombre AS descripcionproductos
                FROM dmi.detalle_repuestos dr
                LEFT JOIN dmi.inventario_catalogo p ON p.id = COALESCE(dr.producto_id, dr.inventario_id)
                JOIN dmi.orden_trabajo ot ON ot.idorden = dr.orden_id
                WHERE ot.cliente_id = :usuario_id
                ORDER BY dr.iddetalle_repuesto DESC
                """,
                {"usuario_id": usuario_id},
            )

            facturas = query_rows(
                conn,
                """
                SELECT
                    f.idfactura,
                    f.codigo_factura,
                    f.orden_id,
                    f.fecha_factura,
                    f.subtotal,
                    f.impuestos,
                    f.descuento,
                    f.total,
                    f.saldo,
                    f.estado,
                    ot.codigo_orden
                FROM dmi.facturas f
                LEFT JOIN dmi.orden_trabajo ot ON ot.idorden = f.orden_id
                WHERE f.cliente_id = :usuario_id
                ORDER BY f.fecha_factura DESC, f.idfactura DESC
                """,
                {"usuario_id": usuario_id},
            )

            columnas_cotizacion = table_columns(conn, "dmi", "cotizaciones")
            fecha_cotizacion_col = next(
                (col for col in ("fecha_cotizacion", "fecha", "created_at", "creado_en") if col in columnas_cotizacion),
                None,
            )
            fecha_cotizacion_select = f"c.{fecha_cotizacion_col} AS fecha_cotizacion" if fecha_cotizacion_col else "NULL::timestamp AS fecha_cotizacion"
            orden_cotizaciones = f"c.{fecha_cotizacion_col} DESC, c.idcotizacion DESC" if fecha_cotizacion_col else "c.idcotizacion DESC"
            cotizaciones = query_rows(
                conn,
                f"""
                SELECT c.idcotizacion, c.codigo_cotizacion, c.orden_id, c.fecha_cotizacion,
                       c.enviado_en, c.respondido_en, c.respuesta_cliente,
                       c.subtotal, c.impuestos, c.descuento, c.total, c.estado, ot.codigo_orden
                FROM dmi.cotizaciones c
                JOIN dmi.orden_trabajo ot ON ot.idorden = c.orden_id
                WHERE c.cliente_id = :usuario_id AND c.enviado_en IS NOT NULL
                ORDER BY {orden_cotizaciones}
                """.replace("c.fecha_cotizacion", fecha_cotizacion_select, 1),
                {"usuario_id": usuario_id},
            )
            cotizacion_detalles = query_rows(
                conn,
                """
                SELECT cd.*
                FROM dmi.cotizacion_detalles cd
                JOIN dmi.cotizaciones c ON c.idcotizacion = cd.cotizacion_id
                WHERE c.cliente_id = :usuario_id AND c.enviado_en IS NOT NULL
                ORDER BY cd.iddetalle_cotizacion
                """,
                {"usuario_id": usuario_id},
            )

            pagos_facturas = query_rows(
                conn,
                """
                SELECT
                    p.idpago,
                    p.factura_id,
                    p.codigo_pago,
                    p.fecha_pago,
                    p.valor,
                    p.referencia,
                    p.estado,
                    mp.descripcionmpago AS metodo,
                    f.codigo_factura
                FROM dmi.pagos p
                LEFT JOIN dmi.facturas f ON f.idfactura = p.factura_id
                LEFT JOIN dmi.metodopago mp ON mp.idmetodopago = p.metodopago_id
                WHERE f.cliente_id = :usuario_id
                ORDER BY p.fecha_pago DESC, p.idpago DESC
                """,
                {"usuario_id": usuario_id},
            )

            historial = query_rows(
                conn,
                """
                SELECT
                    hv.idhistorial,
                    hv.vehiculo_id,
                    hv.orden_id,
                    hv.factura_id,
                    hv.fecha_evento,
                    hv.tipo_evento,
                    hv.descripcion,
                    hv.kilometraje,
                    hv.costo_total,
                    v.placa,
                    v.marca,
                    v.modelo
                FROM dmi.historial_vehiculo hv
                LEFT JOIN dmi.vehiculos v ON v.idvehiculo = hv.vehiculo_id
                WHERE hv.cliente_id = :usuario_id
                ORDER BY hv.fecha_evento DESC, hv.idhistorial DESC
                """,
                {"usuario_id": usuario_id},
            )

            pedidos = []
            productos = []
            notas = []

            if table_exists(conn, "public", "pedidos"):
                checkout_columns = table_columns(conn, "public", "pedidos")
                if "email" in checkout_columns and usuario.get("email"):
                    order_column = "id" if "id" in checkout_columns else "created_at" if "created_at" in checkout_columns else None
                    order_sql = f"ORDER BY {order_column} DESC" if order_column else ""
                    cart_field = next((field for field in ("productos", "items", "carrito", "cart") if field in checkout_columns), None)
                    pedidos = query_rows(
                        conn,
                        f"""
                        SELECT *
                        FROM public.pedidos
                        WHERE LOWER(email) = LOWER(:email)
                        {order_sql}
                        """,
                        {"email": usuario.get("email")},
                    )
                    if cart_field:
                        for pedido in pedidos:
                            for item in normalize_cart_items(pedido.get(cart_field)):
                                if not isinstance(item, dict):
                                    item = {"nombre": item}
                                productos.append({
                                    "codigoproductos": item.get("codigo") or item.get("codigoproductos") or item.get("id"),
                                    "descripcionproductos": item.get("nombre") or item.get("descripcion") or item.get("descripcionproductos"),
                                    "valor_precio": item.get("precioVenta") or item.get("precio") or item.get("valor"),
                                    "cantidad": item.get("quantity") or item.get("cantidad") or 1,
                                    "pedido_idpedido": pedido.get("id") or pedido.get("codigopedido"),
                                })

            pagos = [
                {
                    "id": pedido.get("idpedido") or pedido.get("id"),
                    "codigo": pedido.get("codigopedido") or pedido.get("codigo") or pedido.get("id"),
                    "metodo": pedido.get("metodo_pago") or pedido.get("metodoPago") or pedido.get("metodopago_idmetodopago"),
                    "estado": pedido.get("estado") or "registrado",
                    "total": pedido.get("total"),
                    "fecha": pedido.get("fecha") or pedido.get("created_at"),
                }
                for pedido in pedidos
            ]

            if not productos:
                notas.append("Todavia no hay productos de compra guardados para esta cuenta.")
            if not ordenes:
                notas.append("Todavia no hay ordenes de trabajo para esta cuenta.")

            return JSONResponse({
                "usuario": usuario,
                "vehiculos": vehiculos,
                "citas": citas,
                "ordenes": ordenes,
                "diagnosticos_orden": diagnosticos_orden,
                "servicios_orden": servicios_orden,
                "repuestos_orden": repuestos_orden,
                "cotizaciones": cotizaciones,
                "cotizacion_detalles": cotizacion_detalles,
                "facturas": facturas,
                "pagos_facturas": pagos_facturas,
                "historial": historial,
                "pedidos": pedidos,
                "pagos": pagos,
                "productos": productos,
                "notas": notas,
                "resumen": {
                    "vehiculos": len(vehiculos),
                    "citas_activas": len([c for c in citas if str(c.get("estado") or "").lower() not in ("cancelada", "cancelado", "completada")]),
                    "ordenes_activas": len([o for o in ordenes if str(o.get("estado") or "").lower() not in ("entregada", "cancelada")]),
                    "facturas_pendientes": len([f for f in facturas if str(f.get("estado") or "").lower() in ("pendiente", "parcial")]),
                },
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/config/{entity}/registro/{record_id}")
async def config_obtener_registro(entity: str, record_id: int, access_token: str = Cookie(None)):
    if not config_user_or_redirect(access_token):
        return JSONResponse({"error": "No tienes permiso"}, status_code=403)

    cfg = CONFIG_TABLES.get(entity)
    if not cfg:
        return JSONResponse({"error": "Seccion no valida"}, status_code=404)

    try:
        with engine.connect() as conn:
            pk = resolve_table_pk(conn, cfg["table"], cfg.get("pk")) or cfg.get("pk")
            select_sql = cfg.get("select") or f"SELECT * FROM dmi.{cfg['table']} WHERE {pk} = :id"
            row = conn.execute(
                text(select_sql),
                {"id": record_id},
            ).mappings().fetchone()
        if not row:
            return JSONResponse({"error": "Registro no encontrado"}, status_code=404)
        return JSONResponse({key: json_safe(value) for key, value in dict(row).items()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/config/{entity}/nuevo")
async def config_crear_generico(entity: str, request: Request, access_token: str = Cookie(None)):
    if not config_user_or_redirect(access_token):
        return redirigir_sin_permiso("/configuracion")

    cfg = CONFIG_TABLES.get(entity)
    if not cfg:
        return config_redirect(entity, "Seccion no valida", False)

    try:
        form = await request.form()
        with engine.connect() as conn:
            real_columns = table_columns(conn, "dmi", cfg["table"])
        fields = [field for field in cfg["fields"] if field in form and field in real_columns]
        values = {field: normalize_config_value(form.get(field)) for field in fields}
        if entity == "empleados":
            if "activo" in real_columns and "activo" not in values:
                values["activo"] = True
                fields.append("activo")
            if "estado" in real_columns and "estado" not in values:
                values["estado"] = "activo"
                fields.append("estado")

        if not fields:
            return config_redirect(entity, "No llegaron datos para guardar", False)
        if entity in {"oficinas", "servicios", "tiporeparacion", "productos"}:
            with engine.connect() as conn:
                def exists(table, pk, value):
                    if not value:
                        return True
                    return conn.execute(
                        text(f"SELECT 1 FROM dmi.{table} WHERE {pk} = :id"),
                        {"id": value},
                    ).scalar() is not None

                if entity == "oficinas":
                    if not exists("ciudades", "idciudades", values.get("ciudades_idciudades")):
                        return config_redirect(entity, "Selecciona una ciudad valida registrada en Supabase", False)
                    if not values.get("inventario_idinventario"):
                        return config_redirect(entity, "Selecciona un inventario para la oficina", False)
                    if not exists("inventario", "idinventario", values.get("inventario_idinventario")):
                        return config_redirect(entity, "Selecciona un inventario valido registrado en Supabase", False)

                if entity == "servicios":
                    if not exists("pedido", "idpedido", values.get("pedido_idpedido")):
                        return config_redirect(entity, "Selecciona un pedido valido registrado en Supabase", False)
                    if not exists("serviciosprecio", "idserviciosprecio", values.get("serviciosprecio_idserviciosprecio")):
                        return config_redirect(entity, "Selecciona un precio de servicio valido o deja el campo en blanco", False)

                if entity == "tiporeparacion":
                    if not exists("servicios", "idservicios", values.get("servicios_idservicios")):
                        return config_redirect(entity, "Selecciona un servicio valido registrado en Supabase", False)
                    if not exists("pedido", "idpedido", values.get("pedido_idpedido")):
                        return config_redirect(entity, "Selecciona un pedido valido registrado en Supabase", False)

                if entity == "productos":
                    if not exists("productoprecio", "idproductoprecio", values.get("productoprecio_idproductoprecio")):
                        return config_redirect(entity, "Selecciona un precio de producto valido registrado en Supabase", False)
                    if not exists("pedido", "idpedido", values.get("pedido_idpedido")):
                        return config_redirect(entity, "Selecciona un pedido valido registrado en Supabase", False)

        columns = ", ".join(fields)
        placeholders = ", ".join(f":{field}" for field in fields)
        with engine.connect() as conn:
            conn.execute(
                text(f"INSERT INTO dmi.{cfg['table']} ({columns}) VALUES ({placeholders})"),
                values,
            )
            conn.commit()
        return config_redirect(entity, "Registro guardado correctamente")
    except Exception as e:
        return config_redirect(entity, str(e), False)


@app.post("/config/{entity}/editar/{record_id}")
async def config_editar_generico(entity: str, record_id: int, request: Request, access_token: str = Cookie(None)):
    if not config_user_or_redirect(access_token):
        return redirigir_sin_permiso("/configuracion")

    cfg = CONFIG_TABLES.get(entity)
    if not cfg:
        return config_redirect(entity, "Seccion no valida", False)

    try:
        form = await request.form()
        with engine.connect() as conn:
            real_columns = table_columns(conn, "dmi", cfg["table"])
        fields = [field for field in cfg["fields"] if field in form and field in real_columns]
        values = {field: normalize_config_value(form.get(field)) for field in fields}

        if not fields:
            return config_redirect(entity, "No llegaron datos para editar", False)

        if entity in {"oficinas", "servicios", "tiporeparacion", "productos"}:
            with engine.connect() as conn:
                def exists(table, pk, value):
                    if not value:
                        return True
                    return conn.execute(
                        text(f"SELECT 1 FROM dmi.{table} WHERE {pk} = :id"),
                        {"id": value},
                    ).scalar() is not None

                if entity == "oficinas":
                    if not exists("ciudades", "idciudades", values.get("ciudades_idciudades")):
                        return config_redirect(entity, "Selecciona una ciudad valida registrada en Supabase", False)
                    if not values.get("inventario_idinventario"):
                        return config_redirect(entity, "Selecciona un inventario para la oficina", False)
                    if not exists("inventario", "idinventario", values.get("inventario_idinventario")):
                        return config_redirect(entity, "Selecciona un inventario valido registrado en Supabase", False)

                if entity == "servicios":
                    if not exists("pedido", "idpedido", values.get("pedido_idpedido")):
                        return config_redirect(entity, "Selecciona un pedido valido registrado en Supabase", False)
                    if not exists("serviciosprecio", "idserviciosprecio", values.get("serviciosprecio_idserviciosprecio")):
                        return config_redirect(entity, "Selecciona un precio de servicio valido o deja el campo en blanco", False)

                if entity == "tiporeparacion":
                    if not exists("servicios", "idservicios", values.get("servicios_idservicios")):
                        return config_redirect(entity, "Selecciona un servicio valido registrado en Supabase", False)
                    if not exists("pedido", "idpedido", values.get("pedido_idpedido")):
                        return config_redirect(entity, "Selecciona un pedido valido registrado en Supabase", False)

                if entity == "productos":
                    if not exists("productoprecio", "idproductoprecio", values.get("productoprecio_idproductoprecio")):
                        return config_redirect(entity, "Selecciona un precio de producto valido registrado en Supabase", False)
                    if not exists("pedido", "idpedido", values.get("pedido_idpedido")):
                        return config_redirect(entity, "Selecciona un pedido valido registrado en Supabase", False)

        assignments = ", ".join(f"{field} = :{field}" for field in fields)
        values["id"] = record_id
        with engine.connect() as conn:
            pk = resolve_table_pk(conn, cfg["table"], cfg.get("pk")) or cfg.get("pk")
            conn.execute(
                text(f"UPDATE dmi.{cfg['table']} SET {assignments} WHERE {pk} = :id"),
                values,
            )
            conn.commit()
        return config_redirect(entity, "Registro actualizado correctamente")
    except Exception as e:
        return config_redirect(entity, str(e), False)


@app.post("/config/{entity}/eliminar/{record_id}")
async def config_eliminar_generico(entity: str, record_id: int, access_token: str = Cookie(None)):
    if not config_user_or_redirect(access_token):
        return redirigir_sin_permiso("/configuracion")

    cfg = CONFIG_TABLES.get(entity)
    if not cfg:
        return config_redirect(entity, "Seccion no valida", False)

    try:
        with engine.connect() as conn:
            # Un usuario no debe conservar datos operativos disponibles despues de
            # desactivarse. La informacion se mantiene para auditoria, pero sus
            # vehiculos, citas, ordenes y compras relacionadas quedan inactivas.
            if entity == "usuarios":
                usuario = conn.execute(
                    text("SELECT idusuarios, id, email, vehiculos_idvehiculo FROM dmi.usuarios WHERE idusuarios = :id"),
                    {"id": record_id},
                ).mappings().fetchone()
                if not usuario:
                    return config_redirect(entity, "Usuario no encontrado", False)

                usuario = dict(usuario)

                def desactivar_relacion(schema, table, where, params):
                    if not where or not table_exists(conn, schema, table):
                        return 0
                    cols = table_columns(conn, schema, table)
                    # El estado de una cita/orden suele tener una restriccion
                    # (pendiente, confirmada, cancelada, etc.). Por eso no se
                    # reemplaza por "desactivado": se conserva su estado real
                    # y se crea/usa una marca independiente de actividad.
                    if "activo" not in cols:
                        conn.execute(text(
                            f"ALTER TABLE {schema}.{table} ADD COLUMN IF NOT EXISTS activo boolean DEFAULT TRUE"
                        ))
                    result = conn.execute(
                        text(f"UPDATE {schema}.{table} SET activo = FALSE WHERE {where}"),
                        params,
                    )
                    return result.rowcount or 0

                # Primero se localizan todos los vehiculos y citas, incluso si ya
                # estaban inactivos, para conservar la relacion historica completa.
                vehiculo_ids = []
                if table_exists(conn, "dmi", "vehiculos"):
                    vehiculo_cols = table_columns(conn, "dmi", "vehiculos")
                    vehiculo_filtros = []
                    vehiculo_params = {"usuario_id": record_id, "auth_id": usuario.get("id")}
                    if "cliente_id" in vehiculo_cols:
                        vehiculo_filtros.append("cliente_id = :usuario_id")
                    if "usuarios_idusuarios" in vehiculo_cols:
                        vehiculo_filtros.append("usuarios_idusuarios = :usuario_id")
                    if usuario.get("vehiculos_idvehiculo"):
                        vehiculo_filtros.append("idvehiculo = :vehiculo_principal")
                        vehiculo_params["vehiculo_principal"] = usuario["vehiculos_idvehiculo"]
                    if vehiculo_filtros:
                        vehiculo_ids = [row[0] for row in conn.execute(
                            text(f"SELECT idvehiculo FROM dmi.vehiculos WHERE {' OR '.join(vehiculo_filtros)}"),
                            vehiculo_params,
                        ).fetchall()]
                        desactivar_relacion("dmi", "vehiculos", "idvehiculo = ANY(:vehiculo_ids)", {"vehiculo_ids": vehiculo_ids}) if vehiculo_ids else None

                cita_ids = []
                if vehiculo_ids and table_exists(conn, "dmi", "citas"):
                    cita_cols = table_columns(conn, "dmi", "citas")
                    if "vehiculos_idvehiculo" in cita_cols:
                        cita_ids = [row[0] for row in conn.execute(
                            text("SELECT idcita FROM dmi.citas WHERE vehiculos_idvehiculo = ANY(:vehiculo_ids)"),
                            {"vehiculo_ids": vehiculo_ids},
                        ).fetchall()]
                        desactivar_relacion("dmi", "citas", "vehiculos_idvehiculo = ANY(:vehiculo_ids)", {"vehiculo_ids": vehiculo_ids})

                # Ordenes, cotizaciones, facturas y pedidos se inactivan si su
                # tabla tiene un campo de estado. No se borran: siguen visibles
                # en la ficha administrativa como historial del cliente.
                objetivos = [
                    ("dmi", "orden_trabajo", [
                        ("vehiculos_idvehiculo", "vehiculo_ids", vehiculo_ids),
                        ("citas_idcita", "cita_ids", cita_ids),
                        ("cita_id", "cita_ids", cita_ids),
                    ]),
                    ("dmi", "cotizaciones", [("cliente_id", "usuario_id", record_id)]),
                    ("dmi", "facturas", [("cliente_id", "usuario_id", record_id)]),
                    ("dmi", "pedido", [
                        ("usuarios_idusuarios", "usuario_id", record_id),
                        ("email", "email", usuario.get("email")),
                    ]),
                    ("public", "pedidos", [
                        ("usuarios_idusuarios", "usuario_id", record_id),
                        ("email", "email", usuario.get("email")),
                    ]),
                ]
                for schema, table, relaciones in objetivos:
                    if not table_exists(conn, schema, table):
                        continue
                    columnas_relacion = table_columns(conn, schema, table)
                    filtros, params = [], {}
                    for columna, parametro, valor in relaciones:
                        if columna not in columnas_relacion or valor in (None, [], ""):
                            continue
                        if isinstance(valor, list):
                            filtros.append(f"{columna} = ANY(:{parametro})")
                        elif columna == "email":
                            filtros.append(f"LOWER({columna}) = LOWER(:{parametro})")
                        else:
                            filtros.append(f"{columna} = :{parametro}")
                        params[parametro] = valor
                    if filtros:
                        desactivar_relacion(schema, table, " OR ".join(filtros), params)

            columnas = table_columns(conn, "dmi", cfg["table"])

            if "activo" in columnas:
                conn.execute(
                    text(f"UPDATE dmi.{cfg['table']} SET activo = FALSE WHERE {resolve_table_pk(conn, cfg['table'], cfg.get('pk')) or cfg['pk']} = :id"),
                    {"id": record_id},
                )
            else:
                if "estado" not in columnas:
                    conn.execute(text(f"ALTER TABLE dmi.{cfg['table']} ADD COLUMN estado varchar DEFAULT 'activo'"))
                conn.execute(
                    text(f"UPDATE dmi.{cfg['table']} SET estado = 'desactivado' WHERE {resolve_table_pk(conn, cfg['table'], cfg.get('pk')) or cfg['pk']} = :id"),
                    {"id": record_id},
                )

            conn.commit()
        return config_redirect(entity, "Registro desactivado correctamente")
    except Exception as e:
        return config_redirect(entity, str(e), False)


@app.post("/config/usuarios/activar/{usuario_id}")
async def config_activar_usuario(usuario_id: int, access_token: str = Cookie(None)):
    if not config_user_or_redirect(access_token):
        return redirigir_sin_permiso("/configuracion")

    try:
        with engine.connect() as conn:
            columnas = table_columns(conn, "dmi", "usuarios")
            if "activo" in columnas:
                conn.execute(text("UPDATE dmi.usuarios SET activo = TRUE WHERE idusuarios = :id"), {"id": usuario_id})
            else:
                if "estado" not in columnas:
                    conn.execute(text("ALTER TABLE dmi.usuarios ADD COLUMN estado varchar DEFAULT 'activo'"))
                conn.execute(text("UPDATE dmi.usuarios SET estado = 'activo' WHERE idusuarios = :id"), {"id": usuario_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Usuario activado correctamente#usuarios-desactivados", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={quote(str(e))}#usuarios-desactivados", status_code=302)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
