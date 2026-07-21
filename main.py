from fastapi import FastAPI, Form, Request, Cookie, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
from datetime import date, datetime, time
from decimal import Decimal
from urllib.parse import quote
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.app\.github\.dev|http://localhost:3000|http://127\.0\.0\.1:3000",
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
        # Se mantiene el decodificador sin verificación automática
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




def obtener_ordenes_panel(conn) -> list:
    return [dict(row) for row in conn.execute(
        text("""
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
            ORDER BY fecha_apertura DESC, idorden DESC
            LIMIT 100
        """)
    ).mappings().fetchall()]


def obtener_ordenes_mecanico(conn, empleado_id: int) -> list:
    orden_col = empleado_orden_column(conn)
    if not orden_col:
        return []
    return [dict(row) for row in conn.execute(
        text(f"""
            SELECT r.*
            FROM dmi.v_ordenes_resumen r
            JOIN dmi.orden_trabajo ot ON ot.idorden = r.idorden
            WHERE ot.{orden_col} = :empleado_id
            ORDER BY r.fecha_apertura DESC, r.idorden DESC
            LIMIT 100
        """),
        {"empleado_id": empleado_id},
    ).mappings().fetchall()]


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
# ==================== PÁGINA PRINCIPAL ====================
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

    try:
        with engine.connect() as conn:
            if es_admin(usuario):
                ordenes = obtener_ordenes_panel(conn)
            else:
                empleado = obtener_empleado_actual(conn, usuario)
                if empleado:
                    ordenes = obtener_ordenes_mecanico(conn, empleado.get("idempleado"))
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

    try:
        with engine.connect() as conn:
            ordenes = obtener_ordenes_panel(conn)
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
            "success_msg": success_msg,
            "error": error_msg,
        },
    )


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

            diagnostico = conn.execute(
                text("SELECT * FROM dmi.diagnosticos WHERE orden_id = :id ORDER BY fecha_diagnostico DESC LIMIT 1"),
                {"id": orden_id},
            ).mappings().fetchone()
            servicios = [dict(row) for row in conn.execute(
                text("SELECT * FROM dmi.detalle_servicios WHERE orden_id = :id ORDER BY iddetalle_servicio"),
                {"id": orden_id},
            ).mappings().fetchall()]
            repuestos = [dict(row) for row in conn.execute(
                text("SELECT * FROM dmi.detalle_repuestos WHERE orden_id = :id ORDER BY iddetalle_repuesto"),
                {"id": orden_id},
            ).mappings().fetchall()]
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
            "servicios_orden": servicios,
            "repuestos_orden": repuestos,
            "factura_orden": dict(factura) if factura else None,
            "pagos_orden": pagos,
            "productos_inventario": productos_inventario,
            "metodos_pago": metodos_pago,
            "total_ordenes": 1 if orden else 0,
            "total_diagnostico": 1 if diagnostico else 0,
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

            diagnostico_existente = conn.execute(
                text("""
                    SELECT iddiagnostico
                    FROM dmi.diagnosticos
                    WHERE orden_id = :orden_id
                """),
                {"orden_id": orden_id},
            ).fetchone()

            if diagnostico_existente:

                conn.execute(
                    text("""
                        UPDATE dmi.diagnosticos
                        SET
                            diagnostico_tecnico = :diagnostico,
                            recomendacion = :recomendacion,
                            fecha_diagnostico = :fecha,
                            estado = 'registrado'
                        WHERE orden_id = :orden_id
                    """),
                    {
                        "orden_id": orden_id,
                        "diagnostico": diagnostico_tecnico,
                        "recomendacion": recomendacion,
                        "fecha": datetime.now(),
                    },
                )

            else:

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
            url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Diagnóstico guardado correctamente",
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
    descripcion: str = Form(...),
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
            conn.commit()
        return RedirectResponse(url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Repuesto agregado e inventario actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}", status_code=302)


