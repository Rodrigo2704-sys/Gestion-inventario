const API_BASE_URL = "http://127.0.0.1:8000";
const PAGINA_LOGIN = "login.html";

function obtenerToken(){
    return localStorage.getItem("token");
}

function cerrarSesion(){
    localStorage.removeItem("token");
    localStorage.removeItem("nombre_usuario")
    localStorage.removeItem("rol")
    window.location.href=PAGINA_LOGIN;
}

function mensajeDeError(data,estado){
    if (estado===429) return "Demasiados intentos. Espera un minuto e intentalo de nuevo.";
    if (estado>=500) return "Error en el servidor, intentalo de nuevo mas tarde."

/*Si lanzas el error a mano con tu raise HTTPException en el backend (ej. "Contraseña incorrecta"), FastAPI lo manda como un simple texto (string), por lo que entra directo en la primera condición y se muestra tal cual.

Si es un error automático de validación de FastAPI/Pydantic (ej. faltó rellenar un espacio, el correo no tiene formato válido, etc.), FastAPI lo empaqueta en una lista (array), por lo que pasa de largo la primera condición y entra en el bloque del Array.isArray(detalle) para limpiarlo y unirlo.*/

    const detalle = data && data.detail;
    if (typeof detalle === "string") return detalle;

    // Agarra la lista de errores que manda FastAPI, le borra las palabras feas y técnicas a cada uno, y los une todos en un solo párrafo limpio y ordenado para mostrárselo al usuario de una sola pasada.
    if (Array.isArray(detalle)) {
        return detalle.map(d => String(d.msg).replace(/^Value error, /, "")).join(". ");
    }
    return "No se pudo completar la operación.";
}


function crearError(mensaje, estado) {
    const error = new Error(mensaje); // 1. Crea el error con el texto (ej: "Sesión expirada")
    error.status = estado;            // 2. Le inyecta la propiedad 'status' (ej: 401)
    return error;                     // 3. Devuelve el error listo para usarse
}

//mensajeDeError se encarga de qué texto decir.

//crearError se encarga de empaquetar ese texto junto con su número HTTP (.status) para que el resto de tu aplicación pueda leer el número y tomar decisiones inteligentes.


//Usamos get por defecto, pero si vamos a usar otro metodo toda añadirlo manualmente con su cuerpo.
async function apiFetch(ruta, { metodo = "GET", cuerpo = null, autenticado = true, formulario = false } = {}) {
    const headers = {};

    if (autenticado) {
        const token = obtenerToken();
        if (!token) {
            cerrarSesion();
            //Cuando JavaScript se encuentra con un throw, cancela inmediatamente la ejecución de lo que estaba haciendo y bota un error.
            throw crearError("Sesión no iniciada.", 401);
        }
        headers["Authorization"] = `Bearer ${token}`;
    }

    let body;
    if (cuerpo !== null) {
        if (formulario) {
            body = cuerpo; // URLSearchParams (el login de FastAPI no acepta JSON)
            headers["Content-Type"] = "application/x-www-form-urlencoded";
        } else {
            body = JSON.stringify(cuerpo);
            headers["Content-Type"] = "application/json";
        }
    }

    let respuesta;
    try {
        respuesta = await fetch(`${API_BASE_URL}${ruta}`, { method: metodo, headers, body });
    } catch (error) {
        throw crearError("No se pudo conectar con el servidor.", 0);
    }

    // Si el cuerpo viene vacío o no es JSON, no queremos que reviente aquí.
    let data = null;
    try {
        data = await respuesta.json();
    } catch (error) { /* sin cuerpo JSON */ }

    if (!respuesta.ok) {
        console.error("Error desde la API:", respuesta.status, data);

        // Token vencido o inválido: se limpia la sesión y se manda al login.
        if (respuesta.status === 401 && autenticado) {
            cerrarSesion();
            throw crearError("Tu sesión expiró. Inicia sesión de nuevo.", 401);
        }
        throw crearError(mensajeDeError(data, respuesta.status), respuesta.status);
    }

    return data;
}
