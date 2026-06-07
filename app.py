from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
import os, hashlib, secrets
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=30)
CORS(app)

# ── Google OAuth ───────────────────────────────────────────────────────────────
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# ── Conexión PostgreSQL ────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')

# ── Init DB ────────────────────────────────────────────────────────────────────
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id         SERIAL PRIMARY KEY,
        nombre     TEXT NOT NULL,
        email      TEXT UNIQUE NOT NULL,
        password   TEXT NOT NULL,
        creado_en  TIMESTAMP DEFAULT NOW()
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS citas (
        id         SERIAL PRIMARY KEY,
        usuario_id INTEGER REFERENCES usuarios(id),
        nombre     TEXT NOT NULL,
        telefono   TEXT NOT NULL,
        email      TEXT,
        servicio   TEXT NOT NULL,
        fecha      DATE NOT NULL,
        hora       TEXT NOT NULL,
        notas      TEXT,
        estado     TEXT DEFAULT 'pendiente',
        creada_en  TIMESTAMP DEFAULT NOW()
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS resenas (
        id         SERIAL PRIMARY KEY,
        usuario_id INTEGER REFERENCES usuarios(id),
        nombre     TEXT NOT NULL,
        comentario TEXT NOT NULL,
        estrellas  INTEGER NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
        creada_en  TIMESTAMP DEFAULT NOW()
    )''')
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"DB init warning: {e}")

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ── Páginas ────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html', seccion='inicio', usuario=session.get('usuario'))

@app.route('/citas')
def citas_page():
    return render_template('index.html', seccion='citas', usuario=session.get('usuario'))

@app.route('/contacto')
def contacto_page():
    return render_template('index.html', seccion='contacto', usuario=session.get('usuario'))

@app.route('/ubicacion')
def ubicacion_page():
    return render_template('index.html', seccion='ubicacion', usuario=session.get('usuario'))

@app.route('/login')
def login_page():
    if session.get('usuario'):
        return redirect(url_for('home'))
    return render_template('index.html', seccion='login', usuario=None)

@app.route('/registro')
def registro_page():
    if session.get('usuario'):
        return redirect(url_for('home'))
    return render_template('index.html', seccion='registro', usuario=None)

@app.route('/resenas')
def resenas_page():
    return render_template('index.html', seccion='resenas', usuario=session.get('usuario'))

# ── Auth API ───────────────────────────────────────────────────────────────────
@app.route('/api/registro', methods=['POST'])
def registro():
    data   = request.get_json()
    nombre = data.get('nombre','').strip()
    email  = data.get('email','').strip().lower()
    pw     = data.get('password','')
    if not nombre or not email or not pw:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400
    if len(pw) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('INSERT INTO usuarios (nombre,email,password) VALUES (%s,%s,%s) RETURNING id',
                  (nombre, email, hash_password(pw)))
        uid = c.fetchone()[0]
        conn.commit()
        conn.close()
        session.permanent = True
        session['usuario'] = {'id': uid, 'nombre': nombre, 'email': email}
        return jsonify({'mensaje': f'¡Bienvenida, {nombre}!', 'nombre': nombre})
    except psycopg2.errors.UniqueViolation:
        return jsonify({'error': 'Ese correo ya está registrado'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email','').strip().lower()
    pw       = data.get('password','')
    remember = data.get('remember', False)
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT id,nombre,email FROM usuarios WHERE email=%s AND password=%s',
                  (email, hash_password(pw)))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'Correo o contraseña incorrectos'}), 401
        session.permanent = bool(remember)
        session['usuario'] = {'id': row[0], 'nombre': row[1], 'email': row[2]}
        return jsonify({'mensaje': f'¡Hola de nuevo, {row[1]}!', 'nombre': row[1]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'mensaje': 'Sesión cerrada'})

# ── Google OAuth routes ────────────────────────────────────────────────────────
@app.route('/auth/google')
def auth_google():
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    try:
        token = google.authorize_access_token()
        userinfo = token.get('userinfo')
        if not userinfo:
            return redirect(url_for('login_page'))
        email  = userinfo['email'].strip().lower()
        nombre = userinfo.get('name', email.split('@')[0])
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT id, nombre, email FROM usuarios WHERE email=%s', (email,))
        row = c.fetchone()
        if row:
            uid, nombre_db, email_db = row
            conn.close()
        else:
            placeholder_pw = 'GOOGLE_OAUTH_' + secrets.token_hex(16)
            c.execute('INSERT INTO usuarios (nombre, email, password) VALUES (%s,%s,%s) RETURNING id',
                      (nombre, email, placeholder_pw))
            uid = c.fetchone()[0]
            conn.commit()
            conn.close()
            nombre_db, email_db = nombre, email
        session.permanent = True
        session['usuario'] = {'id': uid, 'nombre': nombre_db, 'email': email_db}
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return redirect(url_for('login_page'))

@app.route('/api/me')
def me():
    u = session.get('usuario')
    if not u:
        return jsonify({'loggedIn': False})
    return jsonify({'loggedIn': True, 'nombre': u['nombre'], 'email': u['email']})

# ── Citas API ──────────────────────────────────────────────────────────────────
HORARIOS = ['09:00','09:30','10:00','10:30','11:00','11:30',
            '12:00','12:30','14:00','14:30','15:00','15:30',
            '16:00','16:30','17:00','17:30','18:00']

@app.route('/api/disponibilidad')
def disponibilidad():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'error': 'Fecha requerida'}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT hora FROM citas WHERE fecha=%s AND estado!='cancelada'", (fecha,))
        ocupados = {r[0] for r in c.fetchall()}
        conn.close()
        return jsonify([{'hora': h, 'disponible': h not in ocupados} for h in HORARIOS])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/citas', methods=['GET'])
def listar_citas():
    u     = session.get('usuario')
    fecha = request.args.get('fecha')
    try:
        conn = get_conn()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if u:
            if fecha:
                c.execute("SELECT * FROM citas WHERE usuario_id=%s AND fecha=%s ORDER BY hora", (u['id'], fecha))
            else:
                c.execute("SELECT * FROM citas WHERE usuario_id=%s AND fecha >= CURRENT_DATE ORDER BY fecha,hora", (u['id'],))
        else:
            if fecha:
                c.execute("SELECT * FROM citas WHERE fecha=%s ORDER BY hora", (fecha,))
            else:
                c.execute("SELECT * FROM citas WHERE fecha >= CURRENT_DATE ORDER BY fecha,hora")
        rows = c.fetchall()
        conn.close()
        # Convertir fecha y datetime a string para JSON
        result = []
        for row in rows:
            d = dict(row)
            if d.get('fecha'): d['fecha'] = str(d['fecha'])
            if d.get('creada_en'): d['creada_en'] = str(d['creada_en'])
            result.append(d)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/citas', methods=['POST'])
def crear_cita():
    data = request.get_json()
    u    = session.get('usuario')
    for f in ['nombre','telefono','servicio','fecha','hora']:
        if not data.get(f):
            return jsonify({'error': f'Campo requerido: {f}'}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id FROM citas WHERE fecha=%s AND hora=%s AND estado!='cancelada'",
                  (data['fecha'], data['hora']))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Ese horario ya está reservado'}), 409
        c.execute('''INSERT INTO citas (usuario_id,nombre,telefono,email,servicio,fecha,hora,notas)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
                  (u['id'] if u else None, data['nombre'], data['telefono'],
                   data.get('email',''), data['servicio'], data['fecha'],
                   data['hora'], data.get('notas','')))
        cita_id = c.fetchone()[0]
        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Cita creada', 'id': cita_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/citas/<int:cid>', methods=['DELETE'])
