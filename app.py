from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
from functools import wraps
from config import Config
from models import db, Cuenta, Categoria, Transaccion, Presupuesto, Meta, Usuario
from datetime import datetime, timedelta, date
from sqlalchemy import func
import io
import csv
import json

# Configuración de sesión
SESSION_TIMEOUT_MINUTES = 15  # Tiempo de inactividad para cerrar sesión

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login', next=request.url))
        
        # Verificar timeout de sesión
        last_activity = session.get('last_activity')
        if last_activity:
            last_activity_time = datetime.fromisoformat(last_activity)
            timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            if datetime.now() - last_activity_time > timeout:
                session.clear()
                flash('Tu sesión ha expirado por inactividad. Por favor, iniciá sesión nuevamente.', 'warning')
                return redirect(url_for('login', next=request.url))
        
        # Actualizar última actividad
        session['last_activity'] = datetime.now().isoformat()
        
        return f(*args, **kwargs)
    return decorated_function

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Context processor para funciones auxiliares
    @app.context_processor
    def utility_processor():
        def today():
            return datetime.now().date()
        return {'today': today}

    db.init_app(app)

    with app.app_context():
        db.create_all()
        crear_usuario_por_defecto()
        crear_categorias_por_defecto()

    # Rutas de autenticación
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            usuario = Usuario.query.filter_by(username=username).first()

            if usuario and usuario.check_password(password):
                session['usuario_id'] = usuario.id
                session['username'] = usuario.username
                session['last_activity'] = datetime.now().isoformat()
                flash(f'Bienvenido, {usuario.username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuario o contraseña incorrectos', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Has cerrado sesión exitosamente', 'info')
        return redirect(url_for('login'))

    @app.route('/importar-datos', methods=['GET', 'POST'])
    @login_required
    def importar_datos():
        """Página web para importar datos desde JSON (para usuarios sin acceso a Shell)"""
        
        HTML_TEMPLATE = """
        {% extends "base.html" %}
        {% block title %}Importar Datos - Finanzas Personales{% endblock %}
        {% block content %}
        <div class="container mt-4">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            <h4 class="mb-0"><i class="fas fa-download me-2"></i>Importar Datos desde Local</h4>
                        </div>
                        <div class="card-body">
                            {% if mensaje %}
                                <div class="alert alert-{{ tipo }} alert-dismissible fade show" role="alert">
                                    {{ mensaje }}
                                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                </div>
                            {% endif %}
                            
                            <p class="text-muted">Subí tu archivo data_export.json para importar todos tus datos.</p>
                            
                            <form method="POST" enctype="multipart/form-data">
                                <div class="mb-3">
                                    <label for="archivo" class="form-label">Archivo JSON</label>
                                    <input type="file" class="form-control form-control-lg" id="archivo" name="archivo" accept=".json" required>
                                </div>
                                <button type="submit" class="btn btn-primary btn-lg">
                                    <i class="fas fa-upload me-2"></i>Importar Todos los Datos
                                </button>
                                <a href="{{ url_for('dashboard') }}" class="btn btn-secondary ms-2">Cancelar</a>
                            </form>
                            
                            <hr class="my-4">
                            <h5>¿Cómo obtener el archivo JSON?</h5>
                            <ol>
                                <li>En tu computadora, andá a la carpeta del proyecto</li>
                                <li>Ejecutá: <code>python migrate_to_render.py</code></li>
                                <li>Se generará un archivo <code>data_export.json</code></li>
                                <li>Subilo aquí con el formulario de arriba</li>
                            </ol>
                            
                            <div class="alert alert-warning mt-3">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                <strong>Nota:</strong> Esto no duplica datos. Si ya existen transacciones con el mismo ID, se saltan.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """
        
        mensaje = None
        tipo = 'info'
        
        if request.method == 'POST':
            archivo = request.files.get('archivo')
            
            if not archivo or archivo.filename == '':
                mensaje = '❌ No se seleccionó ningún archivo'
                tipo = 'danger'
            elif not archivo.filename.endswith('.json'):
                mensaje = '❌ El archivo debe ser .json'
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
        
        from flask import render_template_string
        return render_template_string(HTML_TEMPLATE, mensaje=mensaje, tipo=tipo)

    @app.route('/configurar-usuario', methods=['GET', 'POST'])
    def configurar_usuario():
        """Ruta para cambiar usuario y contraseña"""
        if 'usuario_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            nuevo_username = request.form.get('nuevo_username')
            nueva_password = request.form.get('nueva_password')
            password_actual = request.form.get('password_actual')

            usuario = Usuario.query.get(session['usuario_id'])

            if not usuario.check_password(password_actual):
                flash('Contraseña actual incorrecta', 'danger')
                return render_template('configurar_usuario.html', usuario=usuario)

            if nuevo_username:
                usuario.username = nuevo_username
            if nueva_password:
                usuario.set_password(nueva_password)

            db.session.commit()
            flash('Credenciales actualizadas exitosamente', 'success')
            return redirect(url_for('dashboard'))

        usuario = Usuario.query.get(session['usuario_id'])
        return render_template('configurar_usuario.html', usuario=usuario)

    # Rutas principales
    @app.route('/')
    def index():
        if 'usuario_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Resumen general
        cuentas = Cuenta.query.filter_by(activa=True).all()
        total_activos = sum(c.saldo_actual for c in cuentas)

        # Transacciones recientes
        transacciones_recentes = Transaccion.query.order_by(
            Transaccion.fecha.desc()
        ).limit(10).all()

        # Ingresos vs gastos del mes
        hoy = datetime.now().date()
        inicio_mes = hoy.replace(day=1)

        ingresos_mes = db.session.query(func.sum(Transaccion.monto)).filter(
            Transaccion.tipo == 'ingreso',
            Transaccion.fecha >= inicio_mes
        ).scalar() or 0

        gastos_mes = db.session.query(func.sum(Transaccion.monto)).filter(
            Transaccion.tipo == 'gasto',
            Transaccion.fecha >= inicio_mes
        ).scalar() or 0

        # Gastos por categoría (mes actual)
        gastos_por_categoria = db.session.query(
            Categoria.nombre,
            Categoria.color,
            func.sum(Transaccion.monto).label('total')
        ).join(Transaccion).filter(
            Transaccion.tipo == 'gasto',
            Transaccion.fecha >= inicio_mes,
            Transaccion.categoria_id == Categoria.id
        ).group_by(Categoria.id).all()

        # Presupuestos del mes
        presupuestos = Presupuesto.query.filter_by(
            mes=hoy.month,
            anio=hoy.year
        ).all()

        # Metas activas
        metas = Meta.query.filter_by(activa=True).all()

        return render_template('dashboard.html',
                               cuentas=cuentas,
                               total_activos=total_activos,
                               transacciones_recentes=transacciones_recentes,
                               ingresos_mes=ingresos_mes,
                               gastos_mes=gastos_mes,
                               gastos_por_categoria=gastos_por_categoria,
                               presupuestos=presupuestos,
                               metas=metas,
                               mes_actual=hoy.strftime('%B %Y'))

    @app.route('/cuentas')
    @login_required
    def cuentas():
        todas_cuentas = Cuenta.query.order_by(Cuenta.created_at.desc()).all()
        return render_template('cuentas.html', cuentas=todas_cuentas)

    @app.route('/cuentas/nueva', methods=['GET', 'POST'])
    @login_required
    def nueva_cuenta():
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            tipo = request.form.get('tipo')
            saldo_inicial = float(request.form.get('saldo_inicial', 0))
            moneda = request.form.get('moneda', 'USD')

            cuenta = Cuenta(
                nombre=nombre,
                tipo=tipo,
                saldo_inicial=saldo_inicial,
                moneda=moneda
            )
            db.session.add(cuenta)
            db.session.commit()
            flash('Cuenta creada exitosamente', 'success')
            return redirect(url_for('cuentas'))

        return render_template('cuenta_form.html', cuenta=None)

    @app.route('/cuentas/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_cuenta(id):
        cuenta = Cuenta.query.get_or_404(id)

        if request.method == 'POST':
            cuenta.nombre = request.form.get('nombre')
            cuenta.tipo = request.form.get('tipo')
            cuenta.saldo_inicial = float(request.form.get('saldo_inicial', 0))
            cuenta.moneda = request.form.get('moneda', 'USD')
            cuenta.activa = request.form.get('activa') == 'on'

            db.session.commit()
            flash('Cuenta actualizada exitosamente', 'success')
            return redirect(url_for('cuentas'))

        return render_template('cuenta_form.html', cuenta=cuenta)

    @app.route('/cuentas/eliminar/<int:id>', methods=['POST'])
    @login_required
    def eliminar_cuenta(id):
        cuenta = Cuenta.query.get_or_404(id)
        db.session.delete(cuenta)
        db.session.commit()
        flash('Cuenta eliminada exitosamente', 'success')
        return redirect(url_for('cuentas'))

    @app.route('/transacciones')
    @login_required
    def transacciones():
        filtro = request.args.get('filtro', 'todas')
        cuenta_id = request.args.get('cuenta_id', type=int)

        query = Transaccion.query.order_by(Transaccion.fecha.desc())

        if filtro == 'ingresos':
            query = query.filter_by(tipo='ingreso')
        elif filtro == 'gastos':
            query = query.filter_by(tipo='gasto')

        if cuenta_id:
            query = query.filter_by(cuenta_id=cuenta_id)

        todas_transacciones = query.all()
        cuentas = Cuenta.query.filter_by(activa=True).all()

        return render_template('transacciones.html',
                               transacciones=todas_transacciones,
                               cuentas=cuentas,
                               filtro=filtro,
                               cuenta_seleccionada=cuenta_id)

    @app.route('/transacciones/nueva', methods=['GET', 'POST'])
    @login_required
    def nueva_transaccion():
        categorias = Categoria.query.all()
        cuentas = Cuenta.query.filter_by(activa=True).all()
        
        if not cuentas:
            flash('Primero necesitás crear una cuenta', 'warning')
            return redirect(url_for('nueva_cuenta'))
        
        if request.method == 'POST':
            try:
                descripcion = request.form.get('descripcion', '').strip()
                monto_str = request.form.get('monto', '0')
                tipo = request.form.get('tipo', 'gasto')
                fecha_str = request.form.get('fecha')
                cuenta_id_str = request.form.get('cuenta_id')
                categoria_id_str = request.form.get('categoria_id')

                # Validaciones
                if not descripcion:
                    flash('La descripción es obligatoria', 'danger')
                    return render_template('transaccion_form.html',
                                           transaccion=None,
                                           categorias=categorias,
                                           cuentas=cuentas)
                
                try:
                    monto = float(monto_str) if monto_str else 0
                except:
                    monto = 0
                
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else datetime.now().date()
                except:
                    fecha = datetime.now().date()
                
                try:
                    cuenta_id = int(cuenta_id_str) if cuenta_id_str else None
                except:
                    flash('Seleccioná una cuenta válida', 'danger')
                    return render_template('transaccion_form.html',
                                           transaccion=None,
                                           categorias=categorias,
                                           cuentas=cuentas)
                
                categoria_id = int(categoria_id_str) if categoria_id_str else None

                transaccion = Transaccion(
                    descripcion=descripcion,
                    monto=monto,
                    tipo=tipo,
                    fecha=fecha,
                    cuenta_id=cuenta_id,
                    categoria_id=categoria_id
                )
                db.session.add(transaccion)
                db.session.commit()
                flash('Transacción registrada exitosamente', 'success')
                return redirect(url_for('transacciones'))
                
            except Exception as e:
                flash(f'Error al guardar: {str(e)}', 'danger')
                db.session.rollback()
                import traceback
                traceback.print_exc()

        return render_template('transaccion_form.html',
                               transaccion=None,
                               categorias=categorias,
                               cuentas=cuentas)

    @app.route('/transacciones/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_transaccion(id):
        transaccion = Transaccion.query.get_or_404(id)

        if request.method == 'POST':
            transaccion.descripcion = request.form.get('descripcion')
            transaccion.monto = float(request.form.get('monto'))
            transaccion.tipo = request.form.get('tipo')
            transaccion.fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
            transaccion.cuenta_id = int(request.form.get('cuenta_id'))
            transaccion.categoria_id = int(request.form.get('categoria_id')) if request.form.get('categoria_id') else None

            db.session.commit()
            flash('Transacción actualizada exitosamente', 'success')
            return redirect(url_for('transacciones'))

        categorias = Categoria.query.all()
        cuentas = Cuenta.query.filter_by(activa=True).all()
        return render_template('transaccion_form.html',
                               transaccion=transaccion,
                               categorias=categorias,
                               cuentas=cuentas)

    @app.route('/transacciones/eliminar/<int:id>', methods=['POST'])
    @login_required
    def eliminar_transaccion(id):
        transaccion = Transaccion.query.get_or_404(id)
        db.session.delete(transaccion)
        db.session.commit()
        flash('Transacción eliminada exitosamente', 'success')
        return redirect(url_for('transacciones'))

    @app.route('/categorias')
    @login_required
    def categorias():
        categorias_ingresos = Categoria.query.filter_by(tipo='ingreso').all()
        categorias_gastos = Categoria.query.filter_by(tipo='gasto').all()
        return render_template('categorias.html',
                               categorias_ingresos=categorias_ingresos,
                               categorias_gastos=categorias_gastos)

    @app.route('/categorias/nueva', methods=['GET', 'POST'])
    @login_required
    def nueva_categoria():
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            tipo = request.form.get('tipo')
            icono = request.form.get('icono', 'fa-tag')
            color = request.form.get('color', '#6c757d')

            categoria = Categoria(
                nombre=nombre,
                tipo=tipo,
                icono=icono,
                color=color
            )
            db.session.add(categoria)
            db.session.commit()
            flash('Categoría creada exitosamente', 'success')
            return redirect(url_for('categorias'))

        return render_template('categoria_form.html', categoria=None)

    @app.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_categoria(id):
        categoria = Categoria.query.get_or_404(id)

        if request.method == 'POST':
            categoria.nombre = request.form.get('nombre')
            categoria.tipo = request.form.get('tipo')
            categoria.icono = request.form.get('icono', 'fa-tag')
            categoria.color = request.form.get('color', '#6c757d')

            db.session.commit()
            flash('Categoría actualizada exitosamente', 'success')
            return redirect(url_for('categorias'))

        return render_template('categoria_form.html', categoria=categoria)

    @app.route('/categorias/eliminar/<int:id>', methods=['POST'])
    @login_required
    def eliminar_categoria(id):
        categoria = Categoria.query.get_or_404(id)
        db.session.delete(categoria)
        db.session.commit()
        flash('Categoría eliminada exitosamente', 'success')
        return redirect(url_for('categorias'))

    @app.route('/presupuestos')
    @login_required
    def presupuestos():
        hoy = datetime.now().date()
        presupuestos = Presupuesto.query.filter_by(
            mes=hoy.month,
            anio=hoy.year
        ).all()

        # Calcular gasto actual por categoría
        inicio_mes = hoy.replace(day=1)
        gastos_por_categoria = db.session.query(
            Transaccion.categoria_id,
            func.sum(Transaccion.monto).label('total')
        ).filter(
            Transaccion.tipo == 'gasto',
            Transaccion.fecha >= inicio_mes
        ).group_by(Transaccion.categoria_id).all()

        gastos_dict = {g.categoria_id: g.total for g in gastos_por_categoria}

        return render_template('presupuestos.html',
                               presupuestos=presupuestos,
                               gastos_dict=gastos_dict,
                               mes_actual=hoy.strftime('%B %Y'))

    @app.route('/presupuestos/nuevo', methods=['GET', 'POST'])
    @login_required
    def nuevo_presupuesto():
        if request.method == 'POST':
            categoria_id = int(request.form.get('categoria_id'))
            monto = float(request.form.get('monto'))
            mes = int(request.form.get('mes'))
            anio = int(request.form.get('anio'))

            # Verificar si ya existe
            existente = Presupuesto.query.filter_by(
                categoria_id=categoria_id,
                mes=mes,
                anio=anio
            ).first()

            if existente:
                existente.monto = monto
                flash('Presupuesto actualizado exitosamente', 'success')
            else:
                presupuesto = Presupuesto(
                    categoria_id=categoria_id,
                    monto=monto,
                    mes=mes,
                    anio=anio
                )
                db.session.add(presupuesto)
                flash('Presupuesto creado exitosamente', 'success')

            db.session.commit()
            return redirect(url_for('presupuestos'))

        categorias_gastos = Categoria.query.filter_by(tipo='gasto').all()
        hoy = datetime.now().date()
        return render_template('presupuesto_form.html',
                               categorias=categorias_gastos,
                               mes_actual=hoy.month,
                               anio_actual=hoy.year)

    @app.route('/metas')
    @login_required
    def metas():
        todas_metas = Meta.query.order_by(Meta.activa.desc(), Meta.created_at.desc()).all()
        return render_template('metas.html', metas=todas_metas)

    @app.route('/metas/nueva', methods=['GET', 'POST'])
    @login_required
    def nueva_meta():
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            monto_objetivo = float(request.form.get('monto_objetivo'))
            fecha_limite = None
            if request.form.get('fecha_limite'):
                fecha_limite = datetime.strptime(request.form.get('fecha_limite'), '%Y-%m-%d').date()
            descripcion = request.form.get('descripcion')
            cuenta_id = int(request.form.get('cuenta_id')) if request.form.get('cuenta_id') else None

            meta = Meta(
                nombre=nombre,
                monto_objetivo=monto_objetivo,
                fecha_limite=fecha_limite,
                descripcion=descripcion,
                cuenta_id=cuenta_id
            )
            db.session.add(meta)
            db.session.commit()
            flash('Meta creada exitosamente', 'success')
            return redirect(url_for('metas'))

        cuentas = Cuenta.query.filter_by(activa=True).all()
        return render_template('meta_form.html', meta=None, cuentas=cuentas)

    @app.route('/metas/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_meta(id):
        meta = Meta.query.get_or_404(id)

        if request.method == 'POST':
            meta.nombre = request.form.get('nombre')
            meta.monto_objetivo = float(request.form.get('monto_objetivo'))
            meta.monto_actual = float(request.form.get('monto_actual', 0))
            if request.form.get('fecha_limite'):
                meta.fecha_limite = datetime.strptime(request.form.get('fecha_limite'), '%Y-%m-%d').date()
            meta.descripcion = request.form.get('descripcion')
            meta.cuenta_id = int(request.form.get('cuenta_id')) if request.form.get('cuenta_id') else None
            meta.activa = request.form.get('activa') == 'on'

            db.session.commit()
            flash('Meta actualizada exitosamente', 'success')
            return redirect(url_for('metas'))

        cuentas = Cuenta.query.filter_by(activa=True).all()
        return render_template('meta_form.html', meta=meta, cuentas=cuentas)

    @app.route('/metas/eliminar/<int:id>', methods=['POST'])
    @login_required
    def eliminar_meta(id):
        meta = Meta.query.get_or_404(id)
        db.session.delete(meta)
        db.session.commit()
        flash('Meta eliminada exitosamente', 'success')
        return redirect(url_for('metas'))

    @app.route('/metas/<int:id>/abonar', methods=['POST'])
    @login_required
    def abonar_meta(id):
        meta = Meta.query.get_or_404(id)
        monto = float(request.form.get('monto'))
        meta.monto_actual += monto
        db.session.commit()
        flash(f'Abono de ${monto:,.2f} registrado en la meta "{meta.nombre}"', 'success')
        return redirect(url_for('metas'))

    @app.route('/reportes')
    @login_required
    def reportes():
        hoy = datetime.now().date()
        
        # Obtener mes y año seleccionado (por defecto: mes actual)
        mes = request.args.get('mes', type=int, default=hoy.month)
        anio = request.args.get('anio', type=int, default=hoy.year)
        ver_anual = request.args.get('anual', type=int, default=0)
        
        # Meses en español
        meses_espanol = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        if ver_anual == 1:
            # Vista anual: todos los meses del año
            anio_actual = anio
            resumen_anual = []
            total_ingresos_anual = 0
            total_gastos_anual = 0
            categorias_anuales = {}
            
            for m in range(1, 13):
                inicio_mes = date(anio_actual, m, 1)
                if m == 12:
                    fin_mes = date(anio_actual + 1, 1, 1) - timedelta(days=1)
                else:
                    fin_mes = date(anio_actual, m + 1, 1) - timedelta(days=1)
                
                ingresos_mes = db.session.query(func.sum(Transaccion.monto)).filter(
                    Transaccion.tipo == 'ingreso',
                    Transaccion.fecha >= inicio_mes,
                    Transaccion.fecha <= fin_mes
                ).scalar() or 0
                
                gastos_mes = db.session.query(func.sum(Transaccion.monto)).filter(
                    Transaccion.tipo == 'gasto',
                    Transaccion.fecha >= inicio_mes,
                    Transaccion.fecha <= fin_mes
                ).scalar() or 0
                
                # Gastos por categoría del mes
                gastos_por_cat = db.session.query(
                    Categoria.nombre,
                    func.sum(Transaccion.monto).label('total')
                ).join(Transaccion).filter(
                    Transaccion.tipo == 'gasto',
                    Transaccion.fecha >= inicio_mes,
                    Transaccion.fecha <= fin_mes
                ).group_by(Categoria.id).all()
                
                for cat in gastos_por_cat:
                    if cat.nombre not in categorias_anuales:
                        categorias_anuales[cat.nombre] = 0
                    categorias_anuales[cat.nombre] += float(cat.total)
                
                resumen_anual.append({
                    'mes': m,
                    'nombre': meses_espanol[m-1],
                    'ingresos': float(ingresos_mes),
                    'gastos': float(gastos_mes),
                    'balance': float(ingresos_mes) - float(gastos_mes)
                })
                
                total_ingresos_anual += float(ingresos_mes)
                total_gastos_anual += float(gastos_mes)
            
            # Ordenar categorías por total gastado
            categorias_anuales = dict(sorted(categorias_anuales.items(), key=lambda x: x[1], reverse=True))
            
            # Años disponibles (basados en transacciones)
            anios_disponibles = db.session.query(
                func.extract('year', Transaccion.fecha).label('anio')
            ).distinct().all()
            anios_disponibles = sorted([int(a.anio) for a in anios_disponibles])
            if not anios_disponibles:
                anios_disponibles = [hoy.year]
            
            return render_template('reportes.html',
                                   modo='anual',
                                   anio=anio_actual,
                                   resumen_anual=resumen_anual,
                                   total_ingresos_anual=total_ingresos_anual,
                                   total_gastos_anual=total_gastos_anual,
                                   total_balance_anual=total_ingresos_anual - total_gastos_anual,
                                   categorias_anuales=categorias_anuales,
                                   anios_disponibles=anios_disponibles,
                                   anios_espanol=meses_espanol)
        else:
            # Vista mensual
            inicio_mes = date(anio, mes, 1)
            if mes == 12:
                fin_mes = date(anio + 1, 1, 1) - timedelta(days=1)
            else:
                fin_mes = date(anio, mes + 1, 1) - timedelta(days=1)
            
            # Resumen del mes
            ingresos_mes = db.session.query(func.sum(Transaccion.monto)).filter(
                Transaccion.tipo == 'ingreso',
                Transaccion.fecha >= inicio_mes,
                Transaccion.fecha <= fin_mes
            ).scalar() or 0
            
            gastos_mes = db.session.query(func.sum(Transaccion.monto)).filter(
                Transaccion.tipo == 'gasto',
                Transaccion.fecha >= inicio_mes,
                Transaccion.fecha <= fin_mes
            ).scalar() or 0
            
            # Transacciones del mes
            transacciones_mes = Transaccion.query.filter(
                Transaccion.fecha >= inicio_mes,
                Transaccion.fecha <= fin_mes
            ).order_by(Transaccion.fecha.desc()).all()
            
            # Gastos por categoría del mes
            gastos_por_categoria = db.session.query(
                Categoria.nombre,
                Categoria.color,
                func.sum(Transaccion.monto).label('total')
            ).join(Transaccion).filter(
                Transaccion.tipo == 'gasto',
                Transaccion.fecha >= inicio_mes,
                Transaccion.fecha <= fin_mes
            ).group_by(Categoria.id).all()
            
            # Ingresos por categoría del mes
            ingresos_por_categoria = db.session.query(
                Categoria.nombre,
                Categoria.color,
                func.sum(Transaccion.monto).label('total')
            ).join(Transaccion).filter(
                Transaccion.tipo == 'ingreso',
                Transaccion.fecha >= inicio_mes,
                Transaccion.fecha <= fin_mes
            ).group_by(Categoria.id).all()
            
            # Top gastos del mes
            top_gastos = Transaccion.query.filter(
                Transaccion.tipo == 'gasto',
                Transaccion.fecha >= inicio_mes,
                Transaccion.fecha <= fin_mes
            ).order_by(Transaccion.monto.desc()).limit(5).all()
            
            # Años disponibles
            anios_disponibles = db.session.query(
                func.extract('year', Transaccion.fecha).label('anio')
            ).distinct().all()
            anios_disponibles = sorted([int(a.anio) for a in anios_disponibles])
            if not anios_disponibles:
                anios_disponibles = [hoy.year]
            
            return render_template('reportes.html',
                                   modo='mensual',
                                   mes=mes,
                                   anio=anio,
                                   mes_nombre=meses_espanol[mes-1],
                                   ingresos_mes=float(ingresos_mes),
                                   gastos_mes=float(gastos_mes),
                                   balance_mes=float(ingresos_mes) - float(gastos_mes),
                                   transacciones_mes=transacciones_mes,
                                   gastos_por_categoria=gastos_por_categoria,
                                   ingresos_por_categoria=ingresos_por_categoria,
                                   top_gastos=top_gastos,
                                   anios_disponibles=anios_disponibles,
                                   anios_espanol=meses_espanol)

    @app.route('/reportes/exportar/csv')
    @login_required
    def exportar_csv():
        transacciones = Transaccion.query.order_by(Transaccion.fecha.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Descripción', 'Tipo', 'Monto', 'Cuenta', 'Categoría'])

        for t in transacciones:
            writer.writerow([
                t.fecha.strftime('%Y-%m-%d'),
                t.descripcion,
                t.tipo,
                f"{t.monto:.2f}",
                t.cuenta.nombre,
                t.categoria.nombre if t.categoria else ''
            ])

        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=transacciones.csv'
        response.headers['Content-type'] = 'text/csv'
        return response

    # API para datos de gráficos
    @app.route('/api/dashboard/gastos-categorias')
    @login_required
    def api_gastos_categorias():
        hoy = datetime.now().date()
        inicio_mes = hoy.replace(day=1)

        gastos = db.session.query(
            Categoria.nombre,
            func.sum(Transaccion.monto).label('total')
        ).join(Transaccion).filter(
            Transaccion.tipo == 'gasto',
            Transaccion.fecha >= inicio_mes
        ).group_by(Categoria.id).all()

        return jsonify({
            'labels': [g.nombre for g in gastos],
            'data': [float(g.total) for g in gastos]
        })

    # API para timeout de sesión
    @app.route('/api/session/ping', methods=['POST'])
    @login_required
    def session_ping():
        """Extiende la sesión actual"""
        session['last_activity'] = datetime.now().isoformat()
        return jsonify({'status': 'ok', 'timeout_minutes': SESSION_TIMEOUT_MINUTES})

    @app.route('/api/session/status')
    @login_required
    def session_status():
        """Verifica el estado de la sesión"""
        last_activity = session.get('last_activity')
        if not last_activity:
            return jsonify({'active': False})
        
        last_activity_time = datetime.fromisoformat(last_activity)
        elapsed = datetime.now() - last_activity_time
        remaining = timedelta(minutes=SESSION_TIMEOUT_MINUTES) - elapsed
        
        return jsonify({
            'active': True,
            'remaining_seconds': max(0, int(remaining.total_seconds())),
            'timeout_minutes': SESSION_TIMEOUT_MINUTES
        })

    # Ruta temporal para arreglar secuencias de PostgreSQL
    # Ejecutar UNA SOLA VEZ desde el navegador, después eliminar
    @app.route('/fix-sequences')
    @login_required
    def fix_sequences():
        """Arregla las secuencias de IDs en PostgreSQL después de importar datos"""
        try:
            # Transacciones
            max_id = db.session.query(func.max(Transaccion.id)).scalar() or 0
            db.session.execute(db.text(f"SELECT setval('transacciones_id_seq', {max_id})"))
            
            # Cuentas
            max_id = db.session.query(func.max(Cuenta.id)).scalar() or 0
            db.session.execute(db.text(f"SELECT setval('cuentas_id_seq', {max_id})"))
            
            # Categorías
            max_id = db.session.query(func.max(Categoria.id)).scalar() or 0
            db.session.execute(db.text(f"SELECT setval('categorias_id_seq', {max_id})"))
            
            # Presupuestos
            max_id = db.session.query(func.max(Presupuesto.id)).scalar() or 0
            db.session.execute(db.text(f"SELECT setval('presupuestos_id_seq', {max_id})"))
            
            # Metas
            max_id = db.session.query(func.max(Meta.id)).scalar() or 0
            db.session.execute(db.text(f"SELECT setval('metas_id_seq', {max_id})"))
            
            db.session.commit()
            return {'status': 'ok', 'message': 'Secuencias arregladas!'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}, 500

    return app


def crear_usuario_por_defecto():
    """Crea el usuario admin por defecto si no existe"""
    from config import Config
    config = Config()

    try:
        existente = Usuario.query.filter_by(username=config.USUARIO_ADMIN).first()
        if existente:
            print(f"Usuario ya existe: {config.USUARIO_ADMIN}")
            return
        
        usuario = Usuario(
            username=config.USUARIO_ADMIN,
            password_hash=''
        )
        usuario.set_password(config.PASSWORD_ADMIN)
        db.session.add(usuario)
        db.session.commit()
        print(f"✅ Usuario creado exitosamente: {config.USUARIO_ADMIN}")
        print(f"   Contraseña configurada: {config.PASSWORD_ADMIN}")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando usuario: {e}")
        import traceback
        traceback.print_exc()


def crear_categorias_por_defecto():
    """Crea categorías por defecto si no existen"""
    categorias_defecto = [
        # Ingresos
        {'nombre': 'Salario', 'tipo': 'ingreso', 'icono': 'fa-wallet', 'color': '#28a745'},
        {'nombre': 'Ingresos Extra', 'tipo': 'ingreso', 'icono': 'fa-plus-circle', 'color': '#28a745'},
        {'nombre': 'Inversiones', 'tipo': 'ingreso', 'icono': 'fa-chart-line', 'color': '#28a745'},
        {'nombre': 'Otros Ingresos', 'tipo': 'ingreso', 'icono': 'fa-dollar-sign', 'color': '#28a745'},
        # Gastos
        {'nombre': 'Vivienda', 'tipo': 'gasto', 'icono': 'fa-home', 'color': '#dc3545'},
        {'nombre': 'Alimentación', 'tipo': 'gasto', 'icono': 'fa-utensils', 'color': '#fd7e14'},
        {'nombre': 'Transporte', 'tipo': 'gasto', 'icono': 'fa-car', 'color': '#ffc107'},
        {'nombre': 'Servicios', 'tipo': 'gasto', 'icono': 'fa-bolt', 'color': '#17a2b8'},
        {'nombre': 'Salud', 'tipo': 'gasto', 'icono': 'fa-heartbeat', 'color': '#e83e8c'},
        {'nombre': 'Educación', 'tipo': 'gasto', 'icono': 'fa-graduation-cap', 'color': '#6f42c1'},
        {'nombre': 'Entretenimiento', 'tipo': 'gasto', 'icono': 'fa-film', 'color': '#6610f2'},
        {'nombre': 'Compras', 'tipo': 'gasto', 'icono': 'fa-shopping-bag', 'color': '#e83e8c'},
        {'nombre': 'Otros Gastos', 'tipo': 'gasto', 'icono': 'fa-ellipsis-h', 'color': '#6c757d'},
    ]

    for cat in categorias_defecto:
        existente = Categoria.query.filter_by(
            nombre=cat['nombre'],
            tipo=cat['tipo']
        ).first()
        if not existente:
            categoria = Categoria(**cat)
            db.session.add(categoria)

    try:
        db.session.commit()
    except:
        db.session.rollback()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
