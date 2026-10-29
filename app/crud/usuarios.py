from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import LOGIN_BLOQUEO_MINUTOS, LOGIN_MAX_INTENTOS
from app.core.roles import rol
from app.core.security import hash_password, verificar_contraseña
from app.models.usuarios import UsuariosModel, ahora_utc
from app.schemas.usuarios import EntradaRegistro


class CorreoYaRegistrado(Exception):
    """El correo ya le pertenece a otro usuario"""


class RolInvalido(Exception):
    """El rol_id enviado no existe en el enum rol."""


CAMPOS_EDITABLES = {"nombre", "correo", "activo"}

# En app/crud/usuarios.py (en lugar de invocar hash_password() al arrancar)
HASH_FALSO = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

def normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


# Este es el error oficial que lanza SQLAlchemy cuando rompes una regla de la base de datos (como la regla de que un correo debe ser único).
def _es_correo_duplicado(error: IntegrityError) -> bool:
    # Revisa si el error tiene datos, mira el código numérico que nos mandó la base de datos, y si ese número es exactamente 1062, devuelve True (sí, es un correo repetido). Si es cualquier otro número o error, devuelve False
    args = getattr(error.orig, "args", ())
    return bool(args) and args[0] == 1062


def esta_bloqueado(usuario: UsuariosModel) -> bool:
    return usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora_utc()


def _registrar_fallo(db: Session, usuario: UsuariosModel) -> None:
    """Suma un intento fallido; al llegar al máximo bloquea la cuenta un rato."""
    try:
        # UPDATE atómico (intentos = intentos + 1): si llegan varias peticiones a la vez
        # no se pierden cuentas.
        db.query(UsuariosModel).filter(UsuariosModel.id == usuario.id).update(
            {UsuariosModel.intentos_fallidos: UsuariosModel.intentos_fallidos + 1},
            synchronize_session=False,
        )
        db.commit()
        db.refresh(usuario)

        if usuario.intentos_fallidos >= LOGIN_MAX_INTENTOS:
            usuario.bloqueado_hasta = ahora_utc() + timedelta(minutes=LOGIN_BLOQUEO_MINUTOS)
            usuario.intentos_fallidos = 0
            db.commit()
    except Exception:
        db.rollback()
        raise


# Se eliminan los fallos y intentos fallidos una vez que se inicie sesion de forma exitosa.
def _limpiar_fallos(db: Session, usuario: UsuariosModel) -> None:
    if usuario.intentos_fallidos or usuario.bloqueado_hasta:
        try:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            db.commit()
        except Exception:
            db.rollback()
            raise


# Si la contraseña no cumplio con la validacion en el archivo de security.py entonces registramos un fallo.
def confirmar_password(db: Session, usuario: UsuariosModel, password: str) -> bool:
    if esta_bloqueado(usuario):
        return False
    if not verificar_contraseña(password, usuario.password):
        _registrar_fallo(db, usuario)
        db.refresh(usuario)  # <--- ¡Con esto sincronizas el objeto en memoria!
        return False
    return True


def iniciar_sesion(db: Session, correo: str, contraseña_ingresada: str):
    usuario = (
        db.query(UsuariosModel)
        .options(joinedload(UsuariosModel.rol))  # 👈 Aquí le dices: "Tráete también el rol de una vez"
        .filter(UsuariosModel.correo == normalizar_correo(correo))
        .first()
    )

    if not usuario:
        verificar_contraseña(contraseña_ingresada, HASH_FALSO)
        return None

    if esta_bloqueado(usuario):
        verificar_contraseña(contraseña_ingresada, HASH_FALSO)
        return None
    
    if not verificar_contraseña(contraseña_ingresada, usuario.password):
        _registrar_fallo(db, usuario)
        return None
    
    if not usuario.activo:
        return None

    _limpiar_fallos(db, usuario)
    return usuario


def registrar_usuario(db: Session, usuario: EntradaRegistro):
    # Ese bloque de código por sí solo solo prepara el paquete en la memoria RAM de tu servidor.
    db_usuario = UsuariosModel(
        Nombre=usuario.nombre,
        correo=normalizar_correo(usuario.correo),
        password=hash_password(usuario.password),
        rol_id=int(rol.Empleado.value),
    )

    try:
        db.add(db_usuario)
        db.commit()  # Aquí MySQL saltará si el correo ya existe
        db.refresh(db_usuario)

        # Forzamos la carga de la relación 'rol' ANTES del return: si no, el esquema de
        # salida (Pydantic) intentaría leerla perezosamente y podría fallar.
        _ = db_usuario.rol

        return db_usuario

    except IntegrityError as e:
        db.rollback()
        # Solo es "correo duplicado" si es un Duplicate entry (1062). Cualquier otro
        # IntegrityError se relanza tal cual para no mentirle al usuario.
        if _es_correo_duplicado(e):
            raise CorreoYaRegistrado("El correo electrónico ya se encuentra registrado.")
        raise
    except Exception:
        db.rollback()
        raise


