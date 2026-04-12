from fastapi import FastAPI, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
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
DATABASE_URL = "postgresql://postgres.pjgldixdkavafmxowujt:camiloide1606@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
SUPABASE_URL = "https://pjgldixdkavafmxowujt.supabase.co"
SUPABASE_KEY = "sb_publishable_mt-owoQ2cqmfkgBS_AAl6Q_9yhi38Pj"

engine = create_engine(DATABASE_URL)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")
templates.env.cache = None  

# ==================== PÁGINA PRINCIPAL ====================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: str = Cookie(None)):
    data = []
    tipos = []
    usuario = None
    success_msg = request.query_params.get("success")
    error_msg = request.query_params.get("error")

    if access_token:
        try:
            payload = jwt.decode(access_token, options={"verify_signature": False})
            user_id = payload["sub"]
            user_res = supabase.schema("dmi").table("usuarios")\
                .select("usuarionombre").eq("id", user_id).execute()
            if user_res.data:
                usuario = user_res.data[0]["usuarionombre"]
        except:
            pass

    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.vehiculos LIMIT 20")).fetchall()
            tipos = conn.execute(
                text("SELECT idtipovehiculos, codigotipovehiculos FROM dmi.tipovehiculos")
            ).fetchall()
    except Exception as e:
        error_msg = str(e)
        print("Error en consulta:", error_msg)

    

    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={
        "data": data,
        "tipos": tipos,
        "usuario": usuario,
        "success_msg": success_msg,
        "error": error_msg,
        "vehicle_to_edit": None
    }
)


# ==================== REGISTRO USUARIO ====================
@app.post("/registro")
async def registro(
    email: str = Form(...), password: str = Form(...),
    nombre: str = Form(...), apellidos: str = Form(...),
    documento: str = Form(...), telefono: str = Form(...),
    usuarionombre: str = Form(...)
):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return RedirectResponse(url="/?error=No se pudo registrar", status_code=302)

        supabase.schema("dmi").table("usuarios").insert({
            "id": res.user.id,
            "usuarionombre": usuarionombre,
            "nombre": nombre,
            "apellidos": apellidos,
            "email": email,
            "documento": documento,
            "telefono": telefono
        }).execute()

        return RedirectResponse(url="/?success=Usuario registrado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== LOGIN ====================
@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not res.user:
            return RedirectResponse(url="/?error=Credenciales incorrectas", status_code=302)

        response = RedirectResponse(url="/?success=Inicio de sesión exitoso", status_code=302)
        response.set_cookie(key="access_token", value=res.session.access_token, httponly=True)
        return response
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== CREAR VEHÍCULO ====================
@app.post("/vehiculo/nuevo")
async def crear_vehiculo(
    request: Request,
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
    if not access_token:
        return RedirectResponse(url="/?error=Debes iniciar sesión", status_code=302)

    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO dmi.vehiculos 
                (codigovehiculo, descripcionvehiculo, motor, cantidad_asientos, placa, 
                 capacidad, marca, tipovehiculos_idtipovehiculos, modelo)
                VALUES (:codigovehiculo, :descripcionvehiculo, :motor, :cantidad_asientos, 
                        :placa, :capacidad, :marca, :tipovehiculos_idtipovehiculos, :modelo)
            """), {**locals()})
            conn.commit()
        return RedirectResponse(url="/?success=Vehículo creado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== FORMULARIO EDITAR ====================
@app.get("/vehiculo/editar/{vehiculo_id}")
async def editar_vehiculo_form(request: Request, vehiculo_id: int, access_token: str = Cookie(None)):
    vehicle_to_edit = None
    data = []
    tipos = []
    usuario = None

    # Datos del usuario
    if access_token:
        try:
            payload = jwt.decode(access_token, options={"verify_signature": False})
            user_id = payload["sub"]
            user_res = supabase.schema("dmi").table("usuarios")\
                .select("usuarionombre").eq("id", user_id).execute()
            if user_res.data:
                usuario = user_res.data[0]["usuarionombre"]
        except:
            pass

    # Datos para tabla + vehículo a editar
    try:
        with engine.connect() as conn:
            data = conn.execute(text("SELECT * FROM dmi.vehiculos LIMIT 20")).fetchall()
            tipos = conn.execute(
                text("SELECT idtipovehiculos, codigotipovehiculos FROM dmi.tipovehiculos")
            ).fetchall()
            result = conn.execute(
                text("SELECT * FROM dmi.vehiculos WHERE idvehiculo = :id"),
                {"id": vehiculo_id}
            )
            vehicle_to_edit = result.fetchone()
    except Exception as e:
        print("Error:", e)

    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={
            "request": request,
            "data": data,
            "tipos": tipos,
            "usuario": usuario,
            "success_msg": None,
            "error": None,
            "vehicle_to_edit": vehicle_to_edit
        }
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
    if not access_token:
        return RedirectResponse(url="/?error=Debes iniciar sesión", status_code=302)

    try:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE dmi.vehiculos SET
                    codigovehiculo = :codigovehiculo,
                    descripcionvehiculo = :descripcionvehiculo,
                    motor = :motor,
                    cantidad_asientos = :cantidad_asientos,
                    placa = :placa,
                    capacidad = :capacidad,
                    marca = :marca,
                    tipovehiculos_idtipovehiculos = :tipovehiculos_idtipovehiculos,
                    modelo = :modelo
                WHERE idvehiculo = :idvehiculo
            """), {
                "codigovehiculo": codigovehiculo, "descripcionvehiculo": descripcionvehiculo,
                "motor": motor, "cantidad_asientos": cantidad_asientos, "placa": placa,
                "capacidad": capacidad, "marca": marca,
                "tipovehiculos_idtipovehiculos": tipovehiculos_idtipovehiculos,
                "modelo": modelo, "idvehiculo": vehiculo_id
            })
            conn.commit()
        return RedirectResponse(url="/?success=Vehículo actualizado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== ELIMINAR VEHÍCULO ====================
@app.post("/vehiculo/eliminar/{vehiculo_id}")
async def eliminar_vehiculo(vehiculo_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse(url="/?error=Debes iniciar sesión", status_code=302)

    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM dmi.vehiculos WHERE idvehiculo = :id"), {"id": vehiculo_id})
            conn.commit()
        return RedirectResponse(url="/?success=Vehículo eliminado correctamente", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=302)


# ==================== EJECUCIÓN ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8800, reload=True)

    