# app_clientes/views.py
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.db.models import Sum, F
from django.utils.formats import date_format
from django.utils.timezone import localtime


from .models import (
    Cliente, Categoria, Producto, Promocion, ProductoPromocion,
    Novedad, Carrito, ItemCarrito, Pedido, DetallePedido, MensajeContacto
)
from .templatetags.ui_extras import highlight  # opcional si deseas usar en vista


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('app_clientes:login')
        if not request.user.is_staff:
            messages.error(request, "Acceso restringido al panel administrativo.")
            return redirect('app_clientes:inicio_circley')
        return view_func(request, *args, **kwargs)
    return _wrapped


def obtener_precio_producto(producto: Producto):
    return producto.precio_con_descuento() if producto.tiene_descuento_activo() else producto.precio


def obtener_carrito_cliente(cliente: Cliente):
    carrito, _ = Carrito.objects.get_or_create(cliente=cliente, activo=True)
    return carrito


# ---------- Vistas públicas / clientes ----------
def inicio_circley(request):
    productos = Producto.objects.filter(activo=True, stock__gt=0).select_related('categoria')[:6]
    promociones = Promocion.objects.filter(activo=True)[:6]
    novedades = Novedad.objects.all()[:3]
    contexto = {
        'productos_destacados': productos,
        'promociones_destacadas': promociones,
        'novedades_recientes': novedades,
        'titulo_pagina': 'Inicio',
    }
    return render(request, 'usuario/index.html', contexto)


def productos_servicios(request):
    categoria_id = request.GET.get('categoria')
    search = request.GET.get('busqueda', '').strip()
    productos = Producto.objects.filter(activo=True).select_related('categoria')

    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(categoria__nombre__icontains=search)
        )
        messages.info(request, f"Resultados filtrados por: {search}")

    contexto = {
        'productos': productos,
        'busqueda': search,
        'titulo_pagina': 'Productos y Servicios',
    }
    return render(request, 'usuario/ps.html', contexto)


def promociones_view(request):
    hoy = timezone.now().date()
    promociones = Promocion.objects.filter(
        activo=True,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy
    )
    return render(request, 'usuario/p.html', {
        'promociones': promociones,
        'titulo_pagina': 'Promociones'
    })

def aplicar_promociones(carrito):
    hoy = timezone.now().date()
    total_descuento = Decimal("0.00")

    promociones = (
        Promocion.objects.filter(activa=True)
        .filter(
            Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=hoy),
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy),
        )
        .prefetch_related("productos")  # opcional si usas M2M con productos
    )

    for promo in promociones:
        if promo.tipo_descuento == Promocion.TipoDescuento.BOGO:
            total_descuento += aplicar_bogo(carrito, promo)
        elif promo.tipo_descuento == Promocion.TipoDescuento.PORCENTAJE:
            total_descuento += aplicar_porcentaje(carrito, promo)

    subtotal = carrito.subtotal or Decimal("0.00")
    total_descuento = total_descuento.quantize(Decimal("0.01"))
    carrito.total = max(Decimal("0.00"), subtotal - total_descuento)
    carrito.total_descuento = total_descuento
    carrito.save(update_fields=["total", "total_descuento"])

    return total_descuento

