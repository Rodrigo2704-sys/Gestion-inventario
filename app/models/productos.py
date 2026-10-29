from datetime import datetime, timezone
# Corregido: Agregado Numeric y removido relationship de aquí
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import relationship # El relationship va desde sqlalchemy.orm

from app.core.database import Base

def ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProductoModel(Base):
    __tablename__ = "productos"

    Codigo = Column(String(50), primary_key=True, index=True)
    Nombre = Column(String(50), nullable=False)
    Descripcion = Column(String(255), nullable=False)
    Categoria = Column(String(255), nullable=False)
    Precio_compra = Column(Numeric(10, 2), nullable=False)
    Precio_venta = Column(Numeric(10, 2), nullable=False)
    stock_maximo = Column(Integer, nullable=False)
    stock_minimo = Column(Integer, nullable=False)
    stock_actual = Column(Integer, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    # Relaciones
    entradas = relationship("RegistroEntradaModel", back_populates="producto")
    historial_movimientos = relationship("HistorialModel", back_populates="producto_historial")


class RegistroEntradaModel(Base):
    __tablename__ = "registro_entradas"

    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(10, 2), nullable=False)
    nota = Column(String(255), nullable=False,default="Sin nota")
    fecha = Column(DateTime, nullable=False, default=ahora_utc)
    producto_codigo = Column(String(50), ForeignKey("productos.Codigo"), nullable=False, index=True)
    
    producto = relationship("ProductoModel", back_populates="entradas")


class HistorialModel(Base):
    __tablename__ = "Historial"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    producto_comprado = Column(String(50), ForeignKey("productos.Codigo"), nullable=False, index=True)
    fecha_realizada = Column(DateTime, nullable=False, default=ahora_utc)

    usuario_historial = relationship("UsuariosModel", back_populates="historial_usuarios")
    producto_historial = relationship("ProductoModel", back_populates="historial_movimientos")