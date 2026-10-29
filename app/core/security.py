from datetime import datetime, timedelta, timezone  # 1. timedelta corregido

from app.core.config import Algoritmo, llave_secreta, token_expiracion
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext

# Bcrypt: estándar para guardar contraseñas. Transforma "123456" en un revoltijo
# que no se puede revertir.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
## Extrae el token de la cabecera "Authorization: Bearer ..." de la petición.
autenticacion = OAuth2PasswordBearer(tokenUrl="/usuarios/login")
maximo_contraseña = 72


# 3. Se usa -> en lugar de =>
def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > maximo_contraseña:
        raise ValueError("Error, la contraseña no puede tener más de 72 bytes.")
    return pwd_context.hash(password)


def verificar_contraseña(contraseña_ingresada: str, password_hashed: str) -> bool:
    # "Traduce cada una de estas letras a su número exacto según la tabla UTF-8 y entrégame una secuencia pura de bytes (números del 0 al 255. validamos si es mayor al maximo de caracteres por si pone ñ (tiene 2 caracteres)
    if len(contraseña_ingresada.encode("utf-8")) > maximo_contraseña:
        return False
    try:
        # Passlib verifica de forma segura si coinciden
        return pwd_context.verify(contraseña_ingresada, password_hashed)
    except ValueError:
        return False


def crear_token(datos: dict, tiempo_expiracion: timedelta | None = None) -> str:
    expiracion = datetime.now(timezone.utc) + (
        tiempo_expiracion or timedelta(minutes=token_expiracion)
    )
    payload = {**datos, "exp": expiracion}
    return jwt.encode(payload, llave_secreta, algorithm=Algoritmo) 

def decodificar_token(token: str = Depends(autenticacion)) -> dict:
    try:
        contenido = jwt.decode(
            token,
            llave_secreta,
            algorithms=[Algoritmo],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expiracion vencida.",
        )

    sub = contenido.get("sub")
    # es una función interna de Python que sirve para verificar si un dato es del tipo que esperas.
    if not isinstance(sub, str) or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas"
        )

    token_version = contenido.get("token_version", 0)
    # y que la versión del token  sea un número real, protegiendo a tu API contra manipulaciones maliciosas.
    # Es decir, para Python, un booleano es considerado un número entero.
    if not isinstance(token_version, int) or isinstance(token_version, bool):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
        # El número oficial: El único token válido es el que coincida exactamente con el número que el usuario tiene guardado en la base de datos en ese preciso instante.

        # El número viejo: Cualquier token que traiga un número menor al que está en la base de datos (por ejemplo, traer un 0 cuando la base de datos ya va por el 1) se considera antiguo, obsoleto y se rechaza de inmediato.

    return {"sub": sub, "token_version": token_version}

    # Estamos obligando a que token_version sea exclusivamente un número entero real y prohibiendo que se cuelen textos, decimales o booleanos maliciosos


# Depende de autenticacion, porque va y trae el token de la cabecera sin el "bearer".
# Necesitamos el token para hacer esta tarea.
def verificar_token(token: str = Depends(autenticacion)) -> str:
    return decodificar_token(token)["sub"]