def aplicar_bogo(carrito, promo):
    total_descuento = Decimal("0.00")

    for item in carrito.items.all():
        if promo.productos.filter(pk=item.producto_id).exists():
            pares = item.cantidad // 2
            if pares:
                precio_unitario = item.precio_unitario_actual or item.producto.precio
                descuento = (pares * precio_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_descuento += descuento
                print(f"BOGO {promo}: {item.producto} -> {descuento}")

    return total_descuento

def aplicar_promocion_dos_por_uno(item):
    if item.cantidad < 2:
        return Decimal("0.00")

    pares = item.cantidad // 2
    precio_unitario = item.precio_unitario_actual or item.producto.precio
    return (pares * precio_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def aplicar_porcentaje(carrito, promo):
    queryset = carrito.items.all()
    if promo.productos.exists():
        queryset = queryset.filter(producto__in=promo.productos.all())

    subtotal = queryset.aggregate(
        total=Sum(F("cantidad") * F("producto__precio"))
    )["total"] or Decimal("0.00")

    if subtotal <= 0 or not promo.valor_descuento:
        return Decimal("0.00")

    porcentaje = Decimal(promo.valor_descuento) / Decimal("100")
    descuento = subtotal * porcentaje
    return descuento.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def recalcular_totales_carrito(carrito):
    subtotal = carrito.items.aggregate(
        total=Sum(F("cantidad") * F("producto__precio"))
    )["total"] or Decimal("0.00")

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    carrito.subtotal = subtotal
    carrito.save(update_fields=["subtotal"])

    aplicar_promociones(carrito)

def novedades_view(request):
    novedades = Novedad.objects.all()
    return render(request, 'usuario/n.html', {
        'novedades': novedades,
        'titulo_pagina': 'Novedades'
    })


def contacto_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        correo = request.POST.get('correo')
        mensaje = request.POST.get('mensaje')

        MensajeContacto.objects.create(
            nombre_remitente=nombre,
            email_remitente=correo,
            mensaje=mensaje
        )
        messages.success(request, "Mensaje enviado. Nos pondremos en contacto contigo.")
        return redirect('app_clientes:contacto')

    return render(request, 'usuario/c.html', {'titulo_pagina': 'Contáctanos'})


def registro_clientes(request):
    if request.user.is_authenticated:
        return redirect('app_clientes:inicio_circley')

    if request.method == 'POST':
        username = request.POST.get('username')
        nombre = request.POST.get('nombre')
        apellidos = request.POST.get('apellidos')
        correo = request.POST.get('correo')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        telefono = request.POST.get('telefono')
        direccion = request.POST.get('direccion')

        if User.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya existe.")
            return redirect('app_clientes:registro')

        if password != password_confirm:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('app_clientes:registro')

        user = User.objects.create_user(
            username=username,
            email=correo,
            password=password,
            first_name=nombre,
            last_name=apellidos,
            is_staff=False
        )
        Cliente.objects.create(user=user, telefono=telefono, direccion=direccion)
        messages.success(request, "Registro exitoso. Inicia sesión para continuar.")
        return redirect('app_clientes:login')

    return render(request, 'usuario/login.html', {'modo_registro': True})


def login_usuario(request):
    if request.user.is_authenticated:
        return redirect('app_clientes:inicio_circley')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Credenciales inválidas.")
            return redirect('app_clientes:login')

        login(request, user)
        messages.success(request, f"¡Hola {user.first_name or user.username}!")
        if user.is_staff:
            return redirect('app_clientes:dashboard_admin')
        return redirect('app_clientes:inicio_circley')

    return render(request, 'usuario/login.html', {'modo_registro': False})


@login_required
def logout_usuario(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('app_clientes:inicio_circley')


@login_required
def ver_carrito(request):
    if not hasattr(request.user, "cliente"):
        messages.warning(request, "Regístrate como cliente para usar el carrito.")
        return redirect("app_clientes:login")

    carrito = obtener_carrito_cliente(request.user.cliente)
    recalcular_totales_carrito(carrito)

    items = carrito.items.select_related("producto")
    contexto = {
        "carrito": carrito,
        "items": items,
        "subtotal": carrito.subtotal,
        "total_descuento": carrito.total_descuento,
        "total_a_pagar": carrito.total,
        "titulo_pagina": "Mi carrito",
    }
    return render(request, "usuario/carrito.html", contexto)


@login_required
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)

    if not hasattr(request.user, 'cliente'):
        messages.warning(request, "Necesitas iniciar sesión como cliente para agregar productos.")
        return redirect('app_clientes:login')

    cantidad = int(request.POST.get('cantidad', 1))
    if cantidad <= 0:
        messages.error(request, "La cantidad debe ser positiva.")
        return redirect(request.META.get('HTTP_REFERER', 'app_clientes:inicio_circley'))

    if producto.stock < cantidad:
        messages.error(request, "No hay stock suficiente.")
        return redirect(request.META.get('HTTP_REFERER', 'app_clientes:inicio_circley'))

    carrito = obtener_carrito_cliente(request.user.cliente)
    precio_actual = obtener_precio_producto(producto)

    item, created = ItemCarrito.objects.get_or_create(
        carrito=carrito,
        producto=producto,
        defaults={'cantidad': cantidad, 'precio_unitario_actual': precio_actual}
    )
    if not created:
        item.cantidad += cantidad
        item.precio_unitario_actual = precio_actual
        item.save(update_fields=['cantidad', 'precio_unitario_actual'])

    producto.stock -= cantidad
    producto.save(update_fields=['stock'])

    messages.success(
        request,
        f"{producto.nombre} se añadió al carrito.",
        extra_tags="carrito"
    )
    return redirect(request.META.get('HTTP_REFERER', 'app_clientes:inicio_circley'))


@login_required
def actualizar_item_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, pk=item_id, carrito__cliente__user=request.user)
    nueva_cantidad = int(request.POST.get('cantidad', item.cantidad))

    if nueva_cantidad <= 0:
        return eliminar_item_carrito(request, item_id)

    diferencia = nueva_cantidad - item.cantidad
    producto = item.producto

    if diferencia > 0 and producto.stock < diferencia:
        messages.error(request, "No hay stock suficiente para aumentar la cantidad.")
        return redirect('app_clientes:ver_carrito')

    producto.stock -= diferencia
    producto.save(update_fields=['stock'])
    item.cantidad = nueva_cantidad
    item.precio_unitario_actual = obtener_precio_producto(producto)
    item.save(update_fields=['cantidad', 'precio_unitario_actual'])
    messages.success(request, "Cantidad actualizada.")
    return redirect('app_clientes:ver_carrito')


@login_required
def eliminar_item_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, pk=item_id, carrito__cliente__user=request.user)
    producto = item.producto
    producto.stock += item.cantidad
    producto.save(update_fields=['stock'])
    item.delete()
    messages.info(request, "Producto retirado del carrito.")
    return redirect('app_clientes:ver_carrito')


