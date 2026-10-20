DROP TABLE IF EXISTS cita_productos;
DROP TABLE IF EXISTS citas;
DROP TABLE IF EXISTS tipos_show;
DROP TABLE IF EXISTS productos;

CREATE TABLE productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    cantidad        INTEGER NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    precio          REAL NOT NULL CHECK (precio >= 0),
    fecha_creacion  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualiz  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tipos_show (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    max_juegos      INTEGER NOT NULL,
    precio          REAL NOT NULL CHECK (precio >= 0)
);

INSERT INTO tipos_show (nombre, max_juegos, precio) VALUES
('Cuadro chico', 4, 1500.00),
('Cuadro mediano', 6, 2500.00),
('Cuadro grande', 8, 3500.00);

CREATE TABLE citas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nombre  TEXT NOT NULL,
    contacto        TEXT,
    fecha           DATE NOT NULL,
    hora            TIME NOT NULL,
    tipo_show_id    INTEGER NOT NULL,
    costo_total     REAL NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'Pendiente'
                        CHECK (estado IN ('Pendiente', 'Completada', 'Cancelada')),
    fecha_creacion  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo_show_id) REFERENCES tipos_show(id)
);

CREATE TABLE cita_productos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cita_id     INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad    INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (cita_id) REFERENCES citas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);