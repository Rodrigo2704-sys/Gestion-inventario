async function apiIniciarSesion(correo,password){
    //Te permite armar ese paquete con formato de formulario línea por línea.
    const datos=new URLSearchParams();
    datos.append("username",correo);
    datos.append("password",password);

    const data=await apiFetch("/usuarios/login",{
        metodo:"POST",
        cuerpo:datos,
        autenticado:false,
        formulario:true


});

localStorage.setItem("token",data.acces_token);
localStorage.setItem("nombre_usuario",data.nombre);
localStorage.setItem("rol",data.rol);
return data;

}

/** 1. Registrar usuario (Envía JSON y no pide estar autenticado) */
function apiRegistrarUsuario(datosusuario) {
    return apiFetch("/usuarios/registrar", {
        metodo: "POST",
        cuerpo: datosusuario,
        autenticado: false
    });
}

/*En FastAPI, cuando pones un dato simple (como un número int o un texto str) suelto en los paréntesis de la función y no está en la URL, FastAPI por defecto asume que lo vas a mandar como un parámetro de consulta (Query Parameter), es decir, pegado a la URL después del signo de interrogación (?nuevo_rol_id=2).*/

function ApiCambiarRol(usuario_id, nuevo_rol_id) {
    return apiFetch(`/usuarios/${encodeURIComponent(usuario_id)}/cambiar-rol?nuevo_rol_id=${nuevo_rol_id}`, {
        metodo: "PATCH"
    });
}

/** 3. Buscar por correo (El correo lleva símbolos especiales, por lo que se blinda con encode) */
function ApiBuscarCorreo(email) {
    return apiFetch(`/usuarios/buscar/correo?email=${encodeURIComponent(email)}`);
}

function ApiUsuarioId(usuario_id) {
    return apiFetch(`/usuarios/${encodeURIComponent(usuario_id)}`);
}


function ApiObtenerUsuarios(skip=0,limit=100){
    return apiFetch(`/usuarios/obtener/usuarios?skip=${skip}&limit=${limit}`)

}

function apiActualizarUsuario(usuarioId, datosActualizacion) {
    return apiFetch(`/usuarios/${encodeURIComponent(usuarioId)}/actualizar_usuario`, {
        metodo: "PATCH",
        cuerpo: datosActualizacion 
    });
}

/*Put: registro completo actualizar
PATCH: actualizar solo unos campos*/
function ApiCambiarContrasena(datos) {
    return apiFetch(`/usuarios/cambiar-contrasena`, {
        metodo: "POST",
        cuerpo: datos    
    });
}

/** DELETE /usuarios/{usuario_id} */
function apiBorrarUsuario(usuarioId) {
    return apiFetch(`/usuarios/${encodeURIComponent(usuarioId)}`, {
        metodo: "DELETE" 
    });
}