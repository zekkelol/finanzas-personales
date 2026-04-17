"""
Script para arreglar el problema de IDs duplicados en PostgreSQL.
Ejecutar UNA SOLA VEZ después de migrar o importar datos.
"""
from app import create_app, db
from models import Transaccion, Cuenta, Categoria, Meta, Presupuesto

def fix_sequence_ids():
    app = create_app()
    
    with app.app_context():
        print("🔧 Arreglando secuencias de IDs en PostgreSQL...")
        
        # Arreglar transacciones
        max_id = db.session.query(db.func.max(Transaccion.id)).scalar() or 0
        db.session.execute(db.text(f"SELECT setval('transacciones_id_seq', {max_id})"))
        print(f"   ✓ Transacciones: siguiente ID será {max_id + 1}")
        
        # Arreglar cuentas
        max_id = db.session.query(db.func.max(Cuenta.id)).scalar() or 0
        db.session.execute(db.text(f"SELECT setval('cuentas_id_seq', {max_id})"))
        print(f"   ✓ Cuentas: siguiente ID será {max_id + 1}")
        
        # Arreglar categorias
        max_id = db.session.query(db.func.max(Categoria.id)).scalar() or 0
        db.session.execute(db.text(f"SELECT setval('categorias_id_seq', {max_id})"))
        print(f"   ✓ Categorías: siguiente ID será {max_id + 1}")
        
        # Arreglar presupuestos
        max_id = db.session.query(db.func.max(Presupuesto.id)).scalar() or 0
        db.session.execute(db.text(f"SELECT setval('presupuestos_id_seq', {max_id})"))
        print(f"   ✓ Presupuestos: siguiente ID será {max_id + 1}")
        
        # Arreglar metas
        max_id = db.session.query(db.func.max(Meta.id)).scalar() or 0
        db.session.execute(db.text(f"SELECT setval('metas_id_seq', {max_id})"))
        print(f"   ✓ Metas: siguiente ID será {max_id + 1}")
        
        db.session.commit()
        print("\n✅ Secuencias arregladas! Ya no deberías tener errores de IDs duplicados.")

if __name__ == '__main__':
    fix_sequence_ids()
