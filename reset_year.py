"""
Script para limpiar transacciones de un año específico y reimportar desde CSV.
Uso: python reset_year.py 2025
"""
import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from models import Transaccion

def reset_year(anio):
    app = create_app()
    with app.app_context():
        # Eliminar transacciones del año especificado
        eliminadas = Transaccion.query.filter(
            db.extract('year', Transaccion.fecha) == anio
        ).delete()
        db.session.commit()
        
        print(f"Eliminadas {eliminadas} transacciones del año {anio}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python reset_year.py 2025")
        sys.exit(1)
    
    anio = int(sys.argv[1])
    reset_year(anio)