def cancelar_cita(cid):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE citas SET estado='cancelada' WHERE id=%s", (cid,))
        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Cita cancelada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Reseñas API ────────────────────────────────────────────────────────────────
@app.route('/api/resenas', methods=['GET'])
def listar_resenas():
    try:
        conn = get_conn()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute('SELECT id,nombre,comentario,estrellas,creada_en FROM resenas ORDER BY creada_en DESC')
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            if d.get('creada_en'): d['creada_en'] = str(d['creada_en'])
            result.append(d)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resenas', methods=['POST'])
def crear_resena():
    u = session.get('usuario')
    if not u:
        return jsonify({'error': 'Debes iniciar sesión para publicar una reseña'}), 401
    data = request.get_json()
    comentario = data.get('comentario', '').strip()
    estrellas  = data.get('estrellas')
    if not comentario:
        return jsonify({'error': 'El comentario no puede estar vacío'}), 400
    if not isinstance(estrellas, int) or not (1 <= estrellas <= 5):
        return jsonify({'error': 'La calificación debe ser entre 1 y 5'}), 400
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('INSERT INTO resenas (usuario_id,nombre,comentario,estrellas) VALUES (%s,%s,%s,%s) RETURNING id',
                  (u['id'], u['nombre'], comentario, estrellas))
        rid = c.fetchone()[0]
        conn.commit()
        conn.close()
        return jsonify({'mensaje': '¡Gracias por tu reseña!', 'id': rid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌸 Cami Cosmetología — http://localhost:5000")
    app.run(debug=True, port=5000)
