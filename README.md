# 🌸 Cami Cosmetología — Web App

Sitio web completo con secciones de Inicio, Citas, Contacto, Ubicación e Inicio de sesión.

## Tecnologías
- **Backend:** Python + Flask
- **Base de datos:** SQLite (se crea automáticamente como `cami.db`)
- **Frontend:** HTML, CSS, JavaScript vanilla

---

## Instalación y ejecución

### 1. Instalar dependencias
```bash
pip install flask flask-cors
```

### 2. Ejecutar el servidor
```bash
python app.py
```

### 3. Abrir en el navegador
```
http://localhost:5000
```

---

## Secciones del sitio

| Ruta | Sección |
|------|---------|
| `/` | Inicio + servicios |
| `/citas` | Apartar y ver citas |
| `/contacto` | Formulario de contacto |
| `/ubicacion` | Mapa y dirección |
| `/login` | Iniciar sesión |
| `/registro` | Crear cuenta nueva |

---

## Sistema de usuarios

- Las contraseñas se guardan **hasheadas** (SHA-256)
- El checkbox "Recordar mi sesión" mantiene la sesión activa al cerrar el navegador
- Cada usuario solo ve **sus propias citas** al estar logueado

---

## Base de datos (SQLite)

### Tabla `usuarios`
- id, nombre, email, password (hash), creado_en

### Tabla `citas`
- id, usuario_id, nombre, telefono, email, servicio, fecha, hora, notas, estado, creada_en

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/registro` | Crear cuenta |
| POST | `/api/login` | Iniciar sesión |
| POST | `/api/logout` | Cerrar sesión |
| GET | `/api/me` | Estado del usuario |
| GET | `/api/disponibilidad?fecha=YYYY-MM-DD` | Horarios disponibles |
| GET | `/api/citas` | Listar citas |
| POST | `/api/citas` | Crear cita |
| DELETE | `/api/citas/<id>` | Cancelar cita |
