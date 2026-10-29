from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.productos import ProductoModel,RegistroEntradaModel, HistorialModel
from app.schemas.productos import DatosProducto, EntradaProducto, ActualizarProducto

class ProductoYaRegistrado(Exception):
    """El producto con ese codigo ya se encuentra registrado"""

class ProductoNoEncontrado(Exception):
    """El producto no se ha encontrado."""

class StockInsuficiente(Exception):
    """El stock es insuficiente."""



def registrar_producto(db: Session, Producto: DatosProducto):
    db_producto = ProductoModel(
        Codigo=Producto.Codigo,
        Nombre=Producto.Nombre,
        Descripcion=Producto.Descripcion,
        Categoria=Producto.Categoria,
        Precio_compra=Producto.Precio_compra,
        Precio_venta=Producto.Precio_venta,
        stock_maximo=Producto.stock_maximo,
        stock_minimo=Producto.stock_minimo,
        stock_actual=Producto.stock_actual,
        activo=Producto.activo
    )

    try:
        db.add(db_producto)
        db.commit()
        db.refresh(db_producto)
        return db_producto

    except IntegrityError:
        db.rollback()
        raise ProductoYaRegistrado("El producto ya se encuentra registrado.")
    except Exception:
        db.rollback()
        raise


def registrar_entrada_stock(db: Session, entrada_in: EntradaProducto):
    producto = db.query(ProductoModel).filter(ProductoModel.Codigo == entrada_in.Codigo).first()

    if not producto:
        raise ProductoNoEncontrado("El producto no existe en el catálogo. Debes registrarlo primero.")

    try:
        producto.stock_actual = producto.stock_actual + entrada_in.cantidad
        producto.Precio_compra = entrada_in.Precio_compra
               
        db.add(nuevo_registro)

        db.commit()
        db.refresh(producto)
        return producto

    except Exception:
        db.rollback()
        raise

#
  * Disminuir el stock por concepto de venta, pérdida o retiro.

  * Validación de seguridad: Bloquear y no permitir salidas si el stock actual es menor a la cantidad solicitada.


def registro_salida_stock(db: Session, datos: SalidaProducto, usuario_id: int):
    producto = db.query(ProductoModel).filter(ProductoModel.Codigo == datos.Codigo).first()

    if not producto:
        raise ProductoNoEncontrado("No se encontró el producto.")
    
    if producto.stock_actual < datos.cantidad:
        raise StockInsuficiente("El stock es insuficiente.")
        
    try:
        producto.stock_actual = producto.stock_actual - datos.cantidad

        nuevo_historial = HistorialModel(
            usuario_id=usuario_id,          
            producto_comprado=datos.Codigo,  # Coincide con Pydantic (Codigo)
            cantidad=datos.cantidad,            
            nota=datos.observacion or "Venta"   
        )
        db.add(nuevo_historial)

        db.commit()
        db.refresh(producto)
        return producto

    except Exception:
        db.rollback()
        raise



def actualizar_producto(db: Session, codigo: str, Producto: ActualizarProducto):
    producto = db.query(ProductoModel).filter(ProductoModel.Codigo == codigo).first()

    if not producto:
        raise ProductoNoEncontrado("No se encontró el producto a actualizar.")
    
    datos_a_cambiar = Producto.model_dump(exclude_unset=True)

    for key, value in datos_a_cambiar.items():
        setattr(producto, key, value)
        
    db.commit()
    db.refresh(producto)
    
    return producto


def eliminar_producto(db: Session, codigo: str):
    producto_eliminar = db.query(ProductoModel).filter(ProductoModel.Codigo == codigo).first()

    if not producto_eliminar:
        raise ProductoNoEncontrado("No se encontró el producto.")
    
    try:
        producto_eliminar.activo = False
        db.commit()
        db.refresh(producto_eliminar)
        return producto_eliminar
    except Exception:
        db.rollback()
        raise


def Buscar_producto_categoria(db: Session, categoria: str, skip: int = 0, limit: int = 10):
    return db.query(ProductoModel).filter(ProductoModel.Categoria == categoria).offset(skip).limit(limit).all()


def Buscar_Producto_codigo(db: Session, codigo: str):
    producto = db.query(ProductoModel).filter(ProductoModel.Codigo == codigo).first()
    
    if not producto:
        raise ProductoNoEncontrado("El producto no existe.")
        
    return producto



from sqlalchemy import func, desc

def calcular_valor_inventario(db: Session):
    total = db.query(func.sum(ProductoModel.stock_actual * ProductoModel.Precio_compra)
    ).scalar()#Quita las tuplas
    return total or 0.0 


def contar_productos(db: Session):
    return db.query(ProductoModel).count()
    

# 3. Obtener los 5 productos con mayor movimiento/rotación (usando la tabla Historial)
def obtener_productos_mas_vendidos(db: Session):
    resultado = (
        db.query(HistorialModel.producto_comprado,
            func.sum(HistorialModel.cantidad).label("total_salidas")
        )
        .group_by(HistorialModel.producto_comprado)
        .order_by(desc("total_salidas"))
        .limit(5)
        .all()
    )
    return resultado