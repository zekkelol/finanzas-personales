"""
Script para importar datos desde data_export.json a PostgreSQL de Render.
Se ejecuta desde la consola de Render: python import_data.py
"""
import os
import json
import sys
from app import create_app
from models import db, Cuenta, Categoria, Transaccion, Presupuesto, Meta

def import_data():
    json_file = os.path.join(os.path.dirname(__file__), 'data_export.json')
    
    if not os.path.exists(json_file):
        print("❌ No se encontró data_export.json")
        print("Primero subí el archivo con git push")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    app = create_app()
    
    with app.app_context():
        # Importar cuentas
        for cuenta_data in data.get('cuentas', []):
            existente = Cuenta.query.filter_by(
                id=cuenta_data['id']
            ).first()
            if not existente:
                cuenta = Cuenta(
                    id=cuenta_data['id'],
                    nombre=cuenta_data['nombre'],
                    tipo=cuenta_data['tipo'],
                    saldo_inicial=cuenta_data['saldo_inicial'],
                    moneda=cuenta_data['moneda'],
                    activa=cuenta_data['activa'],
                )
                db.session.add(cuenta)
        db.session.flush()
        print(f"✅ Cuentas importadas: {len(data.get('cuentas', []))}")
        
        # Importar categorias
        for cat_data in data.get('categorias', []):
            existente = Categoria.query.filter_by(
                id=cat_data['id']
            ).first()
            if not existente:
                cat = Categoria(
                    id=cat_data['id'],
                    nombre=cat_data['nombre'],
                    tipo=cat_data['tipo'],
                    icono=cat_data['icono'],
                    color=cat_data['color'],
                )
                db.session.add(cat)
        db.session.flush()
        print(f"✅ Categorías importadas: {len(data.get('categorias', []))}")
        
        # Importar transacciones
        count = 0
        for trans_data in data.get('transacciones', []):
            existente = Transaccion.query.filter_by(
                id=trans_data['id']
            ).first()
            if not existente:
                trans = Transaccion(
                    id=trans_data['id'],
                    descripcion=trans_data['descripcion'],
                    monto=trans_data['monto'],
                    tipo=trans_data['tipo'],
                    cuenta_id=trans_data['cuenta_id'],
                    categoria_id=trans_data.get('categoria_id'),
                )
                # Parse fecha
                fecha_str = trans_data['fecha']
                if isinstance(fecha_str, str):
                    from datetime import date
                    parts = fecha_str.split('-')
                    trans.fecha = date(int(parts[0]), int(parts[1]), int(parts[2]))
                else:
                    trans.fecha = fecha_str
                
                db.session.add(trans)
                count += 1
        db.session.flush()
        print(f"✅ Transacciones importadas: {count}")
        
        # Importar presupuestos
        for pres_data in data.get('presupuestos', []):
            existente = Presupuesto.query.filter_by(
                id=pres_data['id']
            ).first()
            if not existente:
                pres = Presupuesto(
                    id=pres_data['id'],
                    monto=pres_data['monto'],
                    mes=pres_data['mes'],
                    anio=pres_data['anio'],
                    categoria_id=pres_data['categoria_id'],
                )
                db.session.add(pres)
        db.session.flush()
        print(f"✅ Presupuestos importados: {len(data.get('presupuestos', []))}")
        
        # Importar metas
        for meta_data in data.get('metas', []):
            existente = Meta.query.filter_by(
                id=meta_data['id']
            ).first()
            if not existente:
                meta = Meta(
                    id=meta_data['id'],
                    nombre=meta_data['nombre'],
                    monto_objetivo=meta_data['monto_objetivo'],
                    monto_actual=meta_data['monto_actual'],
                    descripcion=meta_data.get('descripcion'),
                    activa=meta_data['activa'],
                    cuenta_id=meta_data.get('cuenta_id'),
                )
                # Parse fecha_limite si existe
                if meta_data.get('fecha_limite'):
                    fecha_str = meta_data['fecha_limite']
                    if isinstance(fecha_str, str):
                        from datetime import date
                        parts = fecha_str.split('-')
                        meta.fecha_limite = date(int(parts[0]), int(parts[1]), int(parts[2]))
                    else:
                        meta.fecha_limite = fecha_str
                
                db.session.add(meta)
        db.session.flush()
        print(f"✅ Metas importadas: {len(data.get('metas', []))}")
        
        db.session.commit()
        print("\n🎉 ¡Todos los datos importados exitosamente!")
        print("Podés verificar entrando a tu app en Render.")


if __name__ == '__main__':
    print("🔄 Importando datos a PostgreSQL de Render...")
    print()
    import_data()
