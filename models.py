from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Usuario(db.Model):
    """Usuario único para autenticación"""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Cuenta(db.Model):
    """Cuentas financieras (ej: efectivo, banco, tarjeta)"""
    __tablename__ = 'cuentas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # efectivo, banco, tarjeta, inversion
    saldo_inicial = db.Column(db.Float, default=0.0)
    moneda = db.Column(db.String(3), default='USD')
    activa = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    transacciones = db.relationship('Transaccion', backref='cuenta', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def saldo_actual(self):
        """Calcula el saldo actual sumando todas las transacciones"""
        ingresos = db.session.query(db.func.sum(Transaccion.monto)).filter(
            Transaccion.cuenta_id == self.id,
            Transaccion.tipo == 'ingreso'
        ).scalar() or 0
        gastos = db.session.query(db.func.sum(Transaccion.monto)).filter(
            Transaccion.cuenta_id == self.id,
            Transaccion.tipo == 'gasto'
        ).scalar() or 0
        return self.saldo_inicial + ingresos - gastos

    def __repr__(self):
        return f'<Cuenta {self.nombre}>'


class Categoria(db.Model):
    """Categorías para transacciones"""
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # ingreso o gasto
    icono = db.Column(db.String(50), default='fa-tag')
    color = db.Column(db.String(20), default='#6c757d')
    parent_id = db.Column(db.Integer, nullable=True)  # Columna mantida por compatibilidad
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    transacciones = db.relationship('Transaccion', backref='categoria', lazy='dynamic')
    presupuestos = db.relationship('Presupuesto', backref='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<Categoria {self.nombre} ({self.tipo})>'


class Transaccion(db.Model):
    """Transacciones financieras"""
    __tablename__ = 'transacciones'

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # ingreso o gasto
    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    pagado = db.Column(db.Boolean, default=True)  # True = pagado, False = pendiente
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    cuenta_id = db.Column(db.Integer, db.ForeignKey('cuentas.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)

    def __repr__(self):
        return f'<Transaccion {self.descripcion} - {self.monto}>'


class Presupuesto(db.Model):
    """Presupuestos mensuales por categoría"""
    __tablename__ = 'presupuestos'

    id = db.Column(db.Integer, primary_key=True)
    monto = db.Column(db.Float, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)

    def __repr__(self):
        return f'<Presupuesto {self.categoria_id} - {self.mes}/{self.anio}>'


class Meta(db.Model):
    """Metas de ahorro"""
    __tablename__ = 'metas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    monto_objetivo = db.Column(db.Float, nullable=False)
    monto_actual = db.Column(db.Float, default=0.0)
    fecha_limite = db.Column(db.Date, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    activa = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    cuenta_id = db.Column(db.Integer, db.ForeignKey('cuentas.id'), nullable=True)

    @property
    def porcentaje_completado(self):
        """Calcula el porcentaje de completado de la meta"""
        if self.monto_objetivo == 0:
            return 0
        return min(100, (self.monto_actual / self.monto_objetivo) * 100)

    def __repr__(self):
        return f'<Meta {self.nombre}>'


class TipoCambio(db.Model):
    """Tipos de cambio entre monedas"""
    __tablename__ = 'tipos_cambio'

    id = db.Column(db.Integer, primary_key=True)
    moneda_origen = db.Column(db.String(3), nullable=False)
    moneda_destino = db.Column(db.String(3), nullable=False)
    tasa = db.Column(db.Float, nullable=False)
    fecha_actualizacion = db.Column(db.Date, default=datetime.utcnow().date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def obtener_tasa(origen, destino):
        """Obtiene la tasa de cambio entre dos monedas"""
        if origen == destino:
            return 1.0
        tasa = TipoCambio.query.filter_by(
            moneda_origen=origen,
            moneda_destino=destino
        ).first()
        if tasa:
            return tasa.tasa
        tasa_inversa = TipoCambio.query.filter_by(
            moneda_origen=destino,
            moneda_destino=origen
        ).first()
        if tasa_inversa:
            return 1 / tasa_inversa.tasa
        return 1.0

    @staticmethod
    def convertir(monto, origen, destino):
        """Convierte un monto de una moneda a otra"""
        tasa = TipoCambio.obtener_tasa(origen, destino)
        return monto * tasa

    def __repr__(self):
        return f'<TipoCambio {self.moneda_origen}/{self.moneda_destino}: {self.tasa}>'
