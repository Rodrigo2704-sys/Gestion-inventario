-- 1. Crear la base de datos y seleccionarla
CREATE DATABASE IF NOT EXISTS GestionVentas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE GestionVentas;

-- 2. Tabla de Roles
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY, 
    Nombre VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO roles (id, nombre) VALUES
(1, "Administrador"),
(2, "Empleado");

-- 3. Tabla de Usuarios (Con campos extra de seguridad y control de tokens)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(50) NOT NULL,
    correo VARCHAR(50) NOT NULL UNIQUE, 
    password VARCHAR(100) NOT NULL,
    rol_id INT NOT NULL DEFAULT 2,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    correo_verificado TINYINT(1) NOT NULL DEFAULT 0,
    intentos_fallidos INT NOT NULL DEFAULT 0,          -- 👈 Nuevo: Para control de bloqueos por contraseña errónea
    bloqueado_hasta DATETIME NULL,                     -- 👈 Nuevo: Hora hasta la que el usuario estará bloqueado
    token_version INT NOT NULL DEFAULT 0,              -- 👈 Nuevo: Para invalidar JWTs si cambia contraseña o cierra sesión
    CONSTRAINT FK_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Tabla de Códigos de Verificación / Recuperación de Contraseña
CREATE TABLE IF NOT EXISTS codigos_verificacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    proposito VARCHAR(30) NOT NULL,                    -- Ej: 'recuperacion_password', 'verificar_correo'
    codigo_hash VARCHAR(64) NOT NULL,                  -- El código (hasheado o plano según prefieras)
    expira_en DATETIME NOT NULL,
    intentos INT NOT NULL DEFAULT 0,
    usado TINYINT(1) NOT NULL DEFAULT 0,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_codigos_verificacion_usuario_id (usuario_id),/*Como la tabla codigos_verificacion va a ir acumulando códigos viejos con el paso del tiempo, cada búsqueda se haría más lenta. Al colocarle un INDEX a usuario_id, MySQL crea un mapa rápido de búsqueda para que, al momento de filtrar por ese usuario, la respuesta sea instantánea, sin importar si la tabla tiene 10 o 100,000 registros.*/
    CONSTRAINT fk_codigos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Tabla de Productos
CREATE TABLE IF NOT EXISTS productos (
    Codigo VARCHAR(50) PRIMARY KEY, 
    Nombre VARCHAR(50) NOT NULL,
    Descripcion VARCHAR(255) NOT NULL,
    Categoria VARCHAR(255) NOT NULL,
    Precio_compra DECIMAL(10,2) NOT NULL,
    Precio_venta DECIMAL(10,2) NOT NULL,
    stock_maximo INT NOT NULL,
    stock_minimo INT NOT NULL,
    stock_actual INT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Tabla de Registro de Entradas (Inventario)
CREATE TABLE IF NOT EXISTS registro_entradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cantidad INT NOT NULL,
    costo_unitario DECIMAL(10,2) NOT NULL,
    nota VARCHAR(255) NOT NULL DEFAULT 'Sin nota',
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_codigo VARCHAR(50) NOT NULL,
    CONSTRAINT FK_Entradas_producto FOREIGN KEY(producto_codigo) REFERENCES productos(Codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Tabla de Historial y Auditoría de Movimientos
CREATE TABLE IF NOT EXISTS Historial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    producto_comprado VARCHAR(50) NOT NULL,
    fecha_realizada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_historial_usuario FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_historial_producto FOREIGN KEY(producto_comprado) REFERENCES productos(Codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
