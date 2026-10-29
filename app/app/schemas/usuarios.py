#Entrada, son los datos que el usuario va enviar por medio de un post,patch, etc.
#Salida, son lo que vmaos a devolver al usuario desde el servidor.

from typing import Annotated, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

# Ajusta max_length al tamaño real de la columna en tu tabla.
Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50)]

# bcrypt ignora (o rechaza, según la librería) lo que pase de 72 bytes.
# Si usas argon2 puedes subir este límite.
MAX_PASSWORD = 72
MAX_CORREO = 100 # Agregado para que la función de correo no falle


def _normalizar_correo(correo: str) -> str:
    if len(correo) > MAX_CORREO:
        raise ValueError(f"El correo no puede superar los {MAX_CORREO} caracteres.")
    return correo.lower()


def _validar_bytes_password(contraseña: str) -> str:
    if len(contraseña.encode("utf-8")) > MAX_PASSWORD:
        raise ValueError("La contraseña excede el límite de bytes permitidos.")
    return contraseña


class RolSalida(BaseModel):
    id: int
    nombre: str
    #Lo pones cada vez que tu endpoint vaya a retornar un objeto que sacaste de la base de datos y quieras que Pydantic lo empaquete y lo convierta a JSON automáticamente para enviárselo al usuario.
    model_config = ConfigDict(from_attributes=True)


class DatosUsuario(BaseModel):
    nombre: str
    correo: EmailStr


class EntradaRegistro(DatosUsuario):
    nombre: Nombre

    @field_validator("correo")
    #Es una exigencia técnica de Pydantic v2. Le indica a Python que este método pertenece a la clase del esquema y no a un objeto individual.
    @classmethod
    def correo_en_minusculas(clase, correo: str) -> str:
        return _normalizar_correo(correo) # Corregido: antes decía 'valor'

    
    password: str = Field(
        ...,
        min_length=8,
        max_length=MAX_PASSWORD,
        description="Entre 8 y 72 caracteres",
    )

    #La reacción de extra="forbid": Como prohibiste los extras con "forbid", Pydantic rechaza toda la petición y le devuelve al usuario un error 422 Unprocessable Entity diciendo: "Oye, estás enviando un campo llamado is_admin que yo no autoricé aquí".
    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def password_72_bytes(clase, contraseña: str) -> str:
        return _validar_bytes_password(contraseña)


class SalidaUsuario(DatosUsuario):
    id: int
    rol_id: int
    activo: bool = True
    rol: Optional[RolSalida] = None

    model_config = ConfigDict(from_attributes=True)


class ActualizarUsuario(BaseModel):
    nombre: Optional[Nombre] = None
    correo: Optional[EmailStr] = None
    activo: Optional[bool] = None

    contraseña_actual: Optional[str] = Field(None, max_length=95) # Corregido el '==' por '='

    #"Oye, lee los datos desde los atributos (from attributes) del objeto de la base de datos, y no busques un diccionario".
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("correo")
    @classmethod
    def normalizar_correo_minusculas(clase, correo: Optional[str]) -> Optional[str]:
        if correo is not None:
            return _normalizar_correo(correo)
        return correo

    #Este bloque de código es un guardián de seguridad que se suele colocar en los esquemas de actualización (PATCH o PUT)
    @model_validator(mode="after")
    def sin_nulos_explicitos(self):
        # Con exclude_unset, un {"nombre": null} llegaría a la BD como NULL
        # y reventaría con un 500 si la columna es NOT NULL.

        #Este bucle recorre cada uno de esos campos que el cliente decidió enviar.
        for campo in self.model_fields_set:
            #Revisa si el valor que mandó el cliente para ese campo es exactamente un null (None en Python).
            if getattr(self, campo) is None:
                raise ValueError(f"'{campo}' no puede ser null")
        return self


class CambiarPassword(BaseModel):
    contraseña_actual: str
    contraseña_nueva: str = Field(..., min_length=8, max_length=MAX_PASSWORD)

    model_config = ConfigDict(extra="forbid")

    @field_validator("contraseña_nueva")
    @classmethod
    def password_72_bytes(clase, contraseña: str) -> str:
        return _validar_bytes_password(contraseña)

    @model_validator(mode="after")
    def distinta_de_la_actual(self):
        if self.contraseña_actual == self.contraseña_nueva:
            raise ValueError("La contraseña nueva debe ser distinta de la actual")
        return self