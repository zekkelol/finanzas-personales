# AGENTS.md - Finanzas Personales

## Run Commands

```bash
# Development
python run.py

# Production (gunicorn)
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

## Default Credentials

- **Username**: `admin`
- **Password**: `admin123`
- Override with env vars: `USUARIO_ADMIN`, `PASSWORD_ADMIN`

## Database

- Local: SQLite at `finanzas.db`
- Production: PostgreSQL via `DATABASE_URL` env var
- Uses psycopg3 dialect: `postgresql+psycopg://...`

## Migration Notes

- `/importar-datos` - Web interface to import data_export.json
- Run `python migrate_to_render.py` locally first to generate JSON export
- After importing to PostgreSQL: visit `/fix-sequences` once to reset auto-increment IDs

## Session Config

- Timeout: 15 minutes of inactivity
- Persisted via `/api/session/ping` calls from frontend

## Routes Summary

| Path | Description |
|------|-------------|
| `/dashboard` | Main dashboard |
| `/transacciones` | Transaction list with filters |
| `/presupuestos` | Monthly budgets |
| `/reportes` | Monthly/annual reports |
| `/metas` | Savings goals |
| `/tipos-cambio` | Currency exchange rates |

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | All routes, ~1200 lines |
| `models.py` | SQLAlchemy models |
| `config.py` | DB URI, auth, currency config |
| `finanzas.db` | SQLite database |