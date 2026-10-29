import html #Es una librería estándar de Python para manipular caracteres especiales en HTML.
import logging#logging.info("Correo enviado exitosamente a usuario@email.com") o logging.error("Fallo al conectar con el servidor SMTP"). Es vital para depurar errores cuando tu API esté corriendo.
import smtplib#Es el "motor" principal. Es la herramienta que le permite a tu código Python conectarse a un servidor de correo externo (como el de Gmail,

import ssl #Hoy en día ningún servidor de correo acepta conexiones sin cifrar por seguridad. Esta librería crea un túnel seguro y encriptado entre tu aplicación FastAPI y el servidor de correo
from email.message import EmailMessage #Te permite armar el mensaje de forma ordenada y profesional. Con ella defines fácilmente:
from app.core import config as cfg

class ErrorEnvioCorreo(Exception):
    pass #Sé que esta clase está vacía por ahora, déjala pasar, no hagas nada y no me des error

def enviar(destino:str,asunto:str,texto:str,cuerpo_html)->None:
    if cfg.EMAIL_EN_CONSOLA:
        logger.warning("[EMAIL EN CONSOLA] para:%s | %s\n%s",destino,asunto,texto)
        return
    if not(cfg.SMTP_HOST and cfg.STMP_USER and cfg.SMTP_PASSWORD):
        raise ErrorEnvioCorreo("SMTP no configurado.")

#Lo que va tener el Email.
mensaje=EmailMessage()
mensaje["Subject"]=asunto
mensaje["From"]=cfg.SMTP_FROM
mensaje["To"]=destino
mensaje.set_content(texto)
mensaje.add_alternative(cuerpo_html,subtype="html")

contexto=ssl.create_default_context()
try:
        # Verificamos el interruptor SMTP_SSL (True = Puerto 465, False = Puerto 587)
        if cfg.SMTP_SSL:
            # --- OPCIÓN 1: SSL DIRECTO (Ej. Puerto 465) ---
            # Abre un túnel cifrado con el servidor desde el primer milisegundo.
            with smtplib.SMTP_SSL(cfg.SMTP_HOST, cfg.SMTP_PORT, context=contexto, timeout=15) as smtp:
                # Nos autenticamos con el usuario y la contraseña de la app
                smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                # Enviamos el paquete de correo que construimos con EmailMessage
                smtp.send_message(mensaje)
        else:
            # --- OPCIÓN 2: STARTTLS (Ej. Puerto 587) ---
            # Abre una conexión abierta estándar al inicio.
            with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=15) as smtp:
                # Subimos el nivel de seguridad y activamos el cifrado TLS en pleno vuelo
                smtp.starttls(context=contexto)
                # Nos autenticamos ante el servidor
                smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                # Enviamos el correo
                smtp.send_message(mensaje)

    except (smtplib.SMTPException, OSError) as error:
        # --- MANEJO DE ERRORES ---
        # Si falla la red (OSError) o el servidor rechaza algo (SMTPException),
        # atrapamos el fallo y lo convertimos en nuestra excepción personalizada.
        raise ErrorEnvioCorreo(str(error)) from error

def _html(nombre: str, intro: str, codigo: str, pie: str) -> str:
    return f"""\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;">
  <h2 style="margin:0 0 16px;">{html.escape(cfg.NOMBRE_APP)}</h2>
  <p>Hola {html.escape(nombre)},</p>
  <p>{html.escape(intro)}</p>
  <p style="font-size:32px;letter-spacing:8px;font-weight:bold;text-align:center;
            background:#f3f4f6;padding:16px;border-radius:8px;">{codigo}</p>
  <p>El código vence en {cfg.CODIGO_EXPIRA_MINUTOS} minutos y solo se puede usar una vez.</p>
  <p style="color:#6b7280;font-size:13px;">{html.escape(pie)}</p>
</div>"""

