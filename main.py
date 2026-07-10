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
import os
import jwt
import json

load_dotenv()

# ==================== CONFIGURACIÃ“N ====================
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.cache = None


# ==================== OBTENER USUARIO ====================
def obtener_usuario(access_token: Optional[str], request: Request = None) -> Optional[dict]:
    if not access_token and request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]

    if not access_token:
        return None
    try:
        # Se mantiene el decodificador sin verificaciÃ³n de firma para evitar cierres de sesiÃ³n automÃ¡ticos
        payload = jwt.decode(access_token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            return None
        user_res = (
            supabase.schema("dmi")
            .table("usuarios")
            .select("usuarionombre, rol")   
            .eq("id", user_id)
            .execute()
        )
        if user_res.data:
            return {
                "id": user_id,
                "nombre": user_res.data[0]["usuarionombre"],
                "rol": user_res.data[0]["rol"],  
            }
    except Exception as e:
        print("ERROR obtener_usuario:", e)
    return None

# ==================== HELPERS DE PERMISOS ====================
def es_admin(usuario: Optional[dict]) -> bool:
    return usuario is not None and usuario.get("rol") == "admin"

def redirigir_sin_permiso(destino: str = "/") -> RedirectResponse:
    return RedirectResponse(
        url=f"{destino}?error=No tienes permiso para realizar esta acciÃ³n",
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


# ==================== PÃGINA PRINCIPAL ====================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: str = Cookie(None)):
    data = []
    tipos = []
    usuarios_data = []
    citas_data = []
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
            "usuario": usuario,
            "success_msg": success_msg,
            "error": error_msg,
            "vehicle_to_edit": None,
        },
    )


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

        response = RedirectResponse(url="/?success=Inicio de sesiÃ³n exitoso", status_code=302)
        response.set_cookie(
            key="access_token",
            value=res.session.access_token,
            httponly=True,
            samesite="lax",
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
            .select("usuarionombre, rol")
            .eq("id", res.user.id)
            .execute()
        )

        rol = "usuario"
        nombre = ""

        if usuario_res.data:
            rol = usuario_res.data[0].get("rol", "usuario")
            nombre = usuario_res.data[0].get("usuarionombre", "")

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
            samesite="lax",
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
    response = RedirectResponse(url="/?success=SesiÃ³n cerrada correctamente", status_code=302)
    response.delete_cookie("access_token")
    return response


# ==================== PROMOVER A ADMIN ====================
@app.post("/admin/promover")
async def promover_admin(
    usuario_id: str = Form(...),   
    secret: str = Form(...),       
    access_token: str = Cookie(None),
):
    if secret != ADMIN_SECRET:
        return RedirectResponse(url="/?error=Clave secreta incorrecta", status_code=302)

    try:
        supabase.schema("dmi").table("usuarios") \
            .update({"rol": "admin"}) \
            .eq("id", usuario_id) \
            .execute()

        return RedirectResponse(url="/?success=Usuario promovido a administrador", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== CREAR VEHÃCULO ====================
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
    shadow_asientos: Optional[str] = Form(None),  # Mapas de asientos alternativos si aplica
    cantidad_asientos: Optional[str] = Form(None),
    capacidad: Optional[str] = Form(None),
    modelo: Optional[str] = Form(None),
):
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]

    usuario = obtener_usuario(access_token, request)
    if not usuario:
        if quiere_json(request):
            return JSONResponse({"error": "Debes iniciar sesion"}, status_code=401)
        return RedirectResponse(url="/?error=Debes iniciar sesiÃ³n", status_code=302)

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

        return RedirectResponse(url="/?success=VehÃ­culo creado y asignado correctamente", status_code=302)
    except Exception as e:
        print("ERROR VEHICULO:", str(e))
        if quiere_json(request):
            return JSONResponse({"error": str(e)}, status_code=500)
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== FORMULARIO EDITAR VEHÃCULO ====================
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


