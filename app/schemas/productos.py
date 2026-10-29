from typing import Annotated, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Definimos restricciones reutilizables para limpiar y validar textos
TextoCorto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
TextoLargo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class DatosProducto(BaseModel):
    Codigo: TextoCorto
    Nombre: TextoCorto
    Descripcion: TextoLargo
    Categoria: TextoLargo
    Precio_compra: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    Precio_venta: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock_maximo: int = Field(ge=0)
    stock_minimo: int = Field(ge=0)
    stock_actual: int = Field(ge=0)
    activo: bool = True

    model_config = ConfigDict(extra="forbid", from_attributes=True)



class EntradaProducto(BaseModel):
    Codigo: TextoCorto  
    cantidad: int = Field(gt=0, description="Cantidad de unidades que ingresan al inventario")
    Precio_compra: Decimal = Field(gt=0, max_digits=10, decimal_places=2, description="Precio unitario de compra del lote")
    observacion: Optional[str] = Field(default=None, max_length=255, description="Nota u observación del ingreso")

    model_config = ConfigDict(extra="forbid")


class SalidaProducto(BaseModel):
    Codigo: TextoCorto  
    cantidad: int = Field(gt=0, description="Cantidad de unidades que salen del inventario")
    observacion: Optional[str] = Field(default=None, max_length=255, description="Motivo de salida (venta, pérdida, retiro)")

    model_config = ConfigDict(extra="forbid")


class ActualizarProducto(BaseModel):
    # Todos son opcionales porque el usuario puede actualizar solo un campo (ej. cambiar solo el precio o el stock)
    Nombre: Optional[TextoCorto] = None
    Descripcion: Optional[TextoLargo] = None
    Categoria: Optional[TextoLargo] = None
    Precio_compra: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)#Por ejemplo, gt=0 significa que acepta 0.1, 1, 50, pero nunca el número 0 ni números negativos.
    Precio_venta: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock_maximo: Optional[int] = Field(default=None, ge=0)
    stock_minimo: Optional[int] = Field(default=None, ge=0)
    stock_actual: Optional[int] = Field(default=None, ge=0)#Por ejemplo, ge=0 significa que sí acepta el 0 y cualquier número positivo, pero rechaza los números negativos
    activo: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")
