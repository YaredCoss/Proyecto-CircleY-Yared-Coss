# app_clientes/admin.py
from django.contrib import admin
from .models import (
    Cliente, Categoria, Producto, Promocion, ProductoPromocion,
    Novedad, Carrito, ItemCarrito, Pedido, DetallePedido, MensajeContacto
)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefono', 'direccion')
    search_fields = ('user__username', 'user__first_name', 'telefono', 'direccion')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'activo')
    search_fields = ('nombre', 'categoria__nombre')
    list_filter = ('categoria', 'activo')


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_descuento', 'valor_descuento', 'fecha_inicio', 'fecha_fin', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo', 'tipo_descuento')


@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_publicacion')
    search_fields = ('titulo',)


admin.site.register(ProductoPromocion)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(MensajeContacto)