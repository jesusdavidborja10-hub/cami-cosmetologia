# 🌸 Guía de despliegue — GitHub + Supabase + Vercel

## Paso 1 — Crear la base de datos en Supabase

1. Ve a **https://supabase.com** y crea una cuenta gratis
2. Clic en **"New project"**, ponle nombre (ej: `cami-cosmetologia`)
3. Elige una contraseña segura y región **South America (São Paulo)**
4. Espera que termine de crear (1-2 minutos)
5. Ve a **Settings → Database → Connection string → URI**
6. Copia ese string, se ve así:
   ```
   postgresql://postgres:[TU-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ```
7. Ve a **SQL Editor** y ejecuta esto para crear las tablas:

```sql
CREATE TABLE IF NOT EXISTS usuarios (
    id         SERIAL PRIMARY KEY,
    nombre     TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,
    creado_en  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS citas (
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
);
```

---

## Paso 2 — Subir a GitHub

1. Ve a **https://github.com** y crea una cuenta si no tienes
2. Clic en **"New repository"**, nómbralo `cami-cosmetologia`
3. Déjalo **Public** (o Private si prefieres)
4. En tu computador, abre la carpeta del proyecto y ejecuta:

```bash
git init
git add .
git commit -m "🌸 Cami Cosmetología - primer commit"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/cami-cosmetologia.git
git push -u origin main
```

---

## Paso 3 — Desplegar en Vercel

1. Ve a **https://vercel.com** y crea cuenta (puedes entrar con GitHub)
2. Clic en **"Add New Project"**
3. Selecciona el repositorio `cami-cosmetologia`
4. Antes de hacer clic en Deploy, ve a **"Environment Variables"** y agrega:

   | Nombre | Valor |
   |--------|-------|
   | `DATABASE_URL` | El string de Supabase que copiaste |
   | `SECRET_KEY` | Una cadena aleatoria larga (ej: `mi-clave-super-secreta-2024`) |

5. Clic en **"Deploy"** — en 1-2 minutos tu sitio estará en línea

---

## ✅ Resultado

Tu sitio quedará en una URL como:
```
https://cami-cosmetologia.vercel.app
```

La base de datos vive en Supabase de forma permanente — los usuarios y citas **nunca se pierden**.

---

## 🔄 Actualizar el sitio después

Cada vez que hagas cambios:
```bash
git add .
git commit -m "descripción del cambio"
git push
```
Vercel lo detecta automáticamente y redespliega en segundos.

---

## ⚠️ Nota importante

Si quieres probar localmente con la base de datos de Supabase, crea un archivo `.env` (no lo subas a GitHub, ya está en .gitignore):
```
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxx.supabase.co:5432/postgres
SECRET_KEY=cualquier-clave-local
```
E instala `python-dotenv`:
```bash
pip install python-dotenv
```
Y agrega al inicio de `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```