@app.post("/admin/ordenes/{orden_id}/cotizacion")
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
            url=(f"/admin/ordenes/{orden_id}?success=" if es_admin(usuario) else f"/mecanico/ordenes/{orden_id}?success=") + f"Cotización generada correctamente",
            status_code=302,
        )

    except Exception as e:
        return RedirectResponse(
            url=f"/admin/ordenes/{orden_id}?error={quote(str(e))}",
            status_code=302,
        )

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
            total_servicios, total_repuestos, total_orden = actualizar_totales_orden(conn, orden_id)
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

        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
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
                    {"error": "Este correo ya tiene una cuenta. Inicia sesion o recupera la contrasena."},
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

        usuario_payload = {
            "id": res.user.id,
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

        supabase.schema("dmi").table("usuarios").insert(usuario_payload).execute()

        return JSONResponse({"success": True, "message": "Usuario registrado correctamente"})
    except Exception as e:
        print("ERROR registro-react:", e)
        error_text = str(e).lower()
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


# ==================== LOGIN / LOGOUT ====================
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
        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return JSONResponse({"message": "Correo y contraseña son obligatorios"}, status_code=400)

        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
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
        print("ERROR login-react:", e)
        return JSONResponse(
            {"message": "Error al iniciar sesión", "detail": str(e)},
            status_code=500
        )


@app.post("/logout")
async def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    response = RedirectResponse(
        url="/?success=Sesión cerrada correctamente",
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


# ==================== CREAR VEHÍCULO ====================
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
                {"error": "Debes iniciar sesión"},
                status_code=401
            )

        return RedirectResponse(
            url="/?error=Debes iniciar sesión",
            status_code=302
        )
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO dmi.vehiculos
                        (codigovehiculo, descripcionvehiculo, motor, cantidad_asientos,
                         placa, capacidad, marca, tipovehiculos_idtipovehiculos, modelo)
                    VALUES
                        (:codigovehiculo, :descripcionvehiculo, :motor, :cantidad_asientos,
                         :placa, :capacidad, :marca, :tipovehiculos_idtipovehiculos, :modelo)
                    RETURNING idvehiculo
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
                },
            )
            nuevo_id = result.fetchone()[0]   

            conn.execute(
                text("UPDATE dmi.usuarios SET vehiculos_idvehiculo = :vid WHERE id = :uid"),
                {"vid": nuevo_id, "uid": usuario["id"]},
            )
            conn.commit()

        if quiere_json(request):
            return JSONResponse({"success": True, "message": "Vehiculo creado correctamente", "idvehiculo": nuevo_id})

        return RedirectResponse(url="/?success=Vehículo creado y asignado correctamente", status_code=302)
    except Exception as e:
        print("ERROR VEHICULO:", str(e))
        if quiere_json(request):
            return JSONResponse({"error": str(e)}, status_code=500)
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== FORMULARIO EDITAR VEHÍCULO ====================
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


# ==================== ACTUALIZAR VEHÍCULO ====================
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
            url="/?success=Vehículo actualizado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== ELIMINAR VEHÍCULO ====================
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
            url="/?success=Vehículo eliminado correctamente",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== PÁGINA DE CITAS ====================
