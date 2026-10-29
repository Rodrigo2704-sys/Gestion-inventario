import hashlib 
import hmac
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import (
    CODIGO_EXPIRA_MINUTOS,
    CODIGO_MAX_INTENTOS,
    CODIGO_REENVIO_SEGUNDOS,
    llave_secreta,

)

from app.core.security import hash_password
from app.crud.usuarios import obtener_usuario_por_correo
from app.models.usuarios import  CodigoVerificacionModel
from app.models.usuarios import UsuariosModel, ahora_utc

PROPOSITO_VERIFICAR="Verificar_correo"
PROPOSITO_RECUPERAR="Recuperar_password"

class CodigoReciente(Exception):
    """Se pidio un codigo hace muy poco, hay que esperar antes de pedir un codigo nuevo."""


def generar_codigo() -> str:
    return f"{secrets.randbelow(10**6):06d}"


#Lo que "hashea" el código es una combinación de datos del usuario + el código secreto + una llave privada del servidor, utilizando el algoritmo SHA-256. El resultado es una cadena cifrada segura que puedes enviar o comparar sin exponer información sensible
def hash_codigo(usuario_id: int, proposito: str, codigo:str )->str:
    mensaje = f"{usuario_id}:{proposito}:{codigo}".encode("utf-8")
    return hmac.new(llave_secreta.encode("utf-8"),mensaje,hashlib.sha256).hexdigest()

def crear_codigo(db: Session, usuario_id: int, proposito: str) -> str:
    """Crea un código nuevo, invalida los anteriores y devuelve el código EN CLARO

    (para enviarlo por correo; nunca se vuelve a poder leer de la BD).
    """
    ahora = ahora_utc()  # Obtiene la fecha y hora actual en UTC
    try:
        # 1. Bloquea la fila del usuario hasta el commit. Esto evita que dos peticiones
        # simultáneas pasen al mismo tiempo la revisión de tiempo de espera y se salten el límite.
        db.query(UsuariosModel).filter(
            UsuariosModel.id == usuario_id
        ).with_for_update().first()

        # 2. Busca el último código generado para este usuario y propósito específico.
        ultimo = (
            db.query(CodigoVerificacionModel)
            .filter(
                CodigoVerificacionModel.usuario_id == usuario_id,
                CodigoVerificacionModel.proposito == proposito,
            )
            .order_by(CodigoVerificacionModel.id.desc())
            .first()
        )

        # Si existe un código previo y no ha pasado el tiempo mínimo de reespera (cooldown), frena la petición.
        if (
            ultimo
            and (ahora - ultimo.creado_en).total_seconds()
            < CODIGO_REENVIO_SEGUNDOS
        ):
            raise CodigoReciente(
                "Espera un momento antes de pedir otro código."
            )

        # 3. Invalida los códigos anteriores: marca como usados (True) todos los que sigan vigentes.
        (
            db.query(CodigoVerificacionModel)
            .filter(
                CodigoVerificacionModel.usuario_id == usuario_id,
                CodigoVerificacionModel.proposito == proposito,
                CodigoVerificacionModel.usado.is_(False),
            )
            .update({"usado": True}, synchronize_session=False)
        )

        # 4. Limpieza de mantenimiento: borra físicamente códigos expirados de hace más de 1 día.
        (
            db.query(CodigoVerificacionModel)
            .filter(CodigoVerificacionModel.expira_en < ahora - timedelta(days=1))
            .delete(synchronize_session=False)
        )

        # 5. Genera el código en claro y guarda su versión hasheada y segura en la base de datos.
        codigo = _generar_codigo()
        db.add(
            CodigoVerificacionModel(
                usuario_id=usuario_id,
                proposito=proposito,
                codigo_hash=_hash_codigo(usuario_id, proposito, codigo),
                expira_en=ahora + timedelta(minutes=CODIGO_EXPIRA_MINUTOS),
                creado_en=ahora,
            )
        )

        # Confirma los cambios permanentemente en la base de datos.
        db.commit()

        # Retorna el código en claro por única vez para enviarlo al usuario.
        return codigo

    except Exception:
        # Si algo falla en el proceso, revierte todos los cambios de la transacción actual.
        db.rollback()
        raise


def _validar_codigo(db: Session, usuario_id: int, proposito: str, codigo: str) -> bool:
    """True si el código es correcto. En ese caso lo marca como usado pero NO hace commit:
    quien llama confirma junto con su propio cambio (así todo ocurre en una sola transacción).
    Si es incorrecto, el intento fallido SÍ se guarda de inmediato."""
    registro = (
        db.query(CodigoVerificacionModel)
        .filter(
            CodigoVerificacionModel.usuario_id == usuario_id,
            CodigoVerificacionModel.proposito == proposito,
            CodigoVerificacionModel.usado.is_(False),
            CodigoVerificacionModel.expira_en > ahora_utc(),
        )
        .order_by(Codigo.id.desc())
        .with_for_update()  # evita que dos peticiones simultáneas se salten el límite de intentos
        .first()
    )
    if not registro or registro.intentos >= CODIGO_MAX_INTENTOS:
        return False

    esperado = _hash_codigo(usuario_id, proposito, codigo)
    if not hmac.compare_digest(registro.codigo_hash, esperado):
        registro.intentos += 1
        db.commit()
        return False

    registro.usado = True
    db.flush()
    return True


def verificar_correo(db: Session, correo: str, codigo: str) -> bool:
    """Marca el correo como verificado si el código es correcto."""
    usuario = obtener_usuario_por_correo(db, correo)
    if not usuario or not usuario.activo or usuario.correo_verificado:
        return False

    try:
        if not _validar_codigo(db, usuario.id, PROPOSITO_VERIFICAR, codigo):
            return False
        usuario.correo_verificado = True
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def restablecer_password(db: Session, correo: str, codigo: str, password_nueva: str) -> bool:
    """Cambia la contraseña si el código es correcto. Como el usuario demostró que controla
    su bandeja de entrada, también deja el correo como verificado.

    NUEVO: sube token_version (cierra todas las sesiones abiertas: si la contraseña se
    restablece porque alguien entró a la cuenta, el atacante queda fuera) y limpia el
    bloqueo por intentos fallidos del login."""
    usuario = obtener_usuario_por_correo(db, correo)
    if not usuario or not usuario.activo:
        return False

    try:
        if not _validar_codigo(db, usuario.id, PROPOSITO_RECUPERAR, codigo):
            return False
        usuario.password = hash_password(password_nueva)
        usuario.correo_verificado = True
        usuario.token_version = UsuariosModel.token_version + 1
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise