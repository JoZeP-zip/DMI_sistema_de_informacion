from fastapi import FastAPI, Form, Request, Cookie, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
import os
import jwt

load_dotenv()

# ==================== CONFIGURACIÓN ====================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://...")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://....supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "yJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBqZ2xkaXhka2F2YWZteG93dWp0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE2MDMxOTAsImV4cCI6MjA4NzE3OTE5MH0.VsdOpz44v2pVYb94ESnw-nmLe7OmaXsm_mMfU-FEKAA")
ADMIN_SECRET  = os.getenv("ADMIN_SECRET", "lolcito")  

engine = create_engine(DATABASE_URL)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://musical-bassoon-wrx6qgr9gvp9f7v-3000.app.github.dev",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.cache = None

class LoginJSON(BaseModel):
    email: str
    password: str

# ==================== OBTENER USUARIO ====================
def obtener_usuario(access_token: Optional[str]) -> Optional[dict]:
    """Decodifica el JWT y retorna dict con id, nombre y rol, o None si falla."""
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


# ==================== HELPERS DE PERMISOS ====================  ← NUEVO BLOQUE

def es_admin(usuario: Optional[dict]) -> bool:
    """Retorna True si el usuario autenticado tiene rol admin."""
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



# ==================== LOGIN PARA REACT ====================
@app.post("/login-react")
async def login_react(data: LoginJSON):
    try:
        res = supabase.auth.sign_in_with_password({"email": data.email, "password": data.password})
        if not res.user:
            return JSONResponse({"error": "Credenciales incorrectas"})

        # Obtener rol del usuario
        user_res = (
            supabase.schema("dmi")
            .table("usuarios")
            .select("usuarionombre, rol")
            .eq("id", res.user.id)
            .execute()
        )
        rol = user_res.data[0]["rol"] if user_res.data else "usuario"

        return JSONResponse({
            "email": data.email,
            "role": rol,
            "token": res.session.access_token
        })
    except Exception as e:
        return JSONResponse({"error": str(e)})

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


# ==================== PROMOVER A ADMIN (protegido por clave) ====================  

@app.post("/admin/promover")
async def promover_admin(
    usuario_id: str = Form(...),   
    secret: str = Form(...),       
    access_token: str = Cookie(None),
):
    """
    Permite a un admin existente (o al primer setup) promover a otro usuario.
    Requiere la ADMIN_SECRET definida en .env para evitar uso no autorizado.
    """
    if secret != ADMIN_SECRET:
        return RedirectResponse(url="/?error=Clave secreta incorrecta", status_code=302)

    try:
        # Actualizar en la tabla dmi.usuarios
        supabase.schema("dmi").table("usuarios") \
            .update({"rol": "admin"}) \
            .eq("id", usuario_id) \
            .execute()

        return RedirectResponse(url="/?success=Usuario promovido a administrador", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== CREAR VEHÍCULO   ====================
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
    # ← Cualquier usuario autenticado puede crear vehículos (permiso permitido)

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
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== FORMULARIO EDITAR ====================
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

# ==================== STATS PARA EL DASHBOARD ====================
@app.get("/admin/stats")
async def admin_stats(authorization: str = Header(None)):
    if not authorization:
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        user_res = supabase.schema("dmi").table("usuarios").select("rol").eq("id", user_id).execute()
        rol = user_res.data[0]["rol"] if user_res.data else "usuario"
        
        if rol != "admin":
            return JSONResponse({"error": "No autorizado"}, status_code=403)
    except:
        return JSONResponse({"error": "Token inválido"}, status_code=403)

    try:
        with engine.connect() as conn:
            citas_pendientes = conn.execute(text("SELECT COUNT(*) FROM dmi.citas WHERE estado = 'pendiente'")).scalar()
            total_vehiculos = conn.execute(text("SELECT COUNT(*) FROM dmi.vehiculos")).scalar()
            total_usuarios = conn.execute(text("SELECT COUNT(*) FROM dmi.usuarios")).scalar()

        return JSONResponse({
            "citas_pendientes": citas_pendientes,
            "total_vehiculos": total_vehiculos,
            "total_usuarios": total_usuarios,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ==================== EJECUCIÓN ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8800, reload=True)