# ==================== PÁGINA DE CITAS ====================
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
                f"Vehículo descrito por el cliente: "
                f"{descripcion_vehiculo}\n{notas}"
            ).strip()

        with engine.connect() as conn:
            vehiculo_id = int(vehiculos_idvehiculo) if vehiculos_idvehiculo else None

            if not vehiculo_id:
                tipo_row = conn.execute(
                    text(
                        "SELECT idtipovehiculos "
                        "FROM dmi.tipovehiculos "
                        "ORDER BY idtipovehiculos LIMIT 1"
                    )
                ).fetchone()

                if not tipo_row:
                    return JSONResponse(
                        {"error": "No hay tipos de vehículo configurados"},
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
                        "descripcion": descripcion_vehiculo or "Vehículo descrito por el cliente",
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

                if usuario:
                    conn.execute(
                        text(
                            "UPDATE dmi.usuarios "
                            "SET vehiculos_idvehiculo = :vid "
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
            url="/citas?error=Debes iniciar sesión",
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
            url="/citas?error=Debes iniciar sesión",
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
            "Servicio técnico automotriz"
        ).strip()

        if costo <= 0:
            return JSONResponse(
                {"error": "Ingresa un costo válido para la factura"},
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
                    {"error": "No se encontró la cita"},
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
            url="/?error=Rol inválido",
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
                    return []

            try:
                asegurar_servicios_base(conn)
            except Exception as e:
                load_errors.append("servicios base: " + str(e))
                conn.rollback()
            ctx["ciudades"]         = fetch("SELECT * FROM dmi.ciudades ORDER BY idciudades", "ciudades")
            ctx["tipovehiculos"]    = fetch("SELECT * FROM dmi.tipovehiculos ORDER BY idtipovehiculos", "tipos de vehiculo")
            ctx["metodospago"]      = fetch("SELECT * FROM dmi.metodopago ORDER BY idmetodopago", "metodos de pago")
            ctx["productosprecios"] = fetch("SELECT * FROM dmi.productoprecio ORDER BY idproductoprecio", "precios producto")
            ctx["serviciosprecios"] = fetch("SELECT * FROM dmi.serviciosprecio ORDER BY idserviciosprecio", "precios servicio")
            ctx["inventario"]       = fetch("SELECT * FROM dmi.inventario ORDER BY idinventario", "inventario")
            ctx["oficinas"] = fetch("""
                SELECT
                    o.*,
                    c.descripcion_ciudad,
                    c.codigo_ciudad,
                    i.codigoinventario,
                    i.descripcioninventario
                FROM dmi.oficinas o
                LEFT JOIN dmi.ciudades c ON c.idciudades = o.ciudades_idciudades
                LEFT JOIN dmi.inventario i ON i.idinventario = o.inventario_idinventario
                ORDER BY o.idoficinas
            """, "oficinas")
            ctx["servicios"] = fetch("""
                SELECT
                    s.*,
                    sp.descripcionserviciosprecio,
                    sp.precioserviciosprecio,
                    pe.codigopedido
                FROM dmi.servicios s
                LEFT JOIN dmi.serviciosprecio sp ON sp.idserviciosprecio = s.serviciosprecio_idserviciosprecio
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
                    p.*,
                    pp.descripcionprprecio,
                    pp.valor AS valor_precio,
                    pe.codigopedido
                FROM dmi.productos p
                LEFT JOIN dmi.productoprecio pp ON pp.idproductoprecio = p.productoprecio_idproductoprecio
                LEFT JOIN dmi.pedido pe ON pe.idpedido = p.pedido_idpedido
                ORDER BY p.idproductos
            """, "productos")
            ctx["movimientos"] = fetch("""
                SELECT m.*, i.codigoinventario, i.descripcioninventario 
                FROM dmi.movimientos_inventario m
                LEFT JOIN dmi.inventario i ON i.idinventario = m.inventario_id
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
            data = conn.execute(text("SELECT * FROM dmi.inventario ORDER BY idinventario")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

#=========================== MOVIMIENTOS INVENTARIO =============================
@app.get("/api/movimientos_inventario")
async def api_movimientos():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("""
                SELECT m.*, i.codigoinventario 
                FROM dmi.movimientos_inventario m
                LEFT JOIN dmi.inventario i ON i.idinventario = m.inventario_id
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
            data = conn.execute(text("SELECT idproductoprecio as id, codigoproductoprecio, descripcionprprecio, valor as precio FROM dmi.productoprecio ORDER BY idproductoprecio")).mappings().fetchall()
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
                    s.serviciosprecio_idserviciosprecio,
                    sp.descripcionserviciosprecio,
                    sp.precioserviciosprecio,
                    pe.codigopedido
                FROM dmi.servicios s
                LEFT JOIN dmi.serviciosprecio sp ON sp.idserviciosprecio = s.serviciosprecio_idserviciosprecio
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
            data = conn.execute(text("SELECT idserviciosprecio as id, codigoserviciosprecio, descripcionserviciosprecio, precioserviciosprecio as precio FROM dmi.serviciosprecio ORDER BY idserviciosprecio")).mappings().fetchall()
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
                    INSERT INTO dmi.inventario
                    (codigoinventario, descripcioninventario, pedido_idpedido, cantidad, costo_unitario, unidad_medida, estado, oficinas_idoficinas)
                    VALUES (:codigo, :descripcion, :pedido, :cantidad, :costo, :unidad, :estado, :oficina)
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
                if "email" in checkout_columns and usuario.get("email"):
                    order_column = "id" if "id" in checkout_columns else "created_at" if "created_at" in checkout_columns else None
                    order_sql = f"ORDER BY {order_column} DESC" if order_column else ""
                    cart_field = next((field for field in ("productos", "items", "carrito", "cart") if field in checkout_columns), None)
                    public_pedidos = query_rows(
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
                    p.codigoproductos,
                    p.descripcionproductos
                FROM dmi.detalle_repuestos dr
                LEFT JOIN dmi.productos p ON p.idproductos = dr.producto_id
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
                "servicios_orden": servicios_orden,
                "repuestos_orden": repuestos_orden,
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