import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencias import obtener_usuario_actual, solo_administradores
from app.crud.usuarios import (
    ProductoYaRegistrado,
    ProductoNoEncontrado,
    StockInsuficiente,
    registrar_entrada_stock,
    registrar_producto,
    registro_salida_stock,
    actualizar_producto,
    eliminar_producto, 
    Buscar_producto_categoria,
    Buscar_Producto_codigo 
)

from app.schemas.usuarios import (
    DatosProducto,
    EntradaProducto,
    ActualizarProducto,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/productos", tags=["Productos"])

@router.post("/registrar/producto", response_model=DatosProducto, status_code=status.HTTP_201_CREATED)
def registrar_un_producto(
    db: Session = Depends(get_db),
    datos: DatosProducto, 
    admin = Depends(solo_administradores)
): 
    try:
        producto_creado = registrar_producto(db, datos)

    except ProductoYaRegistrado as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error)
        )

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Hubo un error en la BD al registrar el producto.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar el producto."
        )

    return producto_creado


@router.post("/registrar/stock", status_code=status.HTTP_200_OK)
def registrar_stock(
    db: Session = Depends(get_db),
    datos: EntradaProducto,
    usuario = Depends(obtener_usuario_actual), 
):
    try:
        registrar_entrada_stock(db, datos)

    except ProductoNoEncontrado as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Hubo un error al intentar registrar el stock al producto.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hubo un error al actualizar el stock al producto."
        )
    return {"Exito": True, "Mensaje": "Stock actualizado con éxito."}


@router.post("/salida/stock",status_code=status.HTTP_200_OK)
def salida_stock_producto(
    db:session=Depends(get_db),
    datos:SalidaProducto,
    usuario_id:int,
    permiso:obtener_usuario_actual

):

   try:
       registro_salida_stock(db,datos,usuario_id)

    except ProductoNoEncontrado as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StockInsuficiente as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Hubo un error al registrar la salida del producto.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hubo un error al registrar la salida del producto."
        )
    return {"Exito:":True,"Mensaje":"Se ha registrado la salida del producto con exito!"}
       

   

@router.patch("/{codigo}/actualizar/producto", response_model=DatosProducto, status_code=status.HTTP_200_OK)
def actualizar_el_producto(
    codigo: str,
    datos: ActualizarProducto,
    db: Session = Depends(get_db),
    admin = Depends(solo_administradores) 
):
    if hasattr(datos, "model_dump"):  
        datos_dict = datos.model_dump(exclude_unset=True)
    else:  
        datos_dict = datos.dict(exclude_unset=True)

    if not datos_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No se envió ningún campo a actualizar."
        )
    
    try:
        actualizar_producto_en_BD = actualizar_producto(db, codigo, datos)

    except ProductoNoEncontrado as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        )
    
    except SQLAlchemyError:
        db.rollback()
        logger.exception("No se pudo actualizar las propiedades del producto.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hubo un error en la BD al actualizar las propiedades del producto."
        )
        
    return actualizar_producto_en_BD 


@router.delete("/{codigo}/eliminar/producto", status_code=status.HTTP_200_OK)
def eliminar_el_producto(
    db: Session = Depends(get_db),
    codigo: str,
    admin = Depends(solo_administradores)
):
    try:
        eliminar_producto(db, codigo) 
    
    except ProductoNoEncontrado as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Hubo un error en la BD al intentar eliminar el producto.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hubo un error en la BD al intentar eliminar el producto."
        )

    return {"Exito": True, "Mensaje": "El producto se ha eliminado con éxito."}
    

@router.get("/categoria/{categoria}", response_model=List[DatosProducto])
def buscar_los_productos_por_categoria(
    categoria: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    permiso:obtener_usuario_actual
):
    return Buscar_producto_categoria(db, categoria=categoria, skip=skip, limit=limit)


@router.get("/producto/{codigo}", response_model=DatosProducto)
def buscar_los_productos_por_codigo(
    codigo: str, 
    db: Session = Depends(get_db),
    permiso:obtener_usuario_actual
):
    producto = Buscar_Producto_codigo(db, codigo=codigo)
    
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El producto no existe."
        )
        
    return producto


@router.get("/dashboard/metricas", status_code=status.HTTP_200_OK)
def obtener_metricas_dashboard(
    db: Session = Depends(get_db),
    usuario = Depends(obtener_usuario_actual) 
):
    valor_inventario = calcular_valor_inventario(db)
    total_productos = contar_productos(db)
    top_productos = obtener_productos_mas_vendidos(db)

    return {
        "valor_total_inventario": valor_inventario,
        "total_productos_registrados": total_productos,
        "productos_mayor_rotacion": [
            {"codigo": item.producto_comprado, "total_salidas": item.total_salidas}
            for item in top_productos
        ]
    }
    

  


