# Guía de Despliegue - Finanzas Personales

Esta guía te permitirá desplegar tu aplicación en **Render** o **Railway** con autenticación y acceso seguro desde internet.

## Requisitos previos

1. Cuenta en GitHub
2. Cuenta en Render (render.com) o Railway (railway.app)
3. Tu aplicación en un repositorio de GitHub

---

## Opción 1: Despliegue en Render (Recomendado)

### Paso 1: Preparar el repositorio

1. Sube tu código a GitHub:
```bash
cd finanzas
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/tu-usuario/finanzas.git
git push -u origin main
```

### Paso 2: Crear el servicio en Render

1. Ve a [render.com](https://render.com) y crea una cuenta
2. Haz clic en **"New +"** → **"Web Service"**
3. Conecta tu repositorio de GitHub
4. Configura el servicio:
   - **Name**: `finanzas-personales` (o el que quieras)
   - **Region**: Elige la más cercana a ti
   - **Branch**: `main`
   - **Root Directory**: (déjalo vacío)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:create_app()`

### Paso 3: Configurar variables de entorno

En la sección **Environment** de Render, agrega:

```
SECRET_KEY=tu-clave-secreta-muy-larga-y-aleatoria
USUARIO_ADMIN=tu-usuario
PASSWORD_ADMIN=tu-contraseña-segura
DATABASE_URL=sqlite:///finanzas.db
```

### Paso 4: Configurar base de datos persistente (Importante)

Render tiene sistema de archivos efímero, así que necesitas un disco persistente:

1. Ve a **"New +"** → **"Disk"**
2. Crea un disco de 1 GB (o más)
3. En tu Web Service, ve a **"Disks"** y monta el disco en `/app/instance`

O usa PostgreSQL de Render:

1. **New +** → **PostgreSQL**
2. Crea la base de datos
3. Copia la URL de conexión (DATABASE_URL interna)
4. En tu Web Service, agrega la variable `DATABASE_URL` con esa URL

### Paso 5: Desplegar

Haz clic en **"Create Web Service"** y espera a que se complete el despliegue.

¡Listo! Tu aplicación estará disponible en `https://finanzas-personales.onrender.com`

---

## Opción 2: Despliegue en Railway

### Paso 1: Preparar el repositorio

Igual que Render, sube tu código a GitHub.

### Paso 2: Crear el proyecto en Railway

1. Ve a [railway.app](https://railway.app)
2. Inicia sesión con GitHub
3. Haz clic en **"New Project"** → **"Deploy from GitHub repo"**
4. Selecciona tu repositorio `finanzas`

### Paso 3: Configurar variables de entorno

En la pestaña **Variables** de tu servicio, agrega:

```
SECRET_KEY=tu-clave-secreta-muy-larga-y-aleatoria
USUARIO_ADMIN=tu-usuario
PASSWORD_ADMIN=tu-contraseña-segura
```

Railway automáticamente detecta que es Python y usa `gunicorn`.

### Paso 4: Agregar base de datos PostgreSQL

1. Haz clic en **"New"** → **"PostgreSQL"**
2. Railway creará la base de datos automáticamente
3. La variable `DATABASE_URL` se agrega automáticamente

### Paso 5: Desplegar

Railway desplegará automáticamente. Haz clic en **"Generate Domain"** para obtener tu URL.

¡Listo! Tu aplicación estará disponible en `https://tu-proyecto.up.railway.app`

---

## Configuración de Seguridad

### Variables de entorno recomendadas

```bash
# Clave secreta para sesiones (genera una aleatoria)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Usuario y contraseña (cámbialos!)
USUARIO_ADMIN=miusuario
PASSWORD_ADMIN=MiContraseñaSegura123!
```

### Después del despliegue

1. **Inicia sesión** con tus credenciales
2. **Cambia la contraseña** desde "Configurar Usuario" en el menú
3. **Verifica** que todas las rutas están protegidas

---

## Solución de problemas

### Error: "Database locked" (SQLite)

Si usas SQLite en Render, necesitas un disco persistente. Usa PostgreSQL en su lugar.

### Error: "Module not found: gunicorn"

Asegúrate de que `gunicorn` esté en `requirements.txt`.

### La aplicación no carga

Revisa los **logs** en Render/Railway para ver el error específico.

### Las sesiones no persisten

Asegúrate de tener `SECRET_KEY` configurada como variable de entorno.

---

## URLs de acceso

| Plataforma | Formato de URL |
|------------|----------------|
| Render | `https://<nombre>.onrender.com` |
| Railway | `https://<nombre>.up.railway.app` |

---

## Costos

- **Render**: Gratis con limitaciones (se duerme después de 15 min de inactividad en plan free)
- **Railway**: $5/mes de crédito, luego $0.00008333/GB-segundo

---

## Backup de datos

### SQLite
Descarga el archivo `finanzas.db` desde el dashboard de Render (con disco persistente).

### PostgreSQL
Usa las herramientas de backup del proveedor o `pg_dump`.
