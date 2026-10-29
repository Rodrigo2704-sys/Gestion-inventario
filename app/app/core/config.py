import os
import warnings
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Detecta en qué entorno estamos operando (desarrollo o producción)
entorno = os.getenv("entorno", "desarrollo").strip().lower()
produccion = entorno == "produccion"

# 1. Validación obligatoria: La llave secreta debe existir en el .env
llave_secreta = os.getenv("llave_secreta")
if not llave_secreta:  # Corregido el espacio en el nombre de la variable
    raise ValueError(
        "ERROR CRÍTICO DE SEGURIDAD: La variable de entorno 'SECRET_KEY' "
        "no está definida en el archivo .env"
    )

# 2. Validación de longitud: La llave debe ser segura (mínimo 32 caracteres)
if len(llave_secreta) < 32:
    if produccion:
        # En producción se bloquea si la clave es corta
        raise ValueError(
            "La llave secreta debe tener al menos 32 caracteres en producción."
        )
    # En desarrollo solo lanza una advertencia en amarillo para no frenar las pruebas
    warnings.warn(
        "La llave secreta es muy corta (menos de 32 caracteres).",
        stacklevel=2,
    )
#El algoritmo en los tokens JWT (JSON Web Tokens) es la fórmula matemática que usa el sistema para firmar y verificar el token
#Es altamente seguro.
Algoritmo = os.getenv("Algoritmo", "HS256")
if Algoritmo not in {"HS256", "HS384", "HS512"}:
    raise ValueError(
        f"Algoritmo '{Algoritmo}' no permitido. Usa HS256, HS384 o HS512."
    )

# CORRECCIÓN: Agregado el signo '=' que faltaba
token_expiracion = int(os.getenv("token_expiracion", 30))

# CORS_ORIGINS: Lista de invitados VIP. Define qué páginas web (Frontend)
# tienen permiso para hacerle peticiones a esta API. Se leen del .env (separados
# por coma); si no existen, se usan los servidores de desarrollo habituales.
_ORIGENES_DEV = (
    "http://127.0.0.1:5500,http://localhost:5500,"
    "http://127.0.0.1:8080,http://localhost:8080"
)
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", _ORIGENES_DEV).split(",") if o.strip()
]

#Lo que hace la función: Toma ese texto del .env, le quita los espacios sobrantes (.strip()), lo pasa a minúsculas (.lower()) y revisa si coincide con alguna forma común de decir "sí" ("1", "true", "si", "sí", "yes").
# ---------------------------------------------------------------------------
# CORREO (SMTP) Y CÓDIGOS DE VERIFICACIÓN
# ---------------------------------------------------------------------------
def _bool_env(nombre: str, defecto: bool = False) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in {"1", "true", "si", "sí", "yes"}

#Credenciales para el codigo de verificacion gmail
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER
# False -> STARTTLS (puerto 587). True -> SSL directo (puerto 465).
SMTP_SSL = _bool_env("SMTP_SSL", False)

# SOLO DESARROLLO: en vez de enviar el correo, imprime el código en la consola.
EMAIL_EN_CONSOLA = _bool_env("EMAIL_EN_CONSOLA", False)
# NUEVO: en producción esto dejaría los códigos de verificación en los logs.
# CORRECCIÓN: Usamos 'produccion' que es la variable declarada arriba
if produccion and EMAIL_EN_CONSOLA:
    raise ValueError("EMAIL_EN_CONSOLA no puede estar activo en producción.")

NOMBRE_APP = os.getenv("NOMBRE_APP", "Mi aplicación")

CODIGO_EXPIRA_MINUTOS = int(os.getenv("CODIGO_EXPIRA_MINUTOS", 15))
CODIGO_MAX_INTENTOS = int(os.getenv("CODIGO_MAX_INTENTOS", 5))
CODIGO_REENVIO_SEGUNDOS = int(os.getenv("CODIGO_REENVIO_SEGUNDOS", 60))

# ---------------------------------------------------------------------------
# NUEVO: BLOQUEO DE CUENTA POR FUERZA BRUTA EN EL LOGIN
# Tras LOGIN_MAX_INTENTOS contraseñas incorrectas seguidas, la cuenta queda
# bloqueada LOGIN_BLOQUEO_MINUTOS (aunque el atacante cambie de IP).
# ---------------------------------------------------------------------------
LOGIN_MAX_INTENTOS = int(os.getenv("LOGIN_MAX_INTENTOS", 5))
LOGIN_BLOQUEO_MINUTOS = int(os.getenv("LOGIN_BLOQUEO_MINUTOS", 15))