@login_required
def checkout(request):
    if not hasattr(request.user, "cliente"):
        messages.warning(request, "Debes ser cliente para completar una compra.")
        return redirect("app_clientes:login")

    carrito = obtener_carrito_cliente(request.user.cliente)
    items = carrito.items.select_related("producto")

    if not items.exists():
        messages.info(request, "Tu carrito está vacío.")
        return redirect("app_clientes:inicio_circley")

    # Asegura que subtotal/total del carrito estén actualizados
    recalcular_totales_carrito(carrito)

    if request.method == "POST":
        metodo_pago = request.POST.get("metodo_pago")
        direccion_envio = request.POST.get("direccion_envio") or request.user.cliente.direccion
        fecha_estimada = request.POST.get("fecha_entrega_estimada")

        with transaction.atomic():
            pedido = Pedido.objects.create(
                cliente=request.user.cliente,
                direccion_envio=direccion_envio,
                metodo_pago=metodo_pago,
                subtotal=carrito.subtotal,
                descuento_total=carrito.total_descuento,
                total=carrito.total,
            )

            for item in items:
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    cantidad=item.cantidad,
                    precio_unitario_venta=item.precio_unitario_actual,
                )

            if fecha_estimada:
                try:
                    pedido.fecha_entrega_estimada = timezone.datetime.strptime(fecha_estimada, "%Y-%m-%d")
                except ValueError:
                    pass
            pedido.save()
            carrito.vaciar()

        messages.success(request, "Pedido generado correctamente.")
        return redirect("app_clientes:historial_pedidos")

    contexto = {
        "carrito": carrito,
        "items": items,
        "subtotal": carrito.subtotal,
        "total_descuento": carrito.total_descuento,
        "total_a_pagar": carrito.total,
        "metodos_pago": Pedido.MetodoPago.choices,
        "titulo_pagina": "Checkout",
    }
    return render(request, "usuario/checkout.html", contexto)


