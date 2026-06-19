from fastapi import FastAPI, Form, Request, Cookie, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
import os
import jwt


load_dotenv()



# ==================== CONFIGURACIÓN ====================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.pjgldixdkavafmxowujt:camiloide1606@aws-1-us-east-1.pooler.supabase.com:5432/postgres")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pjgldixdkavafmxowujt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "yJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBqZ2xkaXhka2F2YWZteG93dWp0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE2MDMxOTAsImV4cCI6MjA4NzE3OTE5MH0.VsdOpz44v2pVYb94ESnw-nmLe7OmaXsm_mMfU-FEKAA")
ADMIN_SECRET  = os.getenv("ADMIN_SECRET", "lolcito")  

engine = create_engine(DATABASE_URL)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

origins = [
    "https://shiny-space-barnacle-5gw6x4p97vqf744g-3000.app.github.dev", 
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://shiny-space-barnacle-5gw6x4p97vqf744g-3000.app.github.dev",
        "http://localhost:3000",
    ],
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
    except Exception:
        pass
    return None

# ==================== HELPERS DE PERMISOS ====================

def es_admin(usuario: Optional[dict]) -> bool:
    return usuario is not None and usuario.get("rol") == "admin"

def redirigir_sin_permiso(destino: str = "/") -> RedirectResponse:
    return RedirectResponse(
        url=f"{destino}?error=No tienes permiso para realizar esta acción",
        status_code=302,
    )


# ==================== DATOS BASE ====================
def obtener_datos_base(conn) -> tuple[list, list]:
    data  = conn.execute(text("SELECT * FROM dmi.vehiculos LIMIT 20")).fetchall()
    tipos = conn.execute(
        text("SELECT idtipovehiculos, codigotipovehiculos FROM dmi.tipovehiculos")
    ).fetchall()
    return data, tipos


# ==================== PÁGINA PRINCIPAL ====================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: str = Cookie(None)):
    data = []
    tipos = []
    usuarios_data = []
    error_msg   = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    usuario = obtener_usuario(access_token)

    try:
        with engine.connect() as conn:
            data, tipos = obtener_datos_base(conn)
          
            if es_admin(usuario):  
                usuarios_data = conn.execute(
                    text("SELECT * FROM dmi.usuarios LIMIT 20")
                ).fetchall()
    except Exception as e:
        error_msg = str(e)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data": data,
            "tipos": tipos,
            "usuarios_data": usuarios_data,
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


# ==================== LOGIN / LOGOUT ====================
@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not res.user:
            return RedirectResponse(url="/?error=Credenciales incorrectas", status_code=302)

        response = RedirectResponse(url="/?success=Inicio de sesión exitoso", status_code=302)
        response.set_cookie(
            key="access_token",
            value=res.session.access_token,
            httponly=True,
            samesite="lax",
        )
        return response
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


@app.post("/logout")
async def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    response = RedirectResponse(url="/?success=Sesión cerrada correctamente", status_code=302)
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


