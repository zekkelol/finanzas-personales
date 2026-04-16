"""
Página web para importar datos desde JSON.
Se usa desde el navegador cuando no hay acceso a la Shell de Render.
"""
import json
import os
from datetime import date

def importar_desde_json(app, db, Cuenta, Categoria, Transaccion, Presupuesto, Meta):
    """
    Función que se llama desde una ruta web para importar datos.
    """
    from flask import render_template_string, request, flash, redirect, url_for
    
    HTML_TEMPLATE = """
    {% extends "base.html" %}
    {% block title %}Importar Datos - Finanzas Personales{% endblock %}
    {% block content %}
    <div class="container mt-4">
        <h2><i class="fas fa-download me-2"></i>Importar Datos</h2>
        <p class="text-muted">Subí tu archivo data_export.json para importar tus datos.</p>
        
        {% if mensaje %}
            <div class="alert alert-{{ tipo }}">{{ mensaje }}</div>
        {% endif %}
        
        <form method="POST" enctype="multipart/form-data" class="card p-4">
            <div class="mb-3">
                <label for="archivo" class="form-label">Archivo JSON</label>
                <input type="file" class="form-control" id="archivo" name="archivo" accept=".json" required>
            </div>
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-upload me-2"></i>Importar Datos
            </button>
            <a href="{{ url_for('dashboard') }}" class="btn btn-secondary ms-2">Volver al Dashboard</a>
        </form>
        
        <hr>
        <h5 class="mt-4">¿Cómo obtener el archivo JSON?</h5>
        <ol>
            <li>Ejecutá localmente: <code>python migrate_to_render.py</code></li>
            <li>Se generará un archivo <code>data_export.json</code></li>
            <li>Subilo aquí con el formulario de arriba</li>
        </ol>
    </div>
    {% endblock %}
    """
    
    @app.route('/importar-datos', methods=['GET', 'POST'])
    def importar_datos():
        if 'usuario_id' not in app.config.get('SESSION_KEY', 'session'):
            from flask import session
            if 'usuario_id' not in session:
                from flask import redirect, url_for
                return redirect(url_for('login'))
        
        mensaje = None
        tipo = 'info'
        
        if request.method == 'POST':
            archivo = request.files.get('archivo')
            
            if not archivo or archivo.filename == '':
                mensaje = 'No se seleccionó ningún archivo'
                tipo = 'danger'
            elif not archivo.filename.endswith('.json'):
                mensaje = 'El archivo debe ser .json'
                tipo = 'danger'
            else:
                try:
                    contenido = archivo.read().decode('utf-8')
                    data = json.loads(contenido)
                    
                    count_cuentas = 0
                    count_categorias = 0
                    count_transacciones = 0
                    count_presupuestos = 0
                    count_metas = 0
                    
                    # Importar cuentas
                    for cuenta_data in data.get('cuentas', []):
                        existente = Cuenta.query.filter_by(id=cuenta_data['id']).first()
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
                            count_cuentas += 1
                    
                    db.session.flush()
                    
                    # Importar categorias
                    for cat_data in data.get('categorias', []):
                        existente = Categoria.query.filter_by(id=cat_data['id']).first()
                        if not existente:
                            cat = Categoria(
                                id=cat_data['id'],
                                nombre=cat_data['nombre'],
                                tipo=cat_data['tipo'],
                                icono=cat_data['icono'],
                                color=cat_data['color'],
                            )
                            db.session.add(cat)
                            count_categorias += 1
                    
                    db.session.flush()
                    
                    # Importar transacciones
                    for trans_data in data.get('transacciones', []):
                        existente = Transaccion.query.filter_by(id=trans_data['id']).first()
                        if not existente:
                            trans = Transaccion(
                                id=trans_data['id'],
                                descripcion=trans_data['descripcion'],
                                monto=trans_data['monto'],
                                tipo=trans_data['tipo'],
                                cuenta_id=trans_data['cuenta_id'],
                                categoria_id=trans_data.get('categoria_id'),
                            )
                            fecha_str = trans_data['fecha']
                            if isinstance(fecha_str, str):
                                parts = fecha_str.split('-')
                                trans.fecha = date(int(parts[0]), int(parts[1]), int(parts[2]))
                            else:
                                trans.fecha = fecha_str
                            db.session.add(trans)
                            count_transacciones += 1
                    
                    db.session.flush()
                    
                    # Importar presupuestos
                    for pres_data in data.get('presupuestos', []):
                        existente = Presupuesto.query.filter_by(id=pres_data['id']).first()
                        if not existente:
                            pres = Presupuesto(
                                id=pres_data['id'],
                                monto=pres_data['monto'],
                                mes=pres_data['mes'],
                                anio=pres_data['anio'],
                                categoria_id=pres_data['categoria_id'],
                            )
                            db.session.add(pres)
                            count_presupuestos += 1
                    
                    db.session.flush()
                    
                    # Importar metas
                    for meta_data in data.get('metas', []):
                        existente = Meta.query.filter_by(id=meta_data['id']).first()
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
                            if meta_data.get('fecha_limite'):
                                fecha_str = meta_data['fecha_limite']
                                if isinstance(fecha_str, str):
                                    parts = fecha_str.split('-')
                                    meta.fecha_limite = date(int(parts[0]), int(parts[1]), int(parts[2]))
                                else:
                                    meta.fecha_limite = fecha_str
                            db.session.add(meta)
                            count_metas += 1
                    
                    db.session.commit()
                    
                    mensaje = (
                        f"✅ Datos importados exitosamente: "
                        f"{count_cuentas} cuentas, {count_categorias} categorías, "
                        f"{count_transacciones} transacciones, "
                        f"{count_presupuestos} presupuestos, {count_metas} metas"
                    )
                    tipo = 'success'
                    
                except json.JSONDecodeError:
                    mensaje = '❌ El archivo JSON no es válido'
                    tipo = 'danger'
                except Exception as e:
                    db.session.rollback()
                    mensaje = f'❌ Error importando datos: {str(e)}'
                    tipo = 'danger'
                    import traceback
                    print(f"Error en importación: {traceback.format_exc()}")
        
        return render_template_string(HTML_TEMPLATE, mensaje=mensaje, tipo=tipo)
    
    return importar_datos
