from fastapi import FastAPI, Form, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase_auth.errors import AuthApiError
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
from fastapi import Cookie
import os
import jwt

load_dotenv()


DATABASE_URL = "postgresql://postgres.pjgldixdkavafmxowujt:camiloide1606@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
SUPABASE_URL = "https://pjgldixdkavafmxowujt.supabase.co"
SUPABASE_KEY = "sb_publishable_mt-owoQ2cqmfkgBS_AAl6Q_9yhi38Pj"

engine = create_engine(DATABASE_URL)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ==============================
# HOME (LISTAR VEHÍCULOS + TIPOS)
# ==============================
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    data = []
    tipos = []
    error_msg = None

    try:
        with engine.connect() as connection:
            # Vehículos
            result = connection.execute(
                text("SELECT * FROM dmi.vehiculos LIMIT 20")
            )
            data = result.fetchall()

            # Tipos de vehículo (para el select)
            result_tipos = connection.execute(
                text("SELECT idtipovehiculos, codigotipovehiculos FROM dmi.tipovehiculos")
            )
            tipos = result_tipos.fetchall()

    except Exception as e:
        error_msg = str(e)
        print("Error en consulta:", error_msg)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data,
            "tipos": tipos,   # 👈 enviamos los tipos al HTML
            "error": error_msg,
        }
    )


# ==============================
# INSERTAR VEHÍCULO
# ==============================
@app.post("/vehiculo/nuevo", response_class=HTMLResponse)
async def crear_vehiculo(
    request: Request,
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
    try:
        with engine.connect() as connection:
            connection.execute(
                text("""
                    INSERT INTO dmi.vehiculos (
                        codigovehiculo,
                        descripcionvehiculo,
                        motor,
                        cantidad_asientos,
                        placa,
                        capacidad,
                        marca,
                        tipovehiculos_idtipovehiculos,
                        modelo
                    ) VALUES (
                        :codigovehiculo,
                        :descripcionvehiculo,
                        :motor,
                        :cantidad_asientos,
                        :placa,
                        :capacidad,
                        :marca,
                        :tipovehiculos_idtipovehiculos,
                        :modelo
                    )
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
                }
            )
            connection.commit()

    except Exception as e:
        print("Error al insertar vehículo:", str(e))

    return read_root(request)

# ==============================
# registro usuario
# ==============================

from fastapi import Form, HTTPException
from supabase import AuthApiError

@app.post("/registro")
def registro(
    email: str = Form(...),
    password: str = Form(...),
    nombre: str = Form(...),
    apellidos: str = Form(...),
    documento: str = Form(...),
    telefono: str = Form(...),
    usuarionombre: str = Form(...)
):
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
    except AuthApiError as e:
        msg = str(e).lower()
        if "user already registered" in msg:
            raise HTTPException(status_code=422, detail="El email ya está registrado")
        elif "rate limit" in msg:
            raise HTTPException(status_code=429, detail="Has superado el límite de registros.")
        else:
            raise HTTPException(status_code=400, detail=str(e))

    if res.user is None:
        raise HTTPException(status_code=400, detail="No se pudo registrar")

    user_id = res.user.id

    supabase.schema("dmi").table("usuarios").insert({
        "id": user_id,
        "usuarionombre": usuarionombre,
        "nombre": nombre,
        "apellidos": apellidos,
        "email": email,
        "documento": documento,
        "telefono": telefono

    }).execute()

    

    return {"mensaje": "Usuario registrado", "user_id": user_id}

    


# ==============================
# login
# ==============================

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    if res.user is None:
        return {"error": "Credenciales incorrectas"}

    return {"access_token": res.session.access_token, "user_id": res.user.id}




# ==============================
# usuraio
# ==============================

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, access_token: str = Cookie(None)):
    data = []
    tipos = []
    error_msg = None
    usuario = None

    try:
        # 🔐 Obtener usuario desde token
        if access_token:
            payload = jwt.decode(access_token, options={"verify_signature": False})
            user_id = payload["sub"]

            user_res = supabase.schema("dmi").table("usuarios")\
                .select("usuarionombre")\
                .eq("id", user_id)\
                .execute()

            if user_res.data:
                usuario = user_res.data[0]["usuarionombre"]

        # 🚗 Vehículos
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM dmi.vehiculos LIMIT 20")
            )
            data = result.fetchall()

            result_tipos = connection.execute(
                text("SELECT idtipovehiculos, codigotipovehiculos FROM dmi.tipovehiculos")
            )
            tipos = result_tipos.fetchall()

    except Exception as e:
        error_msg = str(e)
        print("Error:", error_msg)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data,
            "tipos": tipos,
            "usuario": usuario,
            "error": error_msg,
        }
    )

# ==============================
# autentificacion
# ==============================

from fastapi import Header, HTTPException

def validar_token(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]
        import jwt
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload["sub"]  # user id uuid
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")
    






@app.get("/registro", response_class=HTMLResponse)
def mostrar_registro(request: Request):
    return templates.TemplateResponse("registro.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def mostrar_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})








from fastapi.responses import RedirectResponse

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    if res.user is None:
        return {"error": "Credenciales incorrectas"}

    response = RedirectResponse(url="/vehiculos", status_code=302)
    response.set_cookie(key="access_token", value=res.session.access_token)
    return response










@app.post("/vehiculo/nuevo")
async def crear_vehiculo(
    request: Request,
    codigovehiculo: str = Form(...),
    placa: str = Form(...),
    marca: str = Form(...),
    tipovehiculos_idtipovehiculos: str = Form(...),
    descripcionvehiculo: Optional[str] = Form(None),
    motor: Optional[str] = Form(None),
    cantidad_asientos: Optional[str] = Form(None),
    capacidad: Optional[str] = Form(None),
    modelo: Optional[str] = Form(None),
    authorization: str = Header(...)
):
    user_id = validar_token(authorization)

    # Aquí puedes usar user_id si quieres relacionar vehículo con usuario

    with engine.connect() as connection:
        connection.execute(
            text("""INSERT INTO dmi.vehiculos (
                codigovehiculo,
                descripcionvehiculo,
                motor,
                cantidad_asientos,
                placa,
                capacidad,
                marca,
                tipovehiculos_idtipovehiculos,
                modelo
            ) VALUES (
                :codigovehiculo,
                :descripcionvehiculo,
                :motor,
                :cantidad_asientos,
                :placa,
                :capacidad,
                :marca,
                :tipovehiculos_idtipovehiculos,
                :modelo
            )"""),
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
            }
        )
        connection.commit()

    return await read_root(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)