# ==================== CREAR VEHÍCULO ====================
@app.post("/vehiculo/nuevo")
async def crear_vehiculo(
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
    if not usuario:
        return RedirectResponse(url="/?error=Debes iniciar sesión", status_code=302)

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

        return RedirectResponse(url="/?success=Vehículo creado y asignado correctamente", status_code=302)
    except Exception as e:
        print("ERROR VEHICULO:", str(e))
        return RedirectResponse(
            url=f"/?error={str(e)}",
            status_code=302
        )


# ==================== FORMULARIO EDITAR VEHÍCULO ====================
@app.get("/vehiculo/editar/{vehiculo_id}", response_class=HTMLResponse)
async def editar_vehiculo_form(
    request: Request, vehiculo_id: int, access_token: str = Cookie(None)
):
    usuario = obtener_usuario(access_token)

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
        return RedirectResponse(url="/?success=Vehículo actualizado correctamente", status_code=302)
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
        return RedirectResponse(url="/?success=Vehículo eliminado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)

# ==================== PÁGINA DE CITAS ====================
@app.get("/citas", response_class=HTMLResponse)
async def ver_citas(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)

    if not es_admin(usuario):
        return redirigir_sin_permiso()

    error_msg = request.query_params.get("error")
    success_msg = request.query_params.get("success")
    mes = request.query_params.get("mes")
    anio = request.query_params.get("anio")

    from datetime import date
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
    access_token: str = Cookie(None),
    vehiculos_idvehiculo: int = Form(...),
    fecha_cita: str = Form(...),
    hora_cita: str = Form(...),
    motivo: str = Form(...),
    observaciones: Optional[str] = Form(None),
):
    if not access_token:
        return RedirectResponse(url="/citas?error=Debes iniciar sesión", status_code=302)

    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):   
        return redirigir_sin_permiso()

    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.citas
                        (vehiculos_idvehiculo, fecha, hora, motivo, notas, estado)
                    VALUES
                        (:vehiculo, CAST(:fecha AS date), :hora, :motivo, :obs, 'pendiente')
                """),
                {
                    "vehiculo": vehiculos_idvehiculo,
                    "fecha": fecha_cita,
                    "hora": hora_cita,
                    "motivo": motivo,
                    "obs": observaciones,
                },
            )
            conn.commit()
        return RedirectResponse(url="/citas?success=Cita agendada correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/citas?error={str(e)}", status_code=302)


# ==================== ELIMINAR CITA ====================
@app.post("/citas/eliminar/{cita_id}")
async def eliminar_cita(cita_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse(url="/citas?error=Debes iniciar sesión", status_code=302)
    
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
        return RedirectResponse(url="/citas?error=Debes iniciar sesión", status_code=302)
    
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
        return RedirectResponse(url="/?error=Rol inválido", status_code=302)

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
            data = conn.execute(text("SELECT * FROM dmi.vehiculos")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/usuarios")
async def api_usuarios():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.usuarios")).mappings().fetchall()
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


# ── GET /configuracion ────────────────────────────────────────────
@app.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso()

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
        "movimientos":      [],   # ← Se llenará abajo
    }



    try:
        with engine.connect() as conn:
            def fetch(query):
                return [dict(r) for r in conn.execute(text(query)).mappings().fetchall()]

            ctx["ciudades"]         = fetch("SELECT * FROM dmi.ciudades ORDER BY idciudades")
            ctx["tipovehiculos"]    = fetch("SELECT * FROM dmi.tipovehiculos ORDER BY idtipovehiculos")
            ctx["metodospago"]      = fetch("SELECT * FROM dmi.metodopago ORDER BY idmetodopago")
            ctx["productosprecios"] = fetch("SELECT * FROM dmi.productoprecio ORDER BY idproductoprecio")
            ctx["serviciosprecios"] = fetch("SELECT * FROM dmi.serviciosprecio ORDER BY idserviciosprecio")
            ctx["inventario"]       = fetch("SELECT * FROM dmi.inventario ORDER BY idinventario")
            ctx["oficinas"] = fetch("""
                SELECT o.*, i.codigoinventario, i.descripcioninventario 
                FROM dmi.oficinas o
                LEFT JOIN dmi.inventario i ON i.idinventario = o.inventario_idinventario
                ORDER BY o.idoficinas
            """)
            ctx["servicios"] = fetch("""
                SELECT s.*, sp.descripcionserviciosprecio, sp.precioserviciosprecio 
                FROM dmi.servicios s
                LEFT JOIN dmi.serviciosprecio sp ON sp.idserviciosprecio = s.serviciosprecio_idserviciosprecio
                ORDER BY s.idservicios
            """)
            ctx["tiporeparacion"]   = fetch("SELECT * FROM dmi.tiporeparacion ORDER BY idtiporeparacion")
            ctx["pedidos"]          = fetch("SELECT * FROM dmi.pedido ORDER BY idpedido DESC LIMIT 50")
            ctx["productos"]        = fetch("""SELECT p.*, pp.descripcionprprecio, pp.valor AS valor_precio
                                        FROM dmi.productos p
                                        LEFT JOIN dmi.productoprecio pp ON pp.idproductoprecio = p.productoprecio_idproductoprecio
                                        ORDER BY p.idproductos
                                    """)

            # ← ESTA ES LA LÍNEA QUE FALTABA
            ctx["movimientos"] = fetch("""
                SELECT m.*, i.codigoinventario, i.descripcioninventario 
                FROM dmi.movimientos_inventario m
                LEFT JOIN dmi.inventario i ON i.idinventario = m.inventario_id
                ORDER BY m.fecha DESC 
                LIMIT 50
            """)

    except Exception as e:
        ctx["error"] = str(e)
        
    return templates.TemplateResponse(
        request=request,
        name="configuracion.html",
        context=ctx,
    )


# ══════════════════════════════════════════════════════════════════
#  CIUDADES — CRUD completo
# ══════════════════════════════════════════════════════════════════

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
                {"codigo": codigo_ciudad, "descripcion": descripcion_ciudad, "postal": codigo_postal},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Ciudad creada correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/ciudades/editar/{ciudad_id}")
async def editar_ciudad(
    ciudad_id: int,
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
                    UPDATE dmi.ciudades
                    SET codigo_ciudad = :codigo, descripcion_ciudad = :descripcion, codigo_postal = :postal
                    WHERE idciudades = :id
                """),
                {"codigo": codigo_ciudad, "descripcion": descripcion_ciudad, "postal": codigo_postal, "id": ciudad_id},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Ciudad actualizada correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/ciudades/eliminar/{ciudad_id}")
