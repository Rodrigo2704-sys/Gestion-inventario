import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from app.core.security import crear_token
from app.core.database import get_db
from app.core.dependencias import rol, obtener_usuario_actual, solo_administradores
from app.core.limiter import limiter
from app.core.security import crear_token
from app.crud.verificacion import PROPOSITO_VERIFICAR
from app.crud.usuarios import (
    CorreoYaRegistrado,
    RolInvalido,
    iniciar_sesion,
    registrar_usuario,
    actualizar_rol_usuario_crud,
    obtener_usuario_por_correo,
    obtener_usuario_por_id,
    obtener_todos_los_usuarios,
    actualizar_usuario as actualizar_usuario_crud,
    cambiar_password,
    eliminar_usuario
)

from app.schemas.usuarios import (
    CambiarPassword,
    ActualizarUsuario,
    SalidaUsuario,
    EntradaRegistro,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

CAMPOS_PROHIBIDOS = {"id", "rol_id"}
CAMPOS_SOLO_ADMIN = {"activo"}


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
): 
    usuario = iniciar_sesion(db, correo=form_data.username, contraseña_ingresada=form_data.password)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos."
        )

    if not usuario.correo_verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes verificar tu correo electronico antes de iniciar sesion."
        )

    nombre_rol = usuario.rol.Nombre

    acceso_token = crear_token(
        datos={"sub": str(usuario.id), "rol": nombre_rol, "token_version": usuario.token_version}
    )

    return {
        "access_token": acceso_token,
        "token_type": "bearer",
        "nombre": usuario.Nombre,
        "rol": nombre_rol,
    }


@router.post("/registrar", response_model=SalidaUsuario, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def crear_usuario(
    request: Request,
    datos: EntradaRegistro,
    tareas: BackgroundTasks, # Cuando un usuario le da clic en "Registrarse", el servidor guarda el usuario en la base de datos y le responde inmediatamente con un éxito 201 Created. El usuario no tiene que quedarse esperando 2 o 3 segundos con la pantalla congelada mientras FastAPI se conecta al servidor de correo SMTP para mandar el mensaje. El correo se envía "por detrás" mientras el usuario ya está viendo la pantalla de éxito.
    db: Session = Depends(get_db)
):
    if obtener_usuario_por_correo(db, correo=datos.correo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya se encuentra registrado."
        )

    try:
        nuevo_usuario = registrar_usuario(db, usuario=datos)
    except CorreoYaRegistrado as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error)
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error de la BD al registrar el usuario.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrio un error inesperado en la base de datos al registrar el usuario."
        )
    
    if not nuevo_usuario:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar el usuario",
        )

    # 2. Si el usuario SÍ se creó, continuamos fuera del "if":
    # Generamos y enviamos el código de verificación por correo
    # emitir_codigo(db, nuevo_usuario, PROPOSITO_VERIFICAR, tareas)

    # 3. Refrescamos la instancia para asegurarnos de tener todos los campos creados por la BD (como ID, fechas)
    db.refresh(nuevo_usuario)

    # 4. Forzamos la carga de la relación del rol para que Pydantic pueda serializarlo
    _ = nuevo_usuario.rol

    # 5. Retornamos la respuesta con el usuario registrado
    return nuevo_usuario


@router.patch("/{usuario_id}/cambiar_rol", response_model=SalidaUsuario)
def cambiar_rol_endpoint(
    usuario_id: int,
    nuevo_rol_id: int,
    db: Session = Depends(get_db),
    admin = Depends(solo_administradores),
):
    if admin.id == usuario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error, no puedes cambiar tu propio rol."
        )

    try:
        usuario_actualizado = actualizar_rol_usuario_crud(db, usuario_id, nuevo_rol_id)
    except RolInvalido as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error en la BD al cambiar rol al usuario.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la BD al intentar cambiar el rol del usuario."
        )

    if not usuario_actualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    return usuario_actualizado


@router.get("/buscar/correo", response_model=SalidaUsuario)
def buscar_usuario_correo_endpoint(
    correo: str,
    db: Session = Depends(get_db),
    admin = Depends(solo_administradores)
):
    usuario = obtener_usuario_por_correo(db, correo)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro el usuario."
        )
    return usuario


@router.get("/{usuario_id}/buscar/id", response_model=SalidaUsuario)
def buscar_usuario_id(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(solo_administradores)
):
    usuario_encontrado_id = obtener_usuario_por_id(db, usuario_id)
    if not usuario_encontrado_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    return usuario_encontrado_id


@router.get("/obtener/usuarios", response_model=List[SalidaUsuario]) # List porque son varios objetos que vamos a obtener
def obtener_todos(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    admin = Depends(solo_administradores)
):
    return obtener_todos_los_usuarios(db, skip=skip, limit=limit)


@router.patch("/{usuario_id}/actualizar_usuario", response_model=SalidaUsuario)
def actualizar_usuario_endpoint(
    usuario_id: int,
    datos: ActualizarUsuario,
    db: Session = Depends(get_db),
    admin = Depends(solo_administradores)
):
    if hasattr(datos, "model_dump"):  # Pydantic v2
        datos_dict = datos.model_dump(exclude_unset=True)
    else:  
        datos_dict = datos.dict(exclude_unset=True)

    if not datos_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se envio ningun campo a actualizar."
        )

    # Un admin no puede desactivar su propia cuenta por accidente.
    if "activo" in datos_dict and admin.id == usuario_id and datos_dict["activo"] is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta.",
        )

    try:
        usuario_actualizado = actualizar_usuario_crud(
            db=db, usuario_id=usuario_id, datos_actualizacion=datos_dict
        )
    # CORRECCIÓN: antes se detectaba el duplicado con _es_duplicado(); ahora el CRUD lanza
    # CorreoYaRegistrado y el router solo lo traduce a 409.
    except CorreoYaRegistrado as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error de BD al actualizar usuario %s", usuario_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la base de datos al actualizar el usuario.",
        )

    if not usuario_actualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    return usuario_actualizado


@router.post("/cambiar-contrasena")
@limiter.limit("5/minute")
def cambiar_clave_usuario(
    request: Request,
    datos: CambiarPassword,
    db: Session = Depends(get_db),
    autenticado = Depends(obtener_usuario_actual),
):
    try:
        cambiar = cambiar_password(db, autenticado, datos.password_actual, datos.password_nueva)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error en la BD al intentar cambiar la contraseña")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la BD al intentar cambiar la contraseña"
        )

    if not cambiar:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta o la cuenta está bloqueada."
        )
    
    return {"Exito": True, "Mensaje": "Contraseña actualizada con exito!"}


@router.delete("/{usuario_id}")
def borrar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin_actual = Depends(solo_administradores),
):
    if admin_actual.id == usuario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operación no permitida. No puedes eliminar tu propia cuenta.",
        )

    try:
        usuario_eliminado = eliminar_usuario(db, usuario_id=usuario_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error de BD al eliminar usuario %s", usuario_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la base de datos al intentar desactivar el usuario.",
        )

    if not usuario_eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    return {"Exito": True, "Mensaje": "Usuario desactivado correctamente"}


  

  

   


   
  

