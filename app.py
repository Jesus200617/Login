import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, g, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "inventario_citas.db"
SCHEMA = BASE_DIR / "schema.sql"

app = Flask(__name__)

def get_db():
    """
    Devuelve una conexión SQLite reutilizable dentro del contexto de la
    petición actual.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Cierra la conexión a la base de datos al finalizar cada petición."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea las tablas ejecutando schema.sql."""
    with app.app_context():
        db = get_db()
        with open(SCHEMA, "r", encoding="utf-8") as f:
            db.executescript(f.read())
        db.commit()


# ------------------------------------------------------------------
# RUTAS DE VISTAS (páginas HTML)
# ------------------------------------------------------------------
@app.route("/")
def index():
    """Página principal / dashboard."""
    db = get_db()
    total_productos = db.execute("SELECT COUNT(*) AS c FROM productos").fetchone()["c"]
    stock_bajo = db.execute(
        "SELECT COUNT(*) AS c FROM productos WHERE cantidad <= 5"
    ).fetchone()["c"]
    citas_pendientes = db.execute(
        "SELECT COUNT(*) AS c FROM citas WHERE estado = 'Pendiente'"
    ).fetchone()["c"]
    return render_template(
        "index.html",
        total_productos=total_productos,
        stock_bajo=stock_bajo,
        citas_pendientes=citas_pendientes,
    )


@app.route("/inventario")
def inventario_view():
    """Página del módulo de inventario."""
    return render_template("inventario.html")


@app.route("/citas")
def citas_view():
    """Página del módulo de citas."""
    return render_template("citas.html")


# ------------------------------------------------------------------
# API REST — SHOWS
# ------------------------------------------------------------------
@app.route("/api/shows", methods=["GET"])
def api_listar_shows():
    """Lista los niveles de show disponibles (Cuadro chico, mediano, grande)."""
    db = get_db()
    shows = db.execute("SELECT * FROM tipos_show ORDER BY id").fetchall()
    return jsonify([dict(s) for s in shows])


# ------------------------------------------------------------------
# API REST — PRODUCTOS
# ------------------------------------------------------------------
@app.route("/api/productos", methods=["GET"])
def api_listar_productos():
    """Lista productos/juegos en el inventario."""
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        filas = db.execute(
            "SELECT * FROM productos WHERE nombre LIKE ? ORDER BY nombre",
            (f"%{q}%",),
        ).fetchall()
    else:
        filas = db.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    return jsonify([dict(f) for f in filas])


@app.route("/api/productos", methods=["POST"])
def api_crear_producto():
    """Registra un nuevo producto/juego."""
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    descripcion = (data.get("descripcion") or "").strip()
    cantidad = data.get("cantidad", 0)
    precio = data.get("precio", 0)

    if not nombre:
        return jsonify({"error": "El nombre del producto es obligatorio."}), 400
    try:
        cantidad = int(cantidad)
        precio = float(precio)
        if cantidad < 0 or precio < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Cantidad y precio deben ser números válidos y no negativos."}), 400

    db = get_db()
    cursor = db.execute(
        """INSERT INTO productos (nombre, descripcion, cantidad, precio)
           VALUES (?, ?, ?, ?)""",
        (nombre, descripcion, cantidad, precio),
    )
    db.commit()
    nuevo = db.execute("SELECT * FROM productos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(nuevo)), 201


@app.route("/api/productos/<int:producto_id>/stock", methods=["PATCH"])
def api_actualizar_stock(producto_id):
    """Actualiza la cantidad en stock de un juego."""
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "El valor 'delta' debe ser un número entero."}), 400

    db = get_db()
    producto = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if producto is None:
        return jsonify({"error": "Producto no encontrado."}), 404

    nueva_cantidad = producto["cantidad"] + delta
    if nueva_cantidad < 0:
        return jsonify({"error": "El stock no puede quedar en negativo."}), 400

    db.execute(
        "UPDATE productos SET cantidad = ?, fecha_actualiz = ? WHERE id = ?",
        (nueva_cantidad, datetime.now().isoformat(timespec="seconds"), producto_id),
    )
    db.commit()
    actualizado = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    return jsonify(dict(actualizado))


@app.route("/api/productos/<int:producto_id>", methods=["DELETE"])
def api_eliminar_producto(producto_id):
    """Elimina un producto."""
    db = get_db()
    producto = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if producto is None:
        return jsonify({"error": "Producto no encontrado."}), 404
    db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    db.commit()
    return jsonify({"mensaje": "Producto eliminado correctamente."})