# ==================== ACTUALIZAR VEHÃCULO ====================
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
        return RedirectResponse(url="/?success=VehÃ­culo actualizado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== ELIMINAR VEHÃCULO ====================
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
        return RedirectResponse(url="/?success=VehÃ­culo eliminado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== PÃGINA DE CITAS ====================
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
                    AND EXTRACT(YEAR  FROM c.fecha) = :anio
                    ORDER BY c.fecha, c.hora
                """),
                {"mes": mes, "anio": anio},
            ).mappings().fetchall()

            citas = []
            for c in citas_raw:
                cita = dict(c)
                cita["fecha"] = str(cita["fecha"])
                cita["hora"]  = str(cita["hora"])
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
                cita["hora"]  = str(cita["hora"])
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
            notas = f"Vehiculo descrito por el cliente: {descripcion_vehiculo}\n{notas}".strip()

        with engine.connect() as conn:
            vehiculo_id = int(vehiculos_idvehiculo) if vehiculos_idvehiculo else None

            if not vehiculo_id:
                tipo_row = conn.execute(
                    text("SELECT idtipovehiculos FROM dmi.tipovehiculos ORDER BY idtipovehiculos LIMIT 1")
                ).fetchone()
                if not tipo_row:
                    return JSONResponse({"error": "No hay tipos de vehiculo configurados"}, status_code=400)

                auto_code = f"AUTO{datetime.utcnow().strftime('%m%d%H%M%S%f')[:12]}"
                result = conn.execute(
                    text("""
                        INSERT INTO dmi.vehiculos
                            (codigovehiculo, descripcionvehiculo, motor, cantidad_asientos,
                             placa, capacidad, marca, tipovehiculos_idtipovehiculos, modelo)
                        VALUES
                            (:codigo, :descripcion, :motor, :asientos,
                             :placa, :capacidad, :marca, :tipo, :modelo)
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

                if usuario:
                    conn.execute(
                        text("UPDATE dmi.usuarios SET vehiculos_idvehiculo = :vid WHERE id = :uid"),
                        {"vid": vehiculo_id, "uid": usuario["id"]},
                    )

            conn.execute(
                text("""
                    INSERT INTO dmi.citas
                        (vehiculos_idvehiculo, fecha, hora, motivo, notas, estado)
                    VALUES
                        (:vehiculo, CAST(:fecha AS date), :hora, :motivo, :obs, 'pendiente')
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
            return JSONResponse({"success": True, "message": "Cita agendada correctamente"})
        return RedirectResponse(url="/?admin_section=citas&success=Cita agendada correctamente", status_code=302)
    except Exception as e:
        if quiere_json(request):
            return JSONResponse({"error": str(e)}, status_code=500)
        return RedirectResponse(url=f"/citas?error={str(e)}", status_code=302)


# ==================== ELIMINAR CITA ====================
@app.post("/citas/eliminar/{cita_id}")
async def eliminar_cita(cita_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse(url="/citas?error=Debes iniciar sesiÃ³n", status_code=302)
    
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
        return RedirectResponse(url="/citas?success=Cita eliminada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/citas?error={str(e)}", status_code=302)


# ==================== CAMBIAR ESTADO CITA ====================
@app.post("/citas/estado/{cita_id}")
async def cambiar_estado_cita(
    cita_id: int,
    access_token: str = Cookie(None),
    estado: str = Form(...),
):
    if not access_token:
        return RedirectResponse(url="/citas?error=Debes iniciar sesiÃ³n", status_code=302)
    
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):   
        return redirigir_sin_permiso()

    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE dmi.citas SET estado = :estado WHERE idcita = :id"),
                {"estado": estado, "id": cita_id},
            )
            conn.commit()
        return RedirectResponse(url="/citas?success=Estado actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/citas?error={str(e)}", status_code=302)


@app.post("/api/citas/{cita_id}/factura-servicio")
async def guardar_factura_servicio(
    cita_id: int,
    request: Request,
    access_token: str = Cookie(None),
):
    usuario = obtener_usuario(access_token, request)
    if not es_admin(usuario):
        return JSONResponse({"error": "No tienes permiso para facturar servicios"}, status_code=403)

    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)

        costo = float(body.get("costo") or 0)
        concepto = (body.get("concepto") or "Servicio tecnico automotriz").strip()
        if costo <= 0:
            return JSONResponse({"error": "Ingresa un costo valido para la factura"}, status_code=400)

        factura_linea = (
            f"\n[FAC_SERVICIO] fecha={datetime.now().isoformat(timespec='seconds')}; "
            f"concepto={concepto}; costo={costo}; admin={usuario.get('nombre', 'admin')}"
        )

        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT c.idcita, c.fecha, c.hora, c.motivo, c.estado, c.notas,
                           v.placa, v.marca, v.modelo, v.codigovehiculo,
                           u.nombre, u.apellidos, u.usuarionombre, u.telefono, u.email, u.documento
                    FROM dmi.citas c
                    LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    LEFT JOIN dmi.usuarios u ON u.vehiculos_idvehiculo = c.vehiculos_idvehiculo
                    WHERE c.idcita = :id
                """),
                {"id": cita_id},
            ).mappings().first()

            if not row:
                return JSONResponse({"error": "No se encontro la cita"}, status_code=404)

            notas = f"{row.get('notas') or ''}{factura_linea}".strip()
            conn.execute(
                text("""
                    UPDATE dmi.citas
                    SET estado = 'completada', notas = :notas
                    WHERE idcita = :id
                """),
                {"notas": notas, "id": cita_id},
            )
            conn.commit()

        cita = {}
        for key, value in dict(row).items():
            cita[key] = str(value) if isinstance(value, (date, datetime, time, Decimal, UUID)) else value
        cita["estado"] = "completada"
        cita["notas"] = notas
        cita["costo_facturado"] = costo
        cita["concepto_facturado"] = concepto
        cita["facturada_por"] = usuario.get("nombre", "admin")
        return JSONResponse({"success": True, "cita": cita})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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

    if rol not in ("admin", "usuario"):
        return RedirectResponse(url="/?error=Rol invÃ¡lido", status_code=302)

    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE dmi.usuarios SET rol = :rol WHERE idusuarios = :id"),
                {"rol": rol, "id": usuario_id},
            )
            conn.commit()
        return RedirectResponse(url="/?success=Rol actualizado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== ELIMINAR USUARIO (solo admin) ====================
@app.post("/usuario/eliminar/{usuario_id}")
async def eliminar_usuario(usuario_id: int, access_token: str = Cookie(None)):
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
                text("DELETE FROM dmi.usuarios WHERE idusuarios = :id"),
                {"id": usuario_id},
            )
            conn.commit()

        if user_res.data and user_res.data[0].get("id"):
            supabase.auth.admin.delete_user(user_res.data[0]["id"])

        return RedirectResponse(url="/?success=Usuario eliminado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


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


# â”€â”€ GET /configuracion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

            ctx["ciudades"]         = fetch("SELECT * FROM dmi.ciudades ORDER BY idciudades", "ciudades")
            ctx["tipovehiculos"]    = fetch("SELECT * FROM dmi.tipovehiculos ORDER BY idtipovehiculos", "tipos de vehiculo")
            ctx["metodospago"]      = fetch("SELECT * FROM dmi.metodopago ORDER BY idmetodopago", "metodos de pago")
            ctx["productosprecios"] = fetch("SELECT * FROM dmi.productoprecio ORDER BY idproductoprecio", "precios producto")
            ctx["serviciosprecios"] = fetch("SELECT * FROM dmi.serviciosprecio ORDER BY idserviciosprecio", "precios servicio")
            ctx["inventario"]       = fetch("SELECT * FROM dmi.inventario ORDER BY idinventario", "inventario")
            ctx["oficinas"] = fetch("""
                SELECT o.*, i.codigoinventario, i.descripcioninventario 
                FROM dmi.oficinas o
                LEFT JOIN dmi.inventario i ON i.idinventario = o.inventario_idinventario
                ORDER BY o.idoficinas
            """, "oficinas")
            ctx["servicios"] = fetch("""
                SELECT s.*, sp.descripcionserviciosprecio, sp.precioserviciosprecio 
                FROM dmi.servicios s
                LEFT JOIN dmi.serviciosprecio sp ON sp.idserviciosprecio = s.serviciosprecio_idserviciosprecio
                ORDER BY s.idservicios
            """, "servicios")
            ctx["tiporeparacion"]   = fetch("SELECT * FROM dmi.tiporeparacion ORDER BY idtiporeparacion", "tipos reparacion")
            ctx["pedidos"]          = fetch("SELECT * FROM dmi.pedido ORDER BY idpedido DESC LIMIT 50", "pedidos")
            ctx["productos"]        = fetch("""
                SELECT p.*, pp.descripcionprprecio, pp.valor AS valor_precio
                FROM dmi.productos p
                LEFT JOIN dmi.productoprecio pp ON pp.idproductoprecio = p.productoprecio_idproductoprecio
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
            ctx["usuarios"] = fetch("""
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
            """, "usuarios")
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  CIUDADES â€” CRUD completo (Corregido y Unificado)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@app.post("/config/ciudades/nueva")
async def crear_ciudad(
    access_token: str = Cookie(None),
    codigo_ciudad: int = Form(...),
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
        return RedirectResponse(url="/configuracion?success=Ciudad creada con Ã©xito", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


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

            vehiculos = []
            if vehiculo_id:
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
                        tv.vehiculo AS tipo_vehiculo
                    FROM dmi.vehiculos v
                    LEFT JOIN dmi.tipovehiculos tv ON tv.idtipovehiculos = v.tipovehiculos_idtipovehiculos
                    WHERE v.idvehiculo = :vehiculo_id
                    ORDER BY v.idvehiculo
                    """,
                    {"vehiculo_id": vehiculo_id},
                )

            citas = []
            if vehiculo_id:
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
                        v.placa,
                        COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo
                    FROM dmi.citas c
                    LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    WHERE c.vehiculos_idvehiculo = :vehiculo_id
                    ORDER BY c.fecha DESC, c.hora DESC
                    """,
                    {"vehiculo_id": vehiculo_id},
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

            return JSONResponse({
                "usuario": usuario,
                "vehiculos": vehiculos,
                "citas": citas,
                "pedidos": pedidos,
                "pagos": pagos,
                "productos": productos,
                "notas": notas,
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/mi-garage")
async def api_mi_garage(request: Request, access_token: str = Cookie(None)):
    usuario_actual = obtener_usuario(access_token, request)
    if not usuario_actual:
        return JSONResponse({"error": "Debes iniciar sesion"}, status_code=401)

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
            vehiculo_id = usuario.get("vehiculos_idvehiculo")

            vehiculos = []
            if vehiculo_id:
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
                        tv.vehiculo AS tipo_vehiculo
                    FROM dmi.vehiculos v
                    LEFT JOIN dmi.tipovehiculos tv ON tv.idtipovehiculos = v.tipovehiculos_idtipovehiculos
                    WHERE v.idvehiculo = :vehiculo_id
                    ORDER BY v.idvehiculo
                    """,
                    {"vehiculo_id": vehiculo_id},
                )

            citas = []
            if vehiculo_id:
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
                        v.placa,
                        COALESCE(v.marca, '') || ' ' || COALESCE(v.modelo, '') AS vehiculo
                    FROM dmi.citas c
                    LEFT JOIN dmi.vehiculos v ON v.idvehiculo = c.vehiculos_idvehiculo
                    WHERE c.vehiculos_idvehiculo = :vehiculo_id
                    ORDER BY c.fecha DESC, c.hora DESC
                    """,
                    {"vehiculo_id": vehiculo_id},
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

            return JSONResponse({
                "usuario": usuario,
                "vehiculos": vehiculos,
                "citas": citas,
                "pedidos": pedidos,
                "pagos": pagos,
                "productos": productos,
                "notas": notas,
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
            select_sql = cfg.get("select") or f"SELECT * FROM dmi.{cfg['table']} WHERE {cfg['pk']} = :id"
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
        fields = [field for field in cfg["fields"] if field in form]
        values = {field: normalize_config_value(form.get(field)) for field in fields}

        if not fields:
            return config_redirect(entity, "No llegaron datos para guardar", False)

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
        fields = [field for field in cfg["fields"] if field in form]
        values = {field: normalize_config_value(form.get(field)) for field in fields}

        if not fields:
            return config_redirect(entity, "No llegaron datos para editar", False)

        assignments = ", ".join(f"{field} = :{field}" for field in fields)
        values["id"] = record_id
        with engine.connect() as conn:
            conn.execute(
                text(f"UPDATE dmi.{cfg['table']} SET {assignments} WHERE {cfg['pk']} = :id"),
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
            conn.execute(
                text(f"DELETE FROM dmi.{cfg['table']} WHERE {cfg['pk']} = :id"),
                {"id": record_id},
            )
            conn.commit()
        return config_redirect(entity, "Registro eliminado correctamente")
    except Exception as e:
        return config_redirect(entity, str(e), False)