@login_required
def confirmar_entrega_cliente(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, cliente__user=request.user)
    pedido.confirmado_cliente = True
    if pedido.confirmado_admin:
        pedido.estado_pedido = Pedido.EstadoPedido.ENTREGADO
    pedido.save(update_fields=['confirmado_cliente', 'estado_pedido'])
    messages.success(request, "Entrega confirmada. ¡Gracias por tu compra!")
    return redirect('app_clientes:historial_pedidos')


@admin_required
def confirmar_entrega_admin(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.confirmado_admin = True
    if pedido.confirmado_cliente:
        pedido.marcar_entregado()
    else:
        pedido.estado_pedido = Pedido.EstadoPedido.EN_CAMINO
        pedido.save(update_fields=['confirmado_admin', 'estado_pedido'])
    messages.success(request, "Estado actualizado desde el panel administrativo.")
    return redirect('app_clientes:ver_pedidos')


@login_required
def historial_pedidos(request):
    if not hasattr(request.user, 'cliente'):
        return redirect('app_clientes:inicio_circley')

    pedidos = Pedido.objects.filter(cliente=request.user.cliente).prefetch_related('detalles__producto')
    return render(request, 'usuario/historial.html', {
        'pedidos': pedidos,
        'titulo_pagina': 'Historial de pedidos'
    })


# ---------- Configuración genérica CRUD admin ----------

CRUD_CONFIG = {
    'clientes': {
        'model': Cliente,
        'list_template': 'admin/clientes/ver_clientes.html',
        'delete_template': 'admin/clientes/borrar_clientes.html',
        'list_fields': ['id', 'user', 'telefono', 'direccion'],
        'form_fields': ['user', 'telefono', 'direccion'],
        'search_fields': [
            'user__username', 'user__first_name', 'telefono', 'direccion'
        ],
        'foreign_keys': {'user': User.objects.filter(is_staff=False)},
        'labels': {
            'user': 'Usuario asociado',
            'telefono': 'Teléfono',
            'direccion': 'Dirección'
        }
    },
    'categorias': {
        'model': Categoria,
        'list_template': 'admin/categorias/ver_categorias.html',
        'create_template': 'admin/categorias/agregar_categorias.html',
        'update_template': 'admin/categorias/actualizar_categorias.html',
        'delete_template': 'admin/categorias/borrar_categorias.html',
        "url_lista": "app_clientes:ver_categorias",
        'list_fields': ['id', 'nombre', 'descripcion'],
        'form_fields': ['nombre', 'descripcion'],
        'search_fields': ['nombre', 'descripcion'],
        'labels': {
            'nombre': 'Nombre',
            'descripcion': 'Descripción'
        }
    },
    'productos': {
        'model': Producto,
        'list_template': 'admin/productos/ver_productos.html',
        'create_template': 'admin/productos/agregar_productos.html',
        'update_template': 'admin/productos/actualizar_productos.html',
        'delete_template': 'admin/productos/borrar_productos.html',
        "url_lista": "app_clientes:ver_productos",
        'list_fields': ['id', 'nombre', 'categoria', 'precio', 'stock', 'activo'],
        'form_fields': ['nombre', 'descripcion', 'precio', 'stock', 'categoria', 'imagen_url', 'activo'],
        'many_to_many_fields': ['promociones'],
        'search_fields': ['nombre', 'descripcion', 'categoria__nombre'],
        'foreign_keys': {'categoria': Categoria.objects.all()},
        'boolean_fields': ['activo'],
        'file_fields': ['imagen_url'],
        'labels': {
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'precio': 'Precio',
            'stock': 'Stock',
            'categoria': 'Categoría',
            'imagen_url': 'Imagen',
            'activo': 'Activo'
        }
    },
    'promociones': {
        'model': Promocion,
        'list_template': 'admin/promociones/ver_promociones.html',
        'create_template': 'admin/promociones/agregar_promociones.html',
        'update_template': 'admin/promociones/actualizar_promociones.html',
        'delete_template': 'admin/promociones/borrar_promociones.html',
        "url_lista": "app_clientes:ver_promociones",
        'list_fields': ['id', 'nombre', 'tipo_descuento', 'valor_descuento', 'fecha_inicio', 'fecha_fin', 'activo'],
        'form_fields': ['nombre', 'descripcion', 'tipo_descuento', 'valor_descuento', 'fecha_inicio', 'fecha_fin', 'imagen_url', 'activo'],
        'many_to_many_fields': ['productos'],
        'search_fields': ['nombre', 'descripcion'],
        'choices_fields': {'tipo_descuento': Promocion.TipoDescuento.choices},
        'boolean_fields': ['activo'],
        'file_fields': ['imagen_url'],
        'labels': {
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'tipo_descuento': 'Tipo de descuento',
            'valor_descuento': 'Valor',
            'fecha_inicio': 'Fecha inicio',
            'fecha_fin': 'Fecha fin',
            'imagen_url': 'Imagen',
            'activo': 'Activa'
        }
    },
    'novedades': {
        'model': Novedad,
        'list_template': 'admin/novedades/ver_novedades.html',
        'create_template': 'admin/novedades/agregar_novedades.html',
        'update_template': 'admin/novedades/actualizar_novedades.html',
        'delete_template': 'admin/novedades/borrar_novedades.html',
        "url_lista": "app_clientes:ver_novedades",
        'list_fields': ['id', 'titulo', 'fecha_publicacion'],
        'form_fields': ['titulo', 'descripcion', 'fecha_publicacion', 'imagen_url'],
        'search_fields': ['titulo', 'descripcion'],
        'file_fields': ['imagen_url'],
        'labels': {
            'titulo': 'Título',
            'descripcion': 'Descripción',
            'fecha_publicacion': 'Fecha de publicación',
            'imagen_url': 'Imagen'
        }
    },
    'productos_promociones': {
        'model': ProductoPromocion,
        'list_template': 'admin/productos_promociones/ver_productos_promociones.html',
        'create_template': 'admin/productos_promociones/agregar_productos_promociones.html',
        'update_template': 'admin/productos_promociones/actualizar_productos_promociones.html',
        'delete_template': 'admin/productos_promociones/borrar_productos_promociones.html',
        "url_lista": "app_clientes:ver_productos_promociones",
        'list_fields': ['id', 'producto', 'promocion'],
        'form_fields': ['producto', 'promocion'],
        'search_fields': ['producto__nombre', 'promocion__nombre'],
        'foreign_keys': {
            'producto': Producto.objects.all(),
            'promocion': Promocion.objects.all()
        },
        'labels': {
            'producto': 'Producto',
            'promocion': 'Promoción'
        }
    },
    'pedidos': {
        'model': Pedido,
        'list_template': 'admin/pedidos/ver_pedidos.html',
        'update_template': 'admin/pedidos/actualizar_pedidos.html',
        'delete_template': 'admin/pedidos/borrar_pedidos.html',
        "url_lista": "app_clientes:ver_pedidos",
        'list_fields': ['id', 'cliente', 'estado_pedido', 'total', 'metodo_pago', 'fecha_de_pedido'],
        'form_fields': ['cliente', 'estado_pedido', 'direccion_envio',
                        'metodo_pago', 'fecha_envio', 'fecha_entrega_estimada',
                        'confirmado_cliente', 'confirmado_admin'],
        'search_fields': ['cliente__user__username', 'estado_pedido', 'metodo_pago'],
        'foreign_keys': {'cliente': Cliente.objects.all()},
        'boolean_fields': ['confirmado_cliente', 'confirmado_admin'],
        'choices_fields': {
            'estado_pedido': Pedido.EstadoPedido.choices,
            'metodo_pago': Pedido.MetodoPago.choices
        },
        'labels': {
            'cliente': 'Cliente',
            'estado_pedido': 'Estado',
            'direccion_envio': 'Dirección',
            'metodo_pago': 'Método de pago',
            'fecha_envio': 'Fecha envío',
            'fecha_entrega_estimada': 'Fecha entrega (estimada)',
            'confirmado_cliente': 'Confirmado por cliente',
            'confirmado_admin': 'Confirmado por admin',
            'fecha_de_pedido': 'Fecha_pedido'
        }
    },
    'mensajes_contacto': {
        'model': MensajeContacto,
        'list_template': 'admin/mensajes_contacto/ver_mensajes_contacto.html',
        'update_template': 'admin/mensajes_contacto/actualizar_mensajes_contacto.html',
        'delete_template': 'admin/mensajes_contacto/borrar_mensajes_contacto.html',
        "url_lista": "app_clientes:ver_mensajes_contacto",
        'list_fields': ['id', 'nombre_remitente', 'email_remitente', 'fecha_envio_legible', 'mensaje','leido'],
        'form_fields': ['leido'],
        'search_fields': ['nombre_remitente', 'email_remitente', 'mensaje'],
        'boolean_fields': ['leido'],
        'labels': {
            'nombre_remitente': 'Nombre',
            'email_remitente': 'Correo',
            'mensaje': 'Mensaje',
            'leido': 'Leído',
            'fecha_envio_legible': 'Fecha de envío',
        }
    }
}


def crud_list_view(request, slug):
    config = CRUD_CONFIG[slug]
    Model = config['model']
    queryset = Model.objects.all()
    search = request.GET.get('busqueda', '').strip()

    if search:
        q_objects = Q()
        for field in config.get('search_fields', []):
            q_objects |= Q(**{f"{field}__icontains": search})
        queryset = queryset.filter(q_objects)
        messages.info(request, f"Resultados filtrados por: {search}")

    rows = []
    for obj in queryset:
        valores = []
        for field in config['list_fields']:
            valor = getattr(obj, field, '')
            if callable(valor):
                valor = valor()
            if valor is None:
                valor = ''
            valores.append(str(valor))
        rows.append({
            'id': obj.pk,
            'values': valores,
        })

    contexto = {
        'config': config,
        'objetos': queryset,
        'rows': rows,
        'busqueda': search,
        'slug': slug,
        'titulo_seccion': config.get('titulo', slug.replace('_', ' ').title()),
    }
    return render(request, config['list_template'], contexto)


def crud_create_update(request, slug, instance=None):
    config = CRUD_CONFIG[slug]
    Model = config['model']
    is_update = instance is not None
    template = config['update_template'] if is_update else config['create_template']

    if request.method == 'POST':
        data = {}
        files = request.FILES
        m2m_data = {}

        for field in config['form_fields']:
            if field in config.get('foreign_keys', {}):
                data[f"{field}_id"] = request.POST.get(field) or None
            elif field in config.get('boolean_fields', []):
                data[field] = field in request.POST
            elif field in config.get('file_fields', []):
                archivo = files.get(field)
                if archivo:
                    data[field] = archivo
                elif not archivo and is_update:
                    continue  # mantenemos el archivo existente
            else:
                data[field] = request.POST.get(field)
                
        try:
            if is_update:
                for key, value in data.items():
                    setattr(instance, key, value)
                instance.save()
                messages.success(request, "Registro actualizado correctamente.")
            else:
                instance = Model.objects.create(**data)
                messages.success(request, "Registro creado con éxito.")
            return redirect(reverse(config['url_lista']))
        except Exception as exc:
            messages.error(request, f"Ocurrió un error: {exc}")
            
        for field in config.get('many_to_many_fields', []):
            ids = request.POST.getlist(field)
            m2m_data[field] = [int(pk) for pk in ids if pk]

        if is_update:
            for attr, value in data.items():
                setattr(instance, attr, value)
            instance.save()
        else:
            instance = Model.objects.create(**data)

        # asigna las relaciones M2M
        for field, ids in m2m_data.items():
            getattr(instance, field).set(ids)

        messages.success(request, "Guardado correctamente.")
        return redirect(config['url_lista'])

    foreign_keys_data = {}
    for field, qs in config.get('foreign_keys', {}).items():
        foreign_keys_data[field] = qs() if callable(qs) else qs

    contexto = {
        'config': config,
        'instance': instance,
        'foreign_keys': foreign_keys_data,
        'choices_fields': config.get('choices_fields', {}),
        'labels': config.get('labels', {}),
        'is_update': is_update,
        'slug': slug,
        'titulo_seccion': config.get('titulo', slug.replace('_', ' ').title()),
    }
    return render(request, template, contexto)


def crud_delete(request, slug, pk):
    config = CRUD_CONFIG[slug]
    Model = config['model']
    instance = get_object_or_404(Model, pk=pk)

    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Registro eliminado correctamente.")
        return redirect(reverse(config['url_lista']))

    return render(request, config['delete_template'], {
        'config': config,
        'instance': instance,
        'slug': slug,
        'titulo_seccion': config.get('titulo', slug.replace('_', ' ').title()),
    })


# -------- Wrapper functions con los nombres solicitados --------
@admin_required
def dashboard_admin(request):
    return render(request, 'admin/dashboard.html', {
        'total_clientes': Cliente.objects.count(),
        'total_pedidos': Pedido.objects.count(),
        'total_productos': Producto.objects.count(),
        'total_promociones_activas': Promocion.objects.filter(activo=True).count(),
        'titulo_pagina': 'Panel Circle Y'
    })


@admin_required
def ver_clientes(request):
    return crud_list_view(request, 'clientes')


@admin_required
def agregar_clientes(request):
    return crud_create_update(request, 'clientes')


@admin_required
def actualizar_clientes(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return crud_create_update(request, 'clientes', instance=cliente)


@admin_required
def realizar_actualizacion_clientes(request, pk):
    return actualizar_clientes(request, pk)  # compatibilidad con el punto 5


@admin_required
def borrar_clientes(request, pk):
    return crud_delete(request, 'clientes', pk)


# Repetimos el patrón para cada tabla (categorías, productos, etc.)
@admin_required
def ver_categorias(request):
    return crud_list_view(request, 'categorias')


@admin_required
def agregar_categorias(request):
    return crud_create_update(request, 'categorias')


@admin_required
def actualizar_categorias(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    return crud_create_update(request, 'categorias', categoria)


@admin_required
def realizar_actualizacion_categorias(request, pk):
    return actualizar_categorias(request, pk)


@admin_required
def borrar_categorias(request, pk):
    return crud_delete(request, 'categorias', pk)


@admin_required
def ver_productos(request):
    return crud_list_view(request, 'productos')


@admin_required
def agregar_productos(request):
    return crud_create_update(request, 'productos')


@admin_required
def actualizar_productos(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return crud_create_update(request, 'productos', producto)


@admin_required
def realizar_actualizacion_productos(request, pk):
    return actualizar_productos(request, pk)


@admin_required
def borrar_productos(request, pk):
    return crud_delete(request, 'productos', pk)


@admin_required
def ver_promociones(request):
    return crud_list_view(request, 'promociones')


@admin_required
def agregar_promociones(request):
    return crud_create_update(request, 'promociones')


@admin_required
def actualizar_promociones(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    return crud_create_update(request, 'promociones', promocion)


@admin_required
def realizar_actualizacion_promociones(request, pk):
    return actualizar_promociones(request, pk)


@admin_required
def borrar_promociones(request, pk):
    return crud_delete(request, 'promociones', pk)


@admin_required
def ver_novedades(request):
    return crud_list_view(request, 'novedades')


@admin_required
def agregar_novedades(request):
    return crud_create_update(request, 'novedades')


@admin_required
def actualizar_novedades(request, pk):
    novedad = get_object_or_404(Novedad, pk=pk)
    return crud_create_update(request, 'novedades', novedad)


@admin_required
def realizar_actualizacion_novedades(request, pk):
    return actualizar_novedades(request, pk)


@admin_required
def borrar_novedades(request, pk):
    return crud_delete(request, 'novedades', pk)


@admin_required
def ver_productos_promociones(request):
    return crud_list_view(request, 'productos_promociones')


@admin_required
def agregar_productos_promociones(request):
    return crud_create_update(request, 'productos_promociones')


@admin_required
def actualizar_productos_promociones(request, pk):
    obj = get_object_or_404(ProductoPromocion, pk=pk)
    return crud_create_update(request, 'productos_promociones', obj)


@admin_required
def realizar_actualizacion_productos_promociones(request, pk):
    return actualizar_productos_promociones(request, pk)


@admin_required
def borrar_productos_promociones(request, pk):
    return crud_delete(request, 'productos_promociones', pk)


@admin_required
def ver_carritos(request):
    return crud_list_view(request, 'carritos')


@admin_required
def agregar_carritos(request):
    return crud_create_update(request, 'carritos')


@admin_required
def actualizar_carritos(request, pk):
    carrito = get_object_or_404(Carrito, pk=pk)
    return crud_create_update(request, 'carritos', carrito)


@admin_required
def realizar_actualizacion_carritos(request, pk):
    return actualizar_carritos(request, pk)


@admin_required
def borrar_carritos(request, pk):
    return crud_delete(request, 'carritos', pk)


@admin_required
def ver_items_carrito(request):
    return crud_list_view(request, 'items_carrito')


@admin_required
def agregar_items_carrito(request):
    return crud_create_update(request, 'items_carrito')


@admin_required
def actualizar_items_carrito(request, pk):
    item = get_object_or_404(ItemCarrito, pk=pk)
    return crud_create_update(request, 'items_carrito', item)


@admin_required
def realizar_actualizacion_items_carrito(request, pk):
    return actualizar_items_carrito(request, pk)


@admin_required
def borrar_items_carrito(request, pk):
    return crud_delete(request, 'items_carrito', pk)


@admin_required
def ver_pedidos(request):
    return crud_list_view(request, 'pedidos')


@admin_required
def agregar_pedidos(request):
    return crud_create_update(request, 'pedidos')


@admin_required
def actualizar_pedidos(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return crud_create_update(request, 'pedidos', pedido)


@admin_required
def realizar_actualizacion_pedidos(request, pk):
    return actualizar_pedidos(request, pk)


@admin_required
def borrar_pedidos(request, pk):
    return crud_delete(request, 'pedidos', pk)


@admin_required
def ver_detalles_pedido(request):
    return crud_list_view(request, 'detalles_pedido')


@admin_required
def agregar_detalles_pedido(request):
    return crud_create_update(request, 'detalles_pedido')


@admin_required
def actualizar_detalles_pedido(request, pk):
    detalle = get_object_or_404(DetallePedido, pk=pk)
    return crud_create_update(request, 'detalles_pedido', detalle)


@admin_required
def realizar_actualizacion_detalles_pedido(request, pk):
    return actualizar_detalles_pedido(request, pk)


@admin_required
def borrar_detalles_pedido(request, pk):
    return crud_delete(request, 'detalles_pedido', pk)


@admin_required
def ver_mensajes_contacto(request):
    return crud_list_view(request, 'mensajes_contacto')


@admin_required
def agregar_mensajes_contacto(request):
    return crud_create_update(request, 'mensajes_contacto')


@admin_required
def actualizar_mensajes_contacto(request, pk):
    mensaje = get_object_or_404(MensajeContacto, pk=pk)
    return crud_create_update(request, 'mensajes_contacto', mensaje)


@admin_required
def realizar_actualizacion_mensajes_contacto(request, pk):
    return actualizar_mensajes_contacto(request, pk)


@admin_required
def borrar_mensajes_contacto(request, pk):
    return crud_delete(request, 'mensajes_contacto', pk)