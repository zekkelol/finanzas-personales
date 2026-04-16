import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-cambia-en-produccion'
    
    # Database URL
    _database_url = os.environ.get('DATABASE_URL')
    if _database_url and _database_url.startswith('postgresql://'):
        # psycopg3 usa el dialecto postgresql+psycopg://
        SQLALCHEMY_DATABASE_URI = _database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    else:
        SQLALCHEMY_DATABASE_URI = _database_url or \
            'sqlite:///' + os.path.join(basedir, 'finanzas.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Autenticación
    USUARIO_ADMIN = os.environ.get('USUARIO_ADMIN') or 'admin'
    PASSWORD_ADMIN = os.environ.get('PASSWORD_ADMIN') or 'admin123'

    # Configuración de presupuestos
    DEFAULT_BUDGET_PERIOD = 'monthly'

    # Moneda
    CURRENCY_SYMBOL = '$'
    CURRENCY_CODE = 'USD'
