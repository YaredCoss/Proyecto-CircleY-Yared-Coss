# app_clientes/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.utils.timezone import localtime
from django.utils.formats import date_format

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    class TipoDescuento(models.TextChoices):
        PORCENTAJE = "porcentaje", "Descuento porcentual"
        BOGO = "bogo", "2x1 / lleva N paga M"

    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    tipo_descuento = models.CharField(max_length=20, choices=TipoDescuento.choices)
    valor_descuento = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))],)
    unidades_requeridas = models.PositiveIntegerField(default=0)
    unidades_pagadas = models.PositiveIntegerField(default=0)
    productos_combo = models.ManyToManyField('Producto', related_name='promociones_combo', blank=True)
    productos_requeridos = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    imagen_url = models.ImageField(upload_to='promociones/', blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_inicio', 'nombre']

    def __str__(self):
        return self.nombre

    def esta_activa(self):
        hoy = timezone.now().date()
        return self.activo and self.fecha_inicio <= hoy <= self.fecha_fin

    def aplicar_descuento(self, precio):
        if self.tipo_descuento == self.TipoDescuento.PORCENTAJE:
            return max(Decimal('0.00'), precio - (precio * (self.valor_descuento / Decimal('100'))))
        return max(Decimal('0.00'), precio - self.valor_descuento)
    
    def save(self, *args, **kwargs):
        if self.tipo_descuento == Promocion.TipoDescuento.BOGO:
            self.valor = Decimal("0.00")
        super().save(*args, **kwargs)

class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    imagen_url = models.ImageField(upload_to='productos/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    promociones = models.ManyToManyField(Promocion, through='ProductoPromocion', related_name='productos')

    class Meta:
        ordering = ['nombre']
        unique_together = ('categoria', 'nombre')

    def __str__(self):
        return self.nombre

    def precio_con_descuento(self):
        hoy = timezone.now().date()
        precio_final = self.precio
        for promo in self.promociones.filter(activo=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy):
            precio_final = promo.aplicar_descuento(precio_final)
        return precio_final.quantize(Decimal('0.01'))

    def tiene_descuento_activo(self):
        hoy = timezone.now().date()
        return self.promociones.filter(activo=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy).exists()


class ProductoPromocion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    promocion = models.ForeignKey(Promocion, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('producto', 'promocion')

    def __str__(self):
        return f'{self.producto} ↔ {self.promocion}'


class Novedad(models.Model):
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    fecha_publicacion = models.DateField(default=timezone.now)
    imagen_url = models.ImageField(upload_to='novedades/', blank=True, null=True)

    class Meta:
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return self.titulo


class Carrito(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='carritos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    subtotal = models.DecimalField(max_digits=10,decimal_places=2, default=Decimal("0.00"))
    total_descuento = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ['-fecha_actualizacion']

    def __str__(self):
        return f'Carrito #{self.id} - {self.cliente}'
    
    def calcular_subtotal(self):
        return sum(item.subtotal() for item in self.items.all())

    def calcular_total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def vaciar(self):
        self.items.all().delete()
        self.activo = False
        self.save(update_fields=['activo', 'fecha_actualizacion'])


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario_actual = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('carrito', 'producto')

    def __str__(self):
        return f'{self.producto} x {self.cantidad}'

    def subtotal(self):
        return (self.precio_unitario_actual * self.cantidad).quantize(Decimal('0.01'))


class Pedido(models.Model):
    class EstadoPedido(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_CAMINO = 'EN_CAMINO', 'En camino'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    class MetodoPago(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Pago en efectivo'
        TARJETA = 'TARJETA', 'Tarjeta'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia/Depósito'

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado_pedido = models.CharField(max_length=20, choices=EstadoPedido.choices, default=EstadoPedido.PENDIENTE)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    descuento_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    direccion_envio = models.TextField()
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    fecha_envio = models.DateTimeField(blank=True, null=True)
    fecha_entrega_estimada = models.DateTimeField(blank=True, null=True)
    confirmado_cliente = models.BooleanField(default=False)
    confirmado_admin = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_pedido']

    def __str__(self):
        return f'Pedido #{self.id} - {self.cliente}'

    def actualizar_total(self):
        total = sum(detalle.subtotal() for detalle in self.detalles.all())
        self.total = total.quantize(Decimal('0.01'))
        self.save(update_fields=['total'])

    def marcar_en_camino(self):
        self.estado_pedido = self.EstadoPedido.EN_CAMINO
        self.fecha_envio = timezone.now()
        self.save(update_fields=['estado_pedido', 'fecha_envio'])

    def marcar_entregado(self):
        self.estado_pedido = self.EstadoPedido.ENTREGADO
        self.fecha_entrega_estimada = timezone.now()
        self.confirmado_cliente = True
        self.confirmado_admin = True
        self.save(update_fields=['estado_pedido', 'fecha_entrega_estimada', 'confirmado_cliente', 'confirmado_admin'])
    
    @property
    def fecha_de_pedido(self):
        return date_format(localtime(self.fecha_pedido), "d/m/Y H:i")


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_venta = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name_plural = 'Detalles de Pedido'

    def __str__(self):
        return f'{self.producto} x {self.cantidad}'

    def subtotal(self):
        return (self.precio_unitario_venta * self.cantidad).quantize(Decimal('0.01'))


class MensajeContacto(models.Model):
    nombre_remitente = models.CharField(max_length=120)
    email_remitente = models.EmailField()
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    @property
    def fecha_envio_legible(self):
        return date_format(localtime(self.fecha_envio), "d/m/Y H:i")
    
    class Meta:
        ordering = ['-fecha_envio']

    def __str__(self):
        return f'{self.nombre_remitente} - {self.email_remitente}'