def actualizar_rol_usuario_crud(db: Session, usuario_id: int, nuevo_rol_id: int):
    # El rol inválido lanza RolInvalido; None significa únicamente "usuario no encontrado".
    if nuevo_rol_id not in {rol.value for rol in Rol}:
        raise RolInvalido("El rol indicado no es válido.")

    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        return None

    try:
        usuario.rol_id = nuevo_rol_id
        db.commit()
        db.refresh(usuario)
        _ = usuario.rol
        return usuario
    except Exception:
        db.rollback()
        raise


def obtener_usuario_por_correo(db: Session, correo: str):
    return (
        db.query(UsuariosModel)
        .options(joinedload(UsuariosModel.rol))
        .filter(UsuariosModel.correo == normalizar_correo(correo))
        .first()
    )


def obtener_usuario_por_id(db: Session, usuario_id: int):
    return (
        db.query(UsuariosModel)
        .options(joinedload(UsuariosModel.rol))
        .filter(UsuariosModel.id == usuario_id)
        .first()
    )


def obtener_todos_los_usuarios(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(UsuariosModel)
        .options(joinedload(UsuariosModel.rol))  # evita una consulta extra por usuario
        .order_by(UsuariosModel.id)              # sin orden, la paginación es inestable
        .offset(skip)
        .limit(limit)
        .all()
    )


# No usamos el schema porque en el endpoint es donde vamos a agarrar solo lo datos que el cliente decidió actualizar para que viajen aqui y haga el proceso correspondiente.
def actualizar_usuario(db: Session, usuario_id: int, datos_actualizacion: dict):
    db_usuario = obtener_usuario_por_id(db, usuario_id)
    if not db_usuario:
        return None

    for campo, valor in datos_actualizacion.items():
        # Lista blanca de campos editables.
        if campo not in CAMPOS_EDITABLES:
            continue

        if campo == "correo":
            valor = normalizar_correo(valor)
            # Un correo nuevo vuelve a quedar sin verificar.
            if valor != db_usuario.correo:
                db_usuario.correo_verificado = False

        setattr(db_usuario, campo, valor)
        # Actualiza un dato de un usuario sobre la marcha, usando texto (strings) en lugar de escribir la propiedad fija con un punto (por ejemplo, cambia db_usuario.nombre = "Juan" usando variables).
        # ¿Cuándo lo usarás?
        # Cada vez que hagas una actualización parcial (como un PATCH) y recibas un diccionario dinámico con campos que no sabes de antemano cuáles van a venir (a veces solo el nombre, a veces el correo), permitiéndote recorrerlos y aplicarlos automáticamente uno por uno.

    try:
        db.commit()
        db.refresh(db_usuario)
        _ = db_usuario.rol  # fuerza la carga del Rol para que el esquema no falle
        return db_usuario
    except IntegrityError as e:  # correo ya usado por otro usuario (regla UNIQUE)
        db.rollback()
        if _es_correo_duplicado(e):
            raise CorreoYaRegistrado("El correo electrónico ya se encuentra registrado por otro usuario.")
        raise
    except Exception:
        db.rollback()
        raise


def cambiar_password(
    db: Session, usuario: UsuariosModel, password_actual: str, password_nueva: str
) -> bool:
    """Devuelve False si la contraseña actual no coincide (o la cuenta está bloqueada).

    Al cambiarla sube token_version: TODOS los tokens anteriores (otros dispositivos,
    un atacante con sesión robada) dejan de servir. El router entrega un token nuevo
    para que la sesión actual continúe.
    """
    if not confirmar_password(db, usuario, password_actual):
        return False

    try:
        usuario.password = hash_password(password_nueva)
        # Expresión SQL (token_version + 1): atómica, sin carreras.
        usuario.token_version = UsuariosModel.token_version + 1
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        db.commit()
        db.refresh(usuario)  # recarga el token_version real para emitir el token nuevo
        return True
    except Exception:
        db.rollback()
        raise


def eliminar_usuario(db: Session, usuario_id: int):
    db_usuario = obtener_usuario_por_id(db, usuario_id)
    if not db_usuario:
        return None

    try:
        db_usuario.activo = False
        db.commit()
        return db_usuario
    except Exception:
        db.rollback()
        raise