def enviar_codigo_verificacion(destino: str, nombre: str, codigo: str) -> None:
    intro = "Usa este codigo para confirmar tu correo y activar tu cuenta:"
    pie = "Si no creaste esta cuenta, ignora este mensaje."
    
    texto = (
        f"Hola {nombre},\n\n{intro}\n\n"
        f"Tu código es: {codigo}\n"
        f"Vence en {cfg.CODIGO_EXPIRA_MINUTOS} minutos.\n\n{pie}"
    )
    
    try:
        _enviar(
            destino=destino,
            asunto=f"{cfg.NOMBRE_APP}: Codigo de verificacion",
            texto=texto,
            cuerpo_html=_html(nombre, intro, codigo, pie) # 👈 Aquí usas los 4 datos para el diseño visual
        )
    except ErrorEnvioCorreo:
        # 3. Si algo falla, dejamos constancia en los registros (logs) del servidor
        logger.exception("No se pudo enviar el correo de verificacion.")

def enviar_codigo_recuperacion(destino: str, nombre: str, codigo: str) -> None:
    """
    Función específica para enviar el correo de recuperación de contraseña.
    Reutiliza la infraestructura de _enviar() y el diseño HTML genérico _html().
    """
    
    # 1. Definimos los textos personalizados para la recuperación
    intro = "Recibimos una solicitud para restablecer tu contraseña. Tu código es:"
    pie = "Si no fuiste tú, ignora este mensaje: tu contraseña no cambiará."
    
    # 2. Armamos la versión en texto plano para clientes de correo sin diseño HTML
    texto = (
        f"Hola {nombre},\n\n"
        f"{intro}\n\n"
        f"{codigo}\n\n"
        f"Este código vence en {cfg.CODIGO_EXPIRA_MINUTOS} minutos.\n\n"
        f"{pie}"
    )
    
    try:
        # 3. Llamamos a la función interna _enviar pasándole todos los parámetros necesarios:
        #    - destino: El correo del usuario
        #    - asunto: El título del correo con el nombre de la app dinámico
        #    - texto: El mensaje plano que acabamos de armar arriba
        #    - cuerpo_html: La plantilla HTML generada por _html() con los datos inyectados
        _enviar(
            destino=destino,
            asunto=f"{cfg.NOMBRE_APP}: Recuperar contraseña",
            texto=texto,
            cuerpo_html=_html(nombre, intro, codigo, pie)
        )
        
    except ErrorEnvioCorreo:
        # 4. Si algo falla (red, servidor, credenciales), atrapamos nuestro error personalizado
        #    y dejamos constancia en los registros (logs) del sistema.
        logger.exception("No se pudo enviar el correo de recuperación.")

def enviar_aviso_cambio_password(destino: str, nombre: str) -> None:
    """
    Función de seguridad para notificar al usuario por correo que su contraseña 
    acaba de ser modificada (ya sea por cambio manual o recuperación).
    """
    
    # 1. Definimos el asunto y los textos comerciales de la alerta
    asunto = f"{cfg.NOMBRE_APP}: tu contraseña fue cambiada"
    intro = "La contraseña de tu cuenta acaba de cambiar y se cerraron tus otras sesiones."
    pie = (
        "Si no fuiste tú, restablece tu contraseña de inmediato con la opción "
        "'Olvidé mi contraseña' y contacta al soporte."
    )
    
    # 2. Armamos la versión en texto plano para clientes de correo básicos
    texto = f"Hola {nombre},\n\n{intro}\n\n{pie}\n"
    
    # 3. Creamos una plantilla HTML específica para alertas (con texto en rojo de advertencia)
    
    #Con html.escape: Neutralizas la amenaza convirtiendo esos símbolos en texto inofensivo que se ve bien y no hace daño a nadie. ¡Por eso es obligatorio usarlo con los datos que escriben los usuarios!
    cuerpo_html = f"""\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;">
  <h2 style="margin:0 0 16px;">{html.escape(cfg.NOMBRE_APP)}</h2>
  <p>Hola {html.escape(nombre)},</p>
  <p>{html.escape(intro)}</p>
  <p style="color:#b91c1c;font-size:14px;"><strong>{html.escape(pie)}</strong></p>
</div>"""

    try:
        # 4. Llamamos a la función interna _enviar para disparar el correo de alerta de forma segura
        _enviar(
            destino=destino, 
            asunto=asunto, 
            texto=texto, 
            cuerpo_html=cuerpo_html
        )
        
    except ErrorEnvioCorreo:
        # 5. Si ocurre algún error en la red o el servicio, lo atrapamos y dejamos registro en los logs
        logger.exception("No se pudo enviar el aviso de cambio de contraseña.")