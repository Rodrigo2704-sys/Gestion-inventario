from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship # Correcto desde sqlalchemy.orm

from app.core.database import Base
# (Ya no importamos HistorialModel aquí arriba para evitar el ciclo circular)


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RolModel(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    Nombre = Column(String(50), nullable=False, unique=True)

    usuarios = relationship("UsuariosModel", back_populates="rol")


class UsuariosModel(Base):
    __tablename__ = "usuarios" 

    id = Column(Integer, primary_key=True, index=True)
    Nombre = Column(String(50), nullable=False)
    correo = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(100), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False, default=2)
    activo = Column(Boolean, nullable=False, default=True)
    correo_verificado = Column(Boolean, nullable=False, default=False)
    intentos_fallidos = Column(Integer, nullable=False, default=0)
    bloqueado_hasta = Column(DateTime, nullable=True)
    token_version = Column(Integer, nullable=False, default=0)

    rol = relationship("RolModel", back_populates="usuarios")
    codigos = relationship("CodigoVerificacionModel", back_populates="usuario", cascade="all, delete-orphan")
    historial_usuarios = relationship("HistorialModel", back_populates="usuario_historial")


class CodigoVerificacionModel(Base):
    __tablename__ = "codigos_verificacion"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    proposito = Column(String(30), nullable=False)          
    codigo_hash = Column(String(64), nullable=False)         
    expira_en = Column(DateTime, nullable=False)
    intentos = Column(Integer, nullable=False, default=0)
    usado = Column(Boolean, nullable=False, default=False)
    creado_en = Column(DateTime, nullable=False, default=ahora_utc)

    usuario = relationship("UsuariosModel", back_populates="codigos")