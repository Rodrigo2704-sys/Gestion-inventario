function ApiRegistrarProducto(datosProducto) {
    return apiFetch("/productos/registrar/producto", {
        metodo: "POST",
        cuerpo: datosProducto
    });
}

function ApiRegistrarStock(datosProducto) {
    return apiFetch("/productos/registrar/stock", {
        metodo: "POST",
        cuerpo: datosProducto
    });
}

function ApiSalidaStock(usuario_id, datosProducto) {
    return apiFetch(`/productos/salida/stock/${encodeURIComponent(usuario_id)}`, {
        metodo: "POST",
        cuerpo: datosProducto
    });
}

function apiActualizarProducto(codigo, datosProducto) {
    return apiFetch(`/productos/actualizar/producto/${encodeURIComponent(codigo)}`, {
        metodo: "PATCH",
        cuerpo: datosProducto
    });
}

function ApiEliminarElProducto(codigo) {
    return apiFetch(`/productos/eliminar/producto/${encodeURIComponent(codigo)}`, {
        metodo: "DELETE" 
    });
}

function ApiBuscarProductosPorCategoria(categoria, skip = 0, limit = 10) {
    return apiFetch(`/productos/categoria/${encodeURIComponent(categoria)}?skip=${skip}&limit=${limit}`);
}

function ApiBuscarProductoCodigo(codigo){
    return apiFetch(`/productos/codigo${encodeURIComponent(codigo)}`,{
        
    });
}
function ApiDashboard(){
    return apiFetch("/productos/dashboard/metricas");

}
