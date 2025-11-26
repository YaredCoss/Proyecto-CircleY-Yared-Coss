# app_clientes/context_processors.py
from .models import Categoria, Carrito


def menu_context(request):
    categorias = Categoria.objects.all()
    carrito_activo = None
    total_items = 0

    if request.user.is_authenticated and hasattr(request.user, 'cliente'):
        carrito_activo = Carrito.objects.filter(cliente=request.user.cliente, activo=True).first()
        if carrito_activo:
            total_items = sum(item.cantidad for item in carrito_activo.items.all())

    return {
        'categorias_menu': categorias,
        'carrito_activo': carrito_activo,
        'carrito_total_items': total_items,
    }