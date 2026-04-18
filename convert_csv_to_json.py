"""
Script para convertir CSV de gastos de Excel a JSON compatible con la app.
Uso: python convert_csv_to_json.py archivo.csv
"""
import csv
import json
import sys
import re
from datetime import date

def limpiar_numero(valor):
    """Limpia valores como '$550,000' -> 550000"""
    if not valor or valor.strip() == '':
        return 0
    # Quitar $, espacios, comas, paréntesis (negativos)
    valor = valor.strip()
    es_negativo = '(' in valor or valor.startswith('-')
    valor = re.sub(r'[\$(),]', '', valor).strip()
    valor = valor.replace(',', '')
    try:
        num = float(valor)
        return -num if es_negativo else num
    except:
        return 0

def obtener_o_crear_categoria(nombre, categorias_existentes, cursor):
    """Obtiene ID de categoría o crea nueva"""
    # Normalizar nombre
    nombre_norm = nombre.strip().lower()
    
    # Verificar si existe
    for cat in categorias_existentes:
        if cat['nombre'].lower() == nombre_norm:
            return cat['id']
    
    # Crear nueva categoría
    colores = {
        'tarjeta': '#dc3545',
        'servicio': '#17a2b8',
        'internet': '#6610f2',
        'telefono': '#6f42c1',
        'seguro': '#28a745',
        'credito': '#ffc107',
        'luz': '#fd7e14',
        'gas': '#e83e8c',
        'gym': '#20c997',
        'alquiler': '#6c757d',
        'moto': '#343a40',
        'viaje': '#007bff',
        'ropa': '#d63384',
        'acciones': '#198754',
    }
    
    color = '#6c757d'
    for k, v in colores.items():
        if k in nombre_norm:
            color = v
            break
    
    return None  # Retorna None para que se cree en la app

def convertir_csv_a_json(archivo_csv):
    transacciones = []
    meses = {
        'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4,
        'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
        'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
    }
    
    with open(archivo_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # Buscar fila de meses
    mes_row_idx = None
    for i, row in enumerate(rows):
        if 'Enero' in row:
            mes_row_idx = i
            break
    
    if mes_row_idx is None:
        print("No se encontró la fila de meses")
        return
    
    # Contador para IDs únicos
    transaccion_id = 1
    
    # Procesar cada fila de gasto
    for i in range(mes_row_idx + 1, len(rows)):
        row = rows[i]
        if not row or not row[0].strip():
            continue
        
        nombre_gasto = row[0].strip()
        if nombre_gasto.lower() in ['total', 'gastos', '', ',']:
            continue
        
        if nombre_gasto.startswith(','):
            continue
            
        # Procesar cada mes
        for mes_idx, mes_nombre in enumerate(['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                                               'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']):
            col_idx = mes_row_idx + 1 + mes_idx
            if col_idx < len(row):
                monto = limpiar_numero(row[col_idx])
                if monto > 0:
                    transacciones.append({
                        'id': transaccion_id,
                        'descripcion': nombre_gasto,
                        'monto': monto,
                        'tipo': 'gasto',
                        'fecha': f"2025-{meses[mes_nombre]:02d}-15",
                        'categoria_id': None,
                        'cuenta_id': 1,
                    })
                    transaccion_id += 1
    
    return transacciones

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python convert_csv_to_json.py archivo.csv")
        sys.exit(1)
    
    archivo = sys.argv[1]
    print(f"Convirtiendo {archivo}...")
    
    transacciones = convertir_csv_a_json(archivo)
    
    if transacciones:
        # Crear estructura compatible con importador
        data = {
            'transacciones': transacciones,
            'cuentas': [],
            'categorias': [],
            'presupuestos': [],
            'metas': []
        }
        
        output_file = 'gastos_2025.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Generado: {output_file}")
        print(f"   Total transacciones: {len(transacciones)}")
        print("\nPara importar:")
        print("1. Ve a http://localhost:5000/importar-datos")
        print("2. Sube el archivo gastos_2025.json")
    else:
        print("No se encontraron transacciones")