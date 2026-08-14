from fastapi import FastAPI, Form, Request, Cookie, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from urllib.parse import quote
from urllib.parse import urlparse
from uuid import UUID
from zoneinfo import ZoneInfo
import os
import jwt
import json
from sqlalchemy import text
from datetime import datetime

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.pjgldixdkavafmxowujt:camiloide1606@aws-1-us-east-1.pooler.supabase.com:5432/postgres")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pjgldixdkavafmxowujt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "yJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBqZ2xkaXhka2F2YWZteG93dWp0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE2MDMxOTAsImV4cCI6MjA4NzE3OTE5MH0.VsdOpz44v2pVYb94ESnw-nmLe7OmaXsm_mMfU-FEKAA")
ADMIN_SECRET  = os.getenv("ADMIN_SECRET", "lolcito")  

# Forzamos a SQLAlchemy a buscar directamente en el esquema dmi
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-csearch_path=dmi,public"}
)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        # Se mantiene el decodificador sin verificaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n automÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡tica
        payload = jwt.decode(access_token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            return None
        user_res = (
            supabase.schema("dmi")
            .table("usuarios")
            .select("idusuarios, usuarionombre, rol, email")   
            .eq("id", user_id)
            .execute()
        )
        if user_res.data:
            usuario = {
                "id": user_id,
                "idusuarios": user_res.data[0].get("idusuarios"),
                "nombre": user_res.data[0].get("usuarionombre"),
                "email": user_res.data[0].get("email"),
                "rol": user_res.data[0].get("rol"),
            }
            rol_empleado = obtener_rol_empleado_por_email(usuario.get("email"))
            if rol_empleado and usuario.get("rol") != "admin":
                usuario["rol"] = rol_empleado
            return usuario

        email_token = payload.get("email")
        rol_empleado = obtener_rol_empleado_por_email(email_token)
        if rol_empleado:
            return {
                "id": user_id,
                "idusuarios": None,
                "nombre": email_token.split("@")[0] if email_token else "Mecanico",
                "email": email_token,
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
        WHERE c.fecha = :hoy
          AND lower(COALESCE(c.estado, 'pendiente')) NOT IN ('cancelada', 'cancelado', 'completada')
          {filtro_empleado}
        ORDER BY c.hora ASC, c.idcita ASC
    """), params).mappings().fetchall()]


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
# ==================== PÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂGINA PRINCIPAL ====================
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
    mes_seleccionado = request.query_params.get("mes")

    try:
        with engine.connect() as conn:
            if es_admin(usuario):
                meses_ordenes = obtener_meses_ordenes(conn)
                mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
                ordenes = obtener_ordenes_panel(conn, mes_seleccionado)
                citas_hoy_ordenes = obtener_citas_programadas_hoy(conn)
            else:
                empleado = obtener_empleado_actual(conn, usuario)
                if empleado:
                    meses_ordenes = obtener_meses_ordenes(conn, empleado.get("idempleado"))
                    mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
                    ordenes = obtener_ordenes_mecanico(conn, empleado.get("idempleado"), mes_seleccionado)
                    notificaciones = [orden for orden in obtener_ordenes_mecanico(conn, empleado.get("idempleado")) if orden.get("estado") == "aprobada"]
                    citas_hoy_ordenes = obtener_citas_programadas_hoy(conn, empleado.get("idempleado"))
                else:
                    error_msg = "Tu usuario mecanico no esta enlazado a un empleado por correo."
    except Exception as e:
        error_msg = f"No se pudieron cargar las ordenes del mecanico: {e}"

    return templates.TemplateResponse(
        request=request,
        name="ordenes.html",
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
    mes_seleccionado = request.query_params.get("mes")

    try:
        with engine.connect() as conn:
            meses_ordenes = obtener_meses_ordenes(conn)
            mes_seleccionado = mes_seleccionado or (meses_ordenes[0]["clave"] if meses_ordenes else None)
            ordenes = obtener_ordenes_panel(conn, mes_seleccionado)
            citas_hoy_ordenes = obtener_citas_programadas_hoy(conn)
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
            nombre_empleado = " ".join(filter(None, [empleado.get("nombre") or empleado.get("nombres"), empleado.get("apellido") or empleado.get("apellidos")]))
        return templates.TemplateResponse(request=request, name="ordenes.html", context={
            "usuario": usuario, "ordenes": ordenes, "meses_ordenes": meses_ordenes,
            "mes_seleccionado": mes_seleccionado, "empleado_filtro": nombre_empleado or f"Empleado #{empleado_id}", "empleado_filtro_id": empleado_id,
            "citas_hoy_ordenes": citas_hoy_ordenes,
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
            orden = conn.execute(
                text("SELECT * FROM dmi.v_ordenes_resumen WHERE idorden = :id"),
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
            url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"CotizaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n generada correctamente",
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
            insert_dynamic_returning(conn, "facturas", {
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
            })
            update_dynamic(conn, "orden_trabajo", "idorden", orden_id, {"estado": "facturada", "fecha_finalizacion": datetime.now()})
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
    except Exception as e:
        error_msg = f"No se pudo cargar inventario: {e}"
        total_filtrado = 0

    total_productos = int(total_filtrado)
    total_pages = max((total_productos + per_page - 1) // per_page, 1)
    if page > total_pages:
        page = total_pages
    stock_total = sum(int(p.get("cantidad") or 0) for p in productos)
    sin_stock = sum(1 for p in productos if int(p.get("cantidad") or 0) <= 0)
    stock_bajo = sum(1 for p in productos if 0 < int(p.get("cantidad") or 0) <= 2)
    valor_total = sum(float(p.get("precio_venta") or 0) * int(p.get("cantidad") or 0) for p in productos)
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
            conn.execute(
                text("""
                    INSERT INTO dmi.inventario_catalogo
                    (id_original, codigo, nombre, precio_costo, precio_venta, cantidad, categoria, departamento, imagen_url, activo)
                    VALUES (
                        (SELECT COALESCE(MAX(id_original), 0) + 1 FROM dmi.inventario_catalogo),
                        :codigo, :nombre, :precio_costo, :precio_venta, :cantidad, :categoria, :departamento, :imagen_url, TRUE
                    )
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
            )
            conn.commit()
        return RedirectResponse(url="/admin/inventario?success=Producto creado", status_code=302)
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
        return RedirectResponse(url="/admin/inventario?success=Producto actualizado", status_code=302)
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
        body = await request.json()
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
        body = await request.json()
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

        usuario_res = (
            supabase.schema("dmi")
            .table("usuarios")
            .select("idusuarios, usuarionombre, rol, email")
            .eq("id", res.user.id)
            .execute()
        )

        rol = "usuario"
        nombre = ""

        if usuario_res.data:
            rol = usuario_res.data[0].get("rol", "usuario")
            nombre = usuario_res.data[0].get("usuarionombre", "")

        rol_empleado = obtener_rol_empleado_por_email(email)
        if rol != "admin" and rol_empleado:
            rol = rol_empleado

        response = JSONResponse({
            "access_token": res.session.access_token,
            "token": res.session.access_token,
            "role": rol,
            "rol": rol,
            "email": email,
            "nombre": nombre
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


@app.post("/logout")
async def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    response = RedirectResponse(
        url="/?success=SesiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n cerrada correctamente",
        status_code=302
    )

    response.delete_cookie("access_token", samesite="none", secure=True)
    return response


@app.get("/logout-login")
async def logout_login():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", samesite="none", secure=True)
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


# ==================== CREAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
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


# ==================== FORMULARIO EDITAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
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


# ==================== ACTUALIZAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
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
            url="/?success=VehÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­culo actualizado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== ELIMINAR VEHÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂCULO ====================
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
            url="/?success=VehÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­culo eliminado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== PÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂGINA DE CITAS ====================
# ==================== PÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂGINA DE CITAS ====================
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

            conn.execute(
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
                """),
                {
                    "vehiculo": vehiculo_id,
                    "fecha": fecha_cita,
                    "hora": hora_cita,
                    "motivo": motivo,
                    "obs": notas,
                },
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
# ==================== ELIMINAR CITA ====================
@app.post("/citas/eliminar/{cita_id}")
async def eliminar_cita(cita_id: int, access_token: str = Cookie(None)):
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
                text("DELETE FROM dmi.citas WHERE idcita = :id"),
                {"id": cita_id},
            )
            conn.commit()

        return RedirectResponse(
            url="/citas?success=Cita eliminada",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/citas?error={str(e)}",
            status_code=302
        )


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
            "Servicio tÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©cnico automotriz"
        ).strip()

        if costo <= 0:
            return JSONResponse(
                {"error": "Ingresa un costo vÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido para la factura"},
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
                    {"error": "No se encontrÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ la cita"},
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
            url="/?error=Rol invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido",
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

    try:
        user_res = (
            supabase.schema("dmi")
            .table("usuarios")
            .select("id")
            .eq("idusuarios", usuario_id)
            .execute()
        )

        with engine.connect() as conn:
            conn.execute(
                text(
                    "DELETE FROM dmi.usuarios "
                    "WHERE idusuarios = :id"
                ),
                {
                    "id": usuario_id
                },
            )

            conn.commit()

        if user_res.data and user_res.data[0].get("id"):
            supabase.auth.admin.delete_user(
                user_res.data[0]["id"]
            )

        return RedirectResponse(
            url="/?success=Usuario eliminado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/?error={str(e)}",
            status_code=302
        )
# ===== API JSON PARA REACT =====
@app.get("/api/vehiculos")
async def api_vehiculos():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.vehiculos ORDER BY idvehiculo")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/usuarios")
async def api_usuarios():
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
async def api_citas():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT c.*, v.placa, v.marca, v.codigovehiculo
                FROM dmi.citas c
                JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                ORDER BY c.fecha DESC
            """)).mappings().fetchall()
            result = []
            for r in data:
                row = dict(r)
                row["fecha"] = str(row["fecha"])
                row["hora"]  = str(row["hora"])
                result.append(row)
            return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
            if not table_exists(conn, "public", "pedidos"):
                return JSONResponse({"error": "No existe la tabla de pedidos para guardar la compra"}, status_code=500)

            # La relacion permite que compras y productos aparezcan en la ficha
            # administrativa y se inactiven junto con el cliente si es necesario.
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS usuarios_idusuarios integer"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS activo boolean DEFAULT TRUE"))
            conn.execute(text("ALTER TABLE public.pedidos ADD COLUMN IF NOT EXISTS estado varchar DEFAULT 'pendiente'"))
            columnas = table_columns(conn, "public", "pedidos")
            valores = {
                "nombre": datos.get("nombre"), "telefono": datos.get("telefono"),
                "email": usuario.get("email") or datos.get("email"), "direccion": datos.get("direccion"),
                "ciudad": datos.get("ciudad"), "metodo_pago": datos.get("metodoPago") or datos.get("metodo_pago"),
                "total": total_calculado, "productos": json.dumps(productos),
                "usuarios_idusuarios": usuario.get("idusuarios"), "activo": True, "estado": "pendiente",
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
        return JSONResponse({"ok": True, "pedido_id": pedido_id, "total": total_calculado})
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

        referencia = f"DMI-{factura.get('codigo_factura')}-{factura_id}"
        return JSONResponse({
            "ok": True,
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
