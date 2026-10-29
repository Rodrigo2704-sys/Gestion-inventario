from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.roles import rol
from app.core.security import decodificar_token
from app.models.usuarios import UsuariosModel


def obtener_usuario_actual(
    claims: dict = Depends(decodificar_token),
    db: Session = Depends(get_db),
) -> UsuariosModel:
    try:
        # Porque tu base de datos (MySQL) y tu modelo de SQLAlchemy esperan un número entero (int) para hacer la búsqueda del usuario.
        usuario_id = int(claims["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # osea te trae todo lo de los dos models de acuerdo al id del usuario que etsamos buscando, gracias al puente de relationship
    usuario = (
        db.query(UsuariosModel)
        .options(
            joinedload(UsuariosModel.rol)
        )  # 👈 Aquí le dices: "Tráete también el rol de una vez"
        .filter(UsuariosModel.id == usuario_id)
        .first()
    )

    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
            headers={
                "WWW-Authenticate": "Bearer"
            },  # Si quieres volver a intentarlo, tienes que usar el esquema de seguridad tipo Bearer" (Es decir, enviando un token JWT válido en el encabezado
        )

    if (
        claims["token_version"] != usuario.token_version
    ):  # : Contiene la información oficial que el token "afirma" sobre el usuario (por ejemplo, su ID sub, su rol y su token_version). Cuando tu API lee el token, los claims son simplemente los datos que extrae para saber de quién se trata y verificar su información. // pero en vez de claims se puede otra cosa, esque esta en diccionario
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesion expirada. Inicia sesion de nuevo.",
            headers={
                "WWW-Authenticate": "Bearer"
            },  # Es una etiqueta técnica de aviso que viaja en la respuesta HTTP hacia el navegador o la aplicación del cliente.
        )
    return usuario


def solo_administradores(
    usuario_actual: UsuariosModel = Depends(obtener_usuario_actual),
) -> UsuariosModel:
    if usuario_actual.rol_id != rol.Administrador:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acceso denegado. Se requieren privilegios de administrador.",
        )
    return usuario_actual

