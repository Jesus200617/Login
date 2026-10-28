import sqlite3
import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from flask import Flask, g, jsonify, render_template, request, session, redirect, url_for
from functools import wraps

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "inventario_citas.db"
SCHEMA = BASE_DIR / "schema.sql"

app = Flask(__name__)
app.secret_key = 'OMgGo9@UN6o41gvTO?'
app.config['PERMANENT_SESSION_LIFETIME'] = False

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
# DECORADOR DE AUTENTICACIÓN (Definido antes de usarse en las rutas)
# ------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ------------------------------------------------------------------
# Login y logout
# ------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form if request.form.get("usuario") else request.get_json(silent=True) or {}
        usuario = data.get("usuario", "").strip()
        password = data.get("password", "").strip()

        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE usuario = ? AND password = ?", (usuario, password)).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["usuario"] = user["usuario"]
            session["rol"] = user["rol"]
            return redirect(url_for("index"))
        else:
            return render_template("/templates/login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------------
# RUTAS DE VISTAS (páginas HTML protegidas)
# ------------------------------------------------------------------
@app.route("/")
@login_required
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
@login_required
def inventario_view():
    """Página del módulo de inventario."""
    return render_template("inventario.html")


@app.route("/citas")
@login_required
def citas_view():
    """Página del módulo de citas."""
    return render_template("citas.html")


# ------------------------------------------------------------------
# API REST — SHOWS
# ------------------------------------------------------------------
@app.route("/api/shows", methods=["GET"])
@login_required
def api_listar_shows():
    db = get_db()
    shows = db.execute("SELECT * FROM tipos_show ORDER BY id").fetchall()
    return jsonify([dict(s) for s in shows])


# ------------------------------------------------------------------
# API REST — PRODUCTOS
# ------------------------------------------------------------------
@app.route("/api/productos", methods=["GET"])
@login_required
def api_listar_productos():
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
@login_required
def api_crear_producto():
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
@login_required
def api_actualizar_stock(producto_id):
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
@login_required
def api_eliminar_producto(producto_id):
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
@login_required
def api_listar_citas():
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
@login_required
def api_crear_cita():
    data = request.get_json(silent=True) or {}
    cliente_nombre = (data.get("cliente_nombre") or "").strip()
    contacto = (data.get("contacto") or "").strip()
    fecha = (data.get("fecha") or "").strip()
    hora = (data.get("hora") or "").strip()
    tipo_show_id = data.get("tipo_show_id")
    productos_ids = data.get("productos_ids", [])

    if not cliente_nombre or not fecha or not hora or not tipo_show_id:
        return jsonify({"error": "Nombre del cliente, fecha, hora y tipo de show son obligatorios."}), 400

    db = get_db()
    show = db.execute("SELECT * FROM tipos_show WHERE id = ?", (tipo_show_id,)).fetchone()
    if not show:
        return jsonify({"error": "Tipo de show no válido."}), 400

    if len(productos_ids) > show["max_juegos"]:
        return jsonify({"error": f"El show '{show['nombre']}' solo permite hasta {show['max_juegos']} juegos."}), 400

    for pid in productos_ids:
        prod = db.execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if not prod or prod["cantidad"] < 1:
            return jsonify({"error": f"El juego '{prod['nombre'] if prod else pid}' no tiene stock suficiente."}), 400

    cursor = db.execute(
        """INSERT INTO citas (cliente_nombre, contacto, fecha, hora, tipo_show_id, costo_total, estado)
           VALUES (?, ?, ?, ?, ?, ?, 'Pendiente')""",
        (cliente_nombre, contacto, fecha, hora, tipo_show_id, show["precio"]),
    )
    cita_id = cursor.lastrowid

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
@login_required
def api_actualizar_estado_cita(cita_id):
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
@login_required
def api_eliminar_cita(cita_id):
    db = get_db()
    cita = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    if cita is None:
        return jsonify({"error": "Cita no encontrada."}), 404
    db.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
    db.commit()
    return jsonify({"mensaje": "Cita eliminada correctamente."})


# ------------------------------------------------------------------
# Punto de entrada (Al final del archivo)
# ------------------------------------------------------------------
def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    if not DATABASE.exists():
        print("Base de datos no encontrada. Creando estructura desde schema.sql...")
        init_db()
        print(f"Base de datos creada en: {DATABASE}")

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(0.8, abrir_navegador).start()
        
    app.run(debug=True, host="127.0.0.1", port=5000)