# ------------------------------------------------------------------
# API REST — CITAS Y RESUMEN DE EVENTO
# ------------------------------------------------------------------
@app.route("/api/citas", methods=["GET"])
def api_listar_citas():
    """Obtiene la lista de citas agendadas con su show y juegos seleccionados."""
    db = get_db()
    citas = db.execute(
        """SELECT c.*, s.nombre AS nombre_show 
           FROM citas c 
           JOIN tipos_show s ON c.tipo_show_id = s.id 
           ORDER BY c.fecha, c.hora"""
    ).fetchall()
    
    resultado = []
    for cita in citas:
        c_dict = dict(cita)
        # Buscar juegos asociados a esta cita
        juegos = db.execute(
            """SELECT p.nombre 
               FROM cita_productos cp 
               JOIN productos p ON cp.producto_id = p.id 
               WHERE cp.cita_id = ?""",
            (cita["id"],)
        ).fetchall()
        c_dict["juegos"] = [j["nombre"] for j in juegos]
        resultado.append(c_dict)

    return jsonify(resultado)


@app.route("/api/citas", methods=["POST"])
def api_crear_cita():
    """
    Agendas cita, valida max_juegos del show seleccionado,
    y descuenta automáticamente 1 unidad del inventario por cada juego elegido.
    """
    data = request.get_json(silent=True) or {}
    cliente_nombre = (data.get("cliente_nombre") or "").strip()
    contacto = (data.get("contacto") or "").strip()
    fecha = (data.get("fecha") or "").strip()
    hora = (data.get("hora") or "").strip()
    tipo_show_id = data.get("tipo_show_id")
    productos_ids = data.get("productos_ids", [])  # Lista de IDs de los juegos/productos elegidos

    if not cliente_nombre or not fecha or not hora or not tipo_show_id:
        return jsonify({"error": "Nombre del cliente, fecha, hora y tipo de show son obligatorios."}), 400

    db = get_db()
    show = db.execute("SELECT * FROM tipos_show WHERE id = ?", (tipo_show_id,)).fetchone()
    if not show:
        return jsonify({"error": "Tipo de show no válido."}), 400

    if len(productos_ids) > show["max_juegos"]:
        return jsonify({"error": f"El show '{show['nombre']}' solo permite hasta {show['max_juegos']} juegos."}), 400

    # Verificar stock disponible de cada juego seleccionado
    for pid in productos_ids:
        prod = db.execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if not prod or prod["cantidad"] < 1:
            return jsonify({"error": f"El juego '{prod['nombre'] if prod else pid}' no tiene stock suficiente."}), 400

    # Registrar la cita con el costo del show seleccionado
    cursor = db.execute(
        """INSERT INTO citas (cliente_nombre, contacto, fecha, hora, tipo_show_id, costo_total, estado)
           VALUES (?, ?, ?, ?, ?, ?, 'Pendiente')""",
        (cliente_nombre, contacto, fecha, hora, tipo_show_id, show["precio"]),
    )
    cita_id = cursor.lastrowid

    # Asociar juegos y descontar del inventario
    for pid in productos_ids:
        db.execute("INSERT INTO cita_productos (cita_id, producto_id) VALUES (?, ?)", (cita_id, pid))
        db.execute(
            "UPDATE productos SET cantidad = cantidad - 1, fecha_actualiz = ? WHERE id = ?", 
            (datetime.now().isoformat(timespec="seconds"), pid)
        )

    db.commit()

    nueva = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    return jsonify(dict(nueva)), 201


@app.route("/api/citas/<int:cita_id>/estado", methods=["PATCH"])
def api_actualizar_estado_cita(cita_id):
    """Cambia el estado de una cita."""
    data = request.get_json(silent=True) or {}
    nuevo_estado = (data.get("estado") or "").strip()
    estados_validos = {"Pendiente", "Completada", "Cancelada"}

    if nuevo_estado not in estados_validos:
        return jsonify({"error": f"Estado inválido. Use uno de: {', '.join(estados_validos)}"}), 400

    db = get_db()
    cita = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    if cita is None:
        return jsonify({"error": "Cita no encontrada."}), 404

    db.execute("UPDATE citas SET estado = ? WHERE id = ?", (nuevo_estado, cita_id))
    db.commit()
    actualizada = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    return jsonify(dict(actualizada))


@app.route("/api/citas/<int:cita_id>", methods=["DELETE"])
def api_eliminar_cita(cita_id):
    """Elimina una cita."""
    db = get_db()
    cita = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    if cita is None:
        return jsonify({"error": "Cita no encontrada."}), 404
    db.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
    db.commit()
    return jsonify({"mensaje": "Cita eliminada correctamente."})


# ------------------------------------------------------------------
# Punto de entrada
# ------------------------------------------------------------------
if __name__ == "__main__":
    if not DATABASE.exists():
        print("Base de datos no encontrada. Creando estructura desde schema.sql...")
        init_db()
        print(f"Base de datos creada en: {DATABASE}")

    app.run(debug=True, host="127.0.0.1", port=5000)