async def eliminar_ciudad(ciudad_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.ciudades WHERE idciudades = :id"), {"id": ciudad_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Ciudad eliminada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  TIPO VEHÍCULOS — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/tipovehiculos/nuevo")
async def crear_tipovehiculo(
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
                text("""
                    INSERT INTO dmi.tipovehiculos
                        (codigotipovehiculos, vehiculo)
                    VALUES (:codigo, :vehiculo)
                """),
                {
                    "codigo":      codigotipovehiculos,
                    "vehiculo": vehiculo
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo de vehículo creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/tipovehiculos/editar/{tipo_id}")
async def editar_tipovehiculo(
    tipo_id: int,
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
                text("""
                    UPDATE dmi.tipovehiculos
                    SET codigotipovehiculos = :codigo,
                        vehiculos = :vehiculo,
                    WHERE idtipovehiculos = :id
                """),
                {
                    "codigo":      codigotipovehiculos,
                    "vehiculo": vehiculo,
                    "id":          tipo_id,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo de vehículo actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/tipovehiculos/eliminar/{tipo_id}")
async def eliminar_tipovehiculo(tipo_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.tipovehiculos WHERE idtipovehiculos = :id"), {"id": tipo_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  MÉTODO DE PAGO — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/metodopago/nuevo")
async def crear_metodopago(
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
                text("INSERT INTO dmi.metodopago (codigompago, descripcionmpago) VALUES (:codigo, :desc)"),
                {"codigo": codigompago, "desc": descripcionmpago},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Método de pago creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/metodopago/editar/{mp_id}")
async def editar_metodopago(
    mp_id: int,
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
                text("""
                    UPDATE dmi.metodopago
                    SET codigompago = :codigo, descripcionmpago = :desc
                    WHERE idmetodopago = :id
                """),
                {"codigo": codigompago, "desc": descripcionmpago, "id": mp_id},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Método de pago actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/metodopago/eliminar/{mp_id}")
async def eliminar_metodopago(mp_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.metodopago WHERE idmetodopago = :id"), {"id": mp_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Método eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  PRECIO PRODUCTO — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/productoprecio/nuevo")
async def crear_productoprecio(
    access_token: str = Cookie(None),
    codigoproductoprecio: str = Form(...),
    descripcionprprecio: str = Form(...),
    valor: float = Form(...),        
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.productoprecio (codigoproductoprecio, descripcionprprecio, valor)
                    VALUES (:codigo, :desc, :valor)
                """),
                {"codigo": codigoproductoprecio, "desc": descripcionprprecio, "valor": valor},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Precio de producto creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/productoprecio/editar/{pp_id}")
async def editar_productoprecio(
    pp_id: int,
    access_token: str = Cookie(None),
    codigoproductoprecio: str = Form(...),
    descripcionprprecio: str = Form(...),
    valor: float = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.productoprecio
                    SET codigoproductoprecio = :codigo, descripcionprprecio = :desc, valor = :valor
                    WHERE idproductoprecio = :id
                """),
                {"codigo": codigoproductoprecio, "desc": descripcionprprecio, "valor": valor, "id": pp_id},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Precio de producto actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/productoprecio/eliminar/{pp_id}")
async def eliminar_productoprecio(pp_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.productoprecio WHERE idproductoprecio = :id"), {"id": pp_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Precio eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  PRECIO SERVICIO — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/serviciosprecio/nuevo")
async def crear_serviciosprecio(
    access_token: str = Cookie(None),
    codigoserviciosprecio: str = Form(...),
    descripcionserviciosprecio: str = Form(...),
    precioserviciosprecio: str = Form(...)
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.serviciosprecio (codigoserviciosprecio, descripcionserviciosprecio, precioserviciosprecio)
                    VALUES (:codigo, :desc, :precio)
                """),
                {"codigo": codigoserviciosprecio, "desc": descripcionserviciosprecio, "precio": precioserviciosprecio},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Precio de servicio creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/serviciosprecio/editar/{sp_id}")
async def editar_serviciosprecio(
    sp_id: int,
    access_token: str = Cookie(None),
    codigoserviciosprecio: str = Form(...),
    descripcionserviciosprecio: str = Form(...),
    precioserviciosprecio: str = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.serviciosprecio
                    SET codigoserviciosprecio = :codigo,
                        descripcionserviciosprecio = :desc,
                        precioserviciosprecio = :precio
                    WHERE idserviciosprecio = :id
                """),
                {"codigo": codigoserviciosprecio, "desc": descripcionserviciosprecio, "precio": precioserviciosprecio, "id": sp_id},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Precio de servicio actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/serviciosprecio/eliminar/{sp_id}")
async def eliminar_serviciosprecio(sp_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.serviciosprecio WHERE idserviciosprecio = :id"), {"id": sp_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Precio eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  INVENTARIO — CRUD completo (NIIF compliant)
# ══════════════════════════════════════════════════════════════════

@app.post("/config/inventario/nuevo")
async def crear_inventario(
    access_token: str = Cookie(None),
    codigoinventario: str = Form(...),
    descripcioninventario: str = Form(...),
    cantidad: float = Form(0),
    costo_unitario: float = Form(0),
    unidad_medida: str = Form("UND"),
    estado: str = Form("activo"),
    pedido_idpedido: Optional[int] = Form(None),   # ← Muy importante
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.inventario 
                    (codigoinventario, descripcioninventario, cantidad, 
                     costo_unitario, unidad_medida, estado, pedido_idpedido)
                    VALUES 
                    (:codigo, :desc, :cant, :costo, :unidad, :estado, :pedido)
                """),
                {
                    "codigo": codigoinventario,
                    "desc": descripcioninventario,
                    "cant": cantidad,
                    "costo": costo_unitario,
                    "unidad": unidad_medida,
                    "estado": estado,
                    "pedido": pedido_idpedido,
                }
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Ítem creado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/config/inventario/editar/{inv_id}")
async def editar_inventario(
    inv_id: int,
    access_token: str = Cookie(None),
    codigoinventario: str = Form(...),
    descripcioninventario: str = Form(...),
    cantidad: float = Form(...),
    costo_unitario: float = Form(...),
    unidad_medida: str = Form("UND"),
    estado: str = Form("activo"),
    pedido_idpedido: Optional[int] = Form(None),
    oficinas_idoficinas: Optional[int] = Form(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.inventario SET
                        codigoinventario = :codigo,
                        descripcioninventario = :desc,
                        cantidad = :cant,
                        costo_unitario = :costo,
                        unidad_medida = :unidad,
                        estado = :estado,
                        pedido_idpedido = :pedido,
                        oficinas_idoficinas = :oficina
                    WHERE idinventario = :id
                """),
                {
                    "codigo": codigoinventario,
                    "desc": descripcioninventario,
                    "cant": cantidad,
                    "costo": costo_unitario,
                    "unidad": unidad_medida,
                    "estado": estado,
                    "pedido": pedido_idpedido,
                    "oficina": oficinas_idoficinas,
                    "id": inv_id,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Ítem actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/inventario/eliminar/{inv_id}")
async def eliminar_inventario(inv_id: int, access_token: str = Cookie(None)):
    # ... (mismo que tenías)
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.inventario WHERE idinventario = :id"), {"id": inv_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Ítem eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)
    



# ══════════════════════════════════════════════════════════════════
#  MOVIMIENTOS DE INVENTARIO
# ══════════════════════════════════════════════════════════════════

@app.post("/config/movimientos/nuevo")
async def crear_movimiento(
    access_token: str = Cookie(None),
    inventario_id: int = Form(...),
    tipo_movimiento: str = Form(...),
    cantidad: float = Form(...),
    costo_unitario: Optional[float] = Form(None),
    motivo: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")

    try:
        with engine.connect() as conn:
            # Registrar movimiento
            conn.execute(
                text("""
                    INSERT INTO dmi.movimientos_inventario 
                    (inventario_id, tipo_movimiento, cantidad, costo_unitario, motivo, usuario_id)
                    VALUES (:inv_id, :tipo, :cant, :costo, :motivo, :uid)
                """),
                {
                    "inv_id": inventario_id,
                    "tipo": tipo_movimiento,
                    "cant": cantidad,
                    "costo": costo_unitario,
                    "motivo": motivo,
                    "uid": usuario["id"]
                }
            )
            
            # Actualizar stock
            if tipo_movimiento == "entrada":
                conn.execute(
                    text("UPDATE dmi.inventario SET cantidad = cantidad + :cant WHERE idinventario = :id"),
                    {"cant": cantidad, "id": inventario_id}
                )
            else:  # salida o ajuste
                conn.execute(
                    text("UPDATE dmi.inventario SET cantidad = cantidad - :cant WHERE idinventario = :id"),
                    {"cant": cantidad, "id": inventario_id}
                )
            
            conn.commit()
            
        return RedirectResponse(url="/configuracion?success=Movimiento registrado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)



    
# ══════════════════════════════════════════════════════════════════
#  OFICINAS — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/oficinas/nueva")
async def crear_oficina(
    access_token: str = Cookie(None),
    codigo_oficina: str = Form(...),
    direccion: str = Form(...),
    telefono_oficina: str = Form(...),
    descripcionof: str = Form(...),
    ciudades_idciudades: int = Form(...),
    inventario_idinventario: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.oficinas
                        (codigo_oficina, direccion, telefono_oficina, descripcionof,
                         ciudades_idciudades, inventario_idinventario)
                    VALUES (:codigo, :dir, :tel, :desc, :ciudad, :inv)
                """),
                {
                    "codigo":   codigo_oficina,
                    "dir":      direccion,
                    "tel":      telefono_oficina,
                    "desc":     descripcionof,
                    "ciudad":   ciudades_idciudades,
                    "inv":      inventario_idinventario,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Oficina creada correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/oficinas/editar/{of_id}")
async def editar_oficina(
    of_id: int,
    access_token: str = Cookie(None),
    codigo_oficina: str = Form(...),
    direccion: str = Form(...),
    telefono_oficina: str = Form(...),
    descripcionof: str = Form(...),
    ciudades_idciudades: int = Form(...),
    inventario_idinventario: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.oficinas
                    SET codigo_oficina = :codigo,
                        direccion = :dir,
                        telefono_oficina = :tel,
                        descripcionof = :desc,
                        ciudades_idciudades = :ciudad,
                        inventario_idinventario = :inv
                    WHERE idoficinas = :id
                """),
                {
                    "codigo":   codigo_oficina,
                    "dir":      direccion,
                    "tel":      telefono_oficina,
                    "desc":     descripcionof,
                    "ciudad":   ciudades_idciudades,
                    "inv":      inventario_idinventario,
                    "id":       of_id,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Oficina actualizada correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/oficinas/eliminar/{of_id}")
async def eliminar_oficina(of_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.oficinas WHERE idoficinas = :id"), {"id": of_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Oficina eliminada", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  SERVICIOS — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/servicios/nuevo")
async def crear_servicio(
    access_token: str = Cookie(None),
    codigoservicio: str = Form(...),
    descripcionservicio: str = Form(...),
    serviciosprecio_idserviciosprecio: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.servicios 
                    (codigoservicio, descripcionservicio, serviciosprecio_idserviciosprecio)
                    VALUES (:codigo, :desc, :precio)
                """),
                {
                    "codigo": codigoservicio,
                    "desc": descripcionservicio,
                    "precio": serviciosprecio_idserviciosprecio,
                }
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Servicio creado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={str(e)}", status_code=302)


@app.post("/config/servicios/editar/{srv_id}")
async def editar_servicio(
    srv_id: int,
    access_token: str = Cookie(None),
    codigoservicio: str = Form(...),
    descripcionservicio: str = Form(...),
    pedido_idpedido: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.servicios
                    SET codigoservicio = :codigo, descripcionservicio = :desc, pedido_idpedido = :pedido
                    WHERE idservicios = :id
                """),
                {"codigo": codigoservicio, "desc": descripcionservicio, "pedido": pedido_idpedido, "id": srv_id},
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Servicio actualizado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/servicios/eliminar/{srv_id}")
async def eliminar_servicio(srv_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.servicios WHERE idservicios = :id"), {"id": srv_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Servicio eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  TIPO REPARACIÓN — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/tiporeparacion/nuevo")
async def crear_tiporeparacion(
    access_token: str = Cookie(None),
    codigotiporeparacion: str = Form(...),
    descripciontiporeparacion: str = Form(...),
    servicios_idservicios: int = Form(...),
    pedido_idpedido: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.tiporeparacion
                        (codigotiporeparacion, descripciontiporeparacion,
                         servicios_idservicios, pedido_idpedido)
                    VALUES (:codigo, :desc, :srv, :pedido)
                """),
                {
                    "codigo":  codigotiporeparacion,
                    "desc":    descripciontiporeparacion,
                    "srv":     servicios_idservicios,
                    "pedido":  pedido_idpedido,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo de reparación creado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/tiporeparacion/editar/{tr_id}")
async def editar_tiporeparacion(
    tr_id: int,
    access_token: str = Cookie(None),
    codigotiporeparacion: str = Form(...),
    descripciontiporeparacion: str = Form(...),
    servicios_idservicios: int = Form(...),
    pedido_idpedido: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.tiporeparacion
                    SET codigotiporeparacion = :codigo,
                        descripciontiporeparacion = :desc,
                        servicios_idservicios = :srv,
                        pedido_idpedido = :pedido
                    WHERE idtiporeparacion = :id
                """),
                {
                    "codigo":  codigotiporeparacion,
                    "desc":    descripciontiporeparacion,
                    "srv":     servicios_idservicios,
                    "pedido":  pedido_idpedido,
                    "id":      tr_id,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo de reparación actualizado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/tiporeparacion/eliminar/{tr_id}")
async def eliminar_tiporeparacion(tr_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.tiporeparacion WHERE idtiporeparacion = :id"), {"id": tr_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Tipo de reparación eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  PEDIDOS — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/pedidos/nuevo")
async def crear_pedido(
    access_token: str = Cookie(None),
    codigopedido: str = Form(...),
    fecha: str = Form(...),
    fecha_cita: str = Form(...),
    metodopago_idmetodopago: int = Form(...),
    estado: str = Form("pendiente"),
    descripcion: Optional[str] = Form(None),
    oficinas_idoficinas: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        oficina_val = int(oficinas_idoficinas) if oficinas_idoficinas else None
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.pedido
                        (codigopedido, fecha, fecha_cita, metodopago_idmetodopago,
                         estado, descripcion, oficinas_idoficinas)
                    VALUES (:codigo, :fecha, CAST(:fcita AS timestamptz),
                            :mp, :estado, :desc, :oficina)
                """),
                {
                    "codigo":  codigopedido,
                    "fecha":   fecha,
                    "fcita":   fecha_cita,
                    "mp":      metodopago_idmetodopago,
                    "estado":  estado,
                    "desc":    descripcion,
                    "oficina": oficina_val,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Pedido creado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/pedidos/editar/{ped_id}")
async def editar_pedido(
    ped_id: int,
    access_token: str = Cookie(None),
    codigopedido: str = Form(...),
    fecha: str = Form(...),
    fecha_cita: str = Form(...),
    metodopago_idmetodopago: int = Form(...),
    estado: str = Form("pendiente"),
    descripcion: Optional[str] = Form(None),
    oficinas_idoficinas: Optional[str] = Form(None),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        oficina_val = int(oficinas_idoficinas) if oficinas_idoficinas else None
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.pedido
                    SET codigopedido = :codigo,
                        fecha = :fecha,
                        fecha_cita = CAST(:fcita AS timestamptz),
                        metodopago_idmetodopago = :mp,
                        estado = :estado,
                        descripcion = :desc,
                        oficinas_idoficinas = :oficina
                    WHERE idpedido = :id
                """),
                {
                    "codigo":  codigopedido,
                    "fecha":   fecha,
                    "fcita":   fecha_cita,
                    "mp":      metodopago_idmetodopago,
                    "estado":  estado,
                    "desc":    descripcion,
                    "oficina": oficina_val,
                    "id":      ped_id,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Pedido actualizado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/pedidos/eliminar/{ped_id}")
async def eliminar_pedido(ped_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.pedido WHERE idpedido = :id"), {"id": ped_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Pedido eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  PRODUCTOS — CRUD completo
# ══════════════════════════════════════════════════════════════════

@app.post("/config/productos/nuevo")
async def crear_producto(
    access_token: str = Cookie(None),
    codigoproductos: str = Form(...),
    descripcionproductos: str = Form(...),
    productoprecio_idproductoprecio: int = Form(...),
    pedido_idpedido: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO dmi.productos
                        (codigoproductos, descripcionproductos,
                         productoprecio_idproductoprecio, pedido_idpedido)
                    VALUES (:codigo, :desc, :precio, :pedido)
                """),
                {
                    "codigo":  codigoproductos,
                    "desc":    descripcionproductos,
                    "precio":  productoprecio_idproductoprecio,
                    "pedido":  pedido_idpedido,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Producto creado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/productos/editar/{prod_id}")
async def editar_producto(
    prod_id: int,
    access_token: str = Cookie(None),
    codigoproductos: str = Form(...),
    descripcionproductos: str = Form(...),
    productoprecio_idproductoprecio: int = Form(...),
    pedido_idpedido: int = Form(...),
):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE dmi.productos
                    SET codigoproductos = :codigo,
                        descripcionproductos = :desc,
                        productoprecio_idproductoprecio = :precio,
                        pedido_idpedido = :pedido
                    WHERE idproductos = :id
                """),
                {
                    "codigo":  codigoproductos,
                    "desc":    descripcionproductos,
                    "precio":  productoprecio_idproductoprecio,
                    "pedido":  pedido_idpedido,
                    "id":      prod_id,
                },
            )
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Producto actualizado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


@app.post("/config/productos/eliminar/{prod_id}")
async def eliminar_producto(prod_id: int, access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return redirigir_sin_permiso("/configuracion")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.productos WHERE idproductos = :id"), {"id": prod_id})
            conn.commit()
        return RedirectResponse(url="/configuracion?success=Producto eliminado", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/configuracion?error={e}", status_code=302)


# ══════════════════════════════════════════════════════════════════
#  APIs JSON
# ══════════════════════════════════════════════════════════════════

@app.get("/api/ciudades")
async def api_ciudades():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.ciudades ORDER BY idciudades")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/metodospago")
async def api_metodospago():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.metodopago ORDER BY idmetodopago")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/oficinas")
async def api_oficinas():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.oficinas")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/pedidos")
async def api_pedidos():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.pedido ORDER BY idpedido DESC")).mappings().fetchall()
            result = []
            for r in data:
                row = dict(r)
                if row.get("fecha_cita"):
                    row["fecha_cita"] = str(row["fecha_cita"])
                result.append(row)
            return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/productos")
async def api_productos():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.productos")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/servicios")
async def api_servicios():
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.servicios")).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ==================== LOGIN REACT ====================
@app.post("/login-react")
async def login_react(request: Request):
    try:
        body = await request.json()
        email = body.get("email", "").strip()
        password = body.get("password", "")
        if not email or not password:
            return JSONResponse({"error": "Email y contrasena son requeridos"}, status_code=400)
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not res.user:
            return JSONResponse({"error": "Credenciales incorrectas"}, status_code=401)
        user_res = supabase.schema("dmi").table("usuarios").select("usuarionombre, rol").eq("id", res.user.id).execute()
        rol = "usuario"
        nombre = email
        if user_res.data:
            rol = user_res.data[0].get("rol", "usuario")
            nombre = user_res.data[0].get("usuarionombre", email)
        return JSONResponse({"token": res.session.access_token, "role": rol, "email": email, "nombre": nombre})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== REGISTRO REACT ====================
@app.post("/registro-react")
async def registro_react(request: Request):
    try:
        body = await request.json()
        email = body.get("email", "").strip()
        password = body.get("password", "")
        res = supabase.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return JSONResponse({"error": "No se pudo registrar el usuario"}, status_code=400)
        supabase.schema("dmi").table("usuarios").insert({
            "id": res.user.id,
            "usuarionombre": body.get("usuarionombre", ""),
            "nombre": body.get("nombre", ""),
            "apellidos": body.get("apellidos", ""),
            "email": email,
            "documento": body.get("documento", ""),
            "tipodedocumento": body.get("tipodedocumento", ""),
            "fechadenacimiento": body.get("fechadenacimiento", ""),
            "telefono": body.get("telefono", ""),
            "rol": "usuario",
        }).execute()
        return JSONResponse({"success": True, "message": "Usuario registrado correctamente"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== STATS ADMIN ====================
@app.get("/admin/stats")
async def admin_stats(access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    try:
        with engine.connect() as conn:
            citas     = conn.execute(text("SELECT COUNT(*) FROM dmi.citas WHERE estado='pendiente'")).scalar()
            vehiculos = conn.execute(text("SELECT COUNT(*) FROM dmi.vehiculos")).scalar()
            usuarios  = conn.execute(text("SELECT COUNT(*) FROM dmi.usuarios")).scalar()
        return JSONResponse({"citas_pendientes": citas, "total_vehiculos": vehiculos, "total_usuarios": usuarios})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== EJECUCION ====================

# ==================== LOGIN REACT ====================
@app.post("/login-react")
async def login_react(request: Request):
    try:
        body = await request.json()
        email = body.get("email", "").strip()
        password = body.get("password", "")
        if not email or not password:
            return JSONResponse({"error": "Email y contrasena requeridos"}, status_code=400)
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not res.user:
            return JSONResponse({"error": "Credenciales incorrectas"}, status_code=401)
        user_res = supabase.schema("dmi").table("usuarios").select("usuarionombre, rol").eq("id", res.user.id).execute()
        rol = "usuario"
        nombre = email
        if user_res.data:
            rol = user_res.data[0].get("rol", "usuario")
            nombre = user_res.data[0].get("usuarionombre", email)
        return JSONResponse({"token": res.session.access_token, "role": rol, "email": email, "nombre": nombre})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== REGISTRO REACT ====================
@app.post("/registro-react")
async def registro_react(request: Request):
    try:
        body = await request.json()
        email = body.get("email", "").strip()
        password = body.get("password", "")
        res = supabase.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return JSONResponse({"error": "No se pudo registrar"}, status_code=400)
        supabase.schema("dmi").table("usuarios").insert({
            "id": res.user.id,
            "usuarionombre": body.get("usuarionombre", ""),
            "nombre": body.get("nombre", ""),
            "apellidos": body.get("apellidos", ""),
            "email": email,
            "documento": body.get("documento", ""),
            "tipodedocumento": body.get("tipodedocumento", ""),
            "fechadenacimiento": body.get("fechadenacimiento", ""),
            "telefono": body.get("telefono", ""),
            "rol": "usuario",
        }).execute()
        return JSONResponse({"success": True, "message": "Usuario registrado correctamente"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== STATS ADMIN ====================
@app.get("/admin/stats")
async def admin_stats(access_token: str = Cookie(None)):
    usuario = obtener_usuario(access_token)
    if not es_admin(usuario):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    try:
        with engine.connect() as conn:
            citas     = conn.execute(text("SELECT COUNT(*) FROM dmi.citas WHERE estado='pendiente'")).scalar()
            vehiculos = conn.execute(text("SELECT COUNT(*) FROM dmi.vehiculos")).scalar()
            usuarios  = conn.execute(text("SELECT COUNT(*) FROM dmi.usuarios")).scalar()
        return JSONResponse({"citas_pendientes": citas, "total_vehiculos": vehiculos, "total_usuarios": usuarios})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

#======================= CORS =========================


@app.get("/api/tipovehiculos")
async def api_tipovehiculos():
    try:
        with engine.connect() as conn:
            data = conn.execute(
                text("SELECT idtipovehiculos, codigotipovehiculos, vehiculo FROM dmi.tipovehiculos ORDER BY idtipovehiculos")
            ).mappings().fetchall()
            return JSONResponse([dict(r) for r in data])
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== EJECUCION ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8800, reload=True)
