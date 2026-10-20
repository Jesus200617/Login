# Sistema de Inventario y Agendamiento de Citas

Proyecto web completo con **Flask + SQLite + Bootstrap 5**.

## 📁 Estructura del proyecto

```
inventario_citas/
├── app.py                 # Backend Flask (vistas + API REST)
├── schema.sql              # Esquema de la base de datos
├── requirements.txt         # Dependencias de Python
├── inventario_citas.db      # Se crea automáticamente al primer arranque
└── templates/
    ├── base.html            # Plantilla base (navbar, Bootstrap)
    ├── index.html            # Dashboard
    ├── inventario.html        # Módulo de inventario
    └── citas.html             # Módulo de citas
```

## 🚀 Instalación paso a paso

### 1. Requisitos previos
- Python 3.9 o superior instalado (verifica con `python --version` o `python3 --version`).
- No necesitas instalar MySQL ni ningún gestor de base de datos aparte: SQLite viene incluido en Python.

### 2. Crear un entorno virtual (recomendado)

```bash
# Dentro de la carpeta inventario_citas/
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS / Linux:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear la base de datos

La base de datos se genera **automáticamente** la primera vez que ejecutas `app.py`,
usando `schema.sql`. No necesitas hacer nada manual.

Si en algún momento quieres reiniciar la base de datos desde cero (borrar todos los
datos y volver a crear las tablas), simplemente elimina el archivo `inventario_citas.db`
y vuelve a ejecutar `app.py`.

Alternativa manual (opcional), si prefieres crearla tú mismo con el CLI de SQLite:

```bash
sqlite3 inventario_citas.db < schema.sql
```

### 5. Ejecutar el servidor

```bash
python app.py
```

Verás un mensaje similar a:

```
 * Running on http://127.0.0.1:5000
```

### 6. Abrir la aplicación

Abre tu navegador en:

```
http://127.0.0.1:5000
```

Desde ahí podrás navegar entre el **Panel General**, **Inventario** y **Citas**.

## 🧩 Notas técnicas

- El backend expone una **API REST** en `/api/productos` y `/api/citas`
  (GET, POST, PATCH, DELETE) que el frontend consume mediante JavaScript
  (`fetch`), por lo que las tablas se actualizan sin recargar la página.
- Todas las validaciones críticas (campos obligatorios, números no negativos,
  formato de fecha, estados válidos) se hacen también en el servidor, no solo
  en el HTML, para proteger la integridad de los datos.
- Si prefieres usar MySQL en lugar de SQLite, revisa las notas al final de
  `schema.sql` y cambia la conexión en `app.py` (por ejemplo con la librería
  `mysql-connector-python` o `PyMySQL`) en lugar del módulo `sqlite3`.

## 🔧 Solución de problemas comunes

| Problema | Solución |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Activa el entorno virtual y corre `pip install -r requirements.txt` |
| El puerto 5000 está ocupado | Cambia el puerto en la última línea de `app.py`: `app.run(debug=True, port=5001)` |
| Los cambios no se reflejan | Asegúrate de correr con `debug=True` (ya viene así) y de guardar los archivos antes de recargar el navegador |
| Quiero borrar todos los datos | Elimina `inventario_citas.db` y vuelve a ejecutar `python app.py` |
