"""
Script para exportar datos de la base de datos local SQLite a PostgreSQL de Render.
Uso local: python migrate_to_render.py
"""
import os
import json
from datetime import datetime
import sqlite3
import subprocess
import sys

# Configuración
LOCAL_DB = os.path.join(os.path.dirname(__file__), 'finanzas.db')

def export_local_data():
    """Exporta todos los datos de SQLite local a JSON"""
    if not os.path.exists(LOCAL_DB):
        print("❌ No se encontró la base de datos local (finanzas.db)")
        return None
    
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    data = {}
    
    # Exportar cuentas
    try:
        cursor.execute("SELECT * FROM cuentas")
        data['cuentas'] = [dict(row) for row in cursor.fetchall()]
        print(f"✅ Cuentas exportadas: {len(data['cuentas'])}")
    except Exception as e:
        print(f"⚠️ Error exportando cuentas: {e}")
        data['cuentas'] = []
    
    # Exportar categorias
    try:
        cursor.execute("SELECT * FROM categorias")
        data['categorias'] = [dict(row) for row in cursor.fetchall()]
        print(f"✅ Categorías exportadas: {len(data['categorias'])}")
    except Exception as e:
        print(f"⚠️ Error exportando categorías: {e}")
        data['categorias'] = []
    
    # Exportar transacciones
    try:
        cursor.execute("SELECT * FROM transacciones")
        rows = cursor.fetchall()
        data['transacciones'] = []
        for row in rows:
            item = dict(row)
            # Convertir fechas a string
            if item.get('fecha'):
                item['fecha'] = item['fecha']
            data['transacciones'].append(item)
        print(f"✅ Transacciones exportadas: {len(data['transacciones'])}")
    except Exception as e:
        print(f"⚠️ Error exportando transacciones: {e}")
        data['transacciones'] = []
    
    # Exportar presupuestos
    try:
        cursor.execute("SELECT * FROM presupuestos")
        data['presupuestos'] = [dict(row) for row in cursor.fetchall()]
        print(f"✅ Presupuestos exportados: {len(data['presupuestos'])}")
    except Exception as e:
        print(f"⚠️ Error exportando presupuestos: {e}")
        data['presupuestos'] = []
    
    # Exportar metas
    try:
        cursor.execute("SELECT * FROM metas")
        data['metas'] = [dict(row) for row in cursor.fetchall()]
        print(f"✅ Metas exportadas: {len(data['metas'])}")
    except Exception as e:
        print(f"⚠️ Error exportando metas: {e}")
        data['metas'] = []
    
    conn.close()
    
    # Guardar a JSON
    output_file = os.path.join(os.path.dirname(__file__), 'data_export.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n📦 Datos exportados a: {output_file}")
    return output_file


def print_instructions():
    """Imprime instrucciones para importar en Render"""
    print("\n" + "="*60)
    print("📋 INSTRUCCIONES PARA IMPORTAR EN RENDER:")
    print("="*60)
    print()
    print("1. Copiá el archivo data_export.json a tu repo de GitHub:")
    print("   git add data_export.json")
    print("   git commit -m 'Add data export for migration'")
    print("   git push origin main")
    print()
    print("2. Una vez que Render haga deploy, entrá a la consola:")
    print("   - Andá a tu Web Service en Render")
    print("   - Click en 'Shell' (tab)")
    print("   - Ejecutá: python import_data.py")
    print()
    print("3. Después de importar, borrá el archivo data_export.json")
    print("   por seguridad (contiene tus datos):")
    print("   git rm data_export.json")
    print("   git commit -m 'Remove exported data'")
    print("   git push origin main")
    print()


if __name__ == '__main__':
    print("🔄 Migrando datos de SQLite local a JSON...")
    print()
    
    result = export_local_data()
    
    if result:
        print_instructions()
    else:
        print("\n❌ No se pudo exportar. Asegurate de tener finanzas.db en el directorio.")
