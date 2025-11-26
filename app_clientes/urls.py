# app_clientes/urls.py
from django.urls import path
from . import views

app_name = 'app_clientes'

urlpatterns = [
    # Sitio público / clientes
    path('', views.inicio_circley, name='inicio_circley'),
    path('productos/', views.productos_servicios, name='productos_servicios'),
    path('promociones/', views.promociones_view, name='promociones'),
    path('novedades/', views.novedades_view, name='novedades'),
    path('contacto/', views.contacto_view, name='contacto'),
    path('registro/', views.registro_clientes, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/item/<int:item_id>/actualizar/', views.actualizar_item_carrito, name='actualizar_item_carrito'),
    path('carrito/item/<int:item_id>/eliminar/', views.eliminar_item_carrito, name='eliminar_item_carrito'),
    path('checkout/', views.checkout, name='checkout'),
    path('pedidos/historial/', views.historial_pedidos, name='historial_pedidos'),
    path('pedidos/<int:pedido_id>/confirmar/', views.confirmar_entrega_cliente, name='confirmar_entrega_cliente'),

    # Panel admin
    path('admin/dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('admin/clientes/', views.ver_clientes, name='ver_clientes'),
    path('admin/clientes/agregar/', views.agregar_clientes, name='agregar_clientes'),
    path('admin/clientes/<int:pk>/editar/', views.actualizar_clientes, name='actualizar_clientes'),
    path('admin/clientes/<int:pk>/actualizar/', views.realizar_actualizacion_clientes, name='realizar_actualizacion_clientes'),
    path('admin/clientes/<int:pk>/eliminar/', views.borrar_clientes, name='borrar_clientes'),

    path('admin/categorias/', views.ver_categorias, name='ver_categorias'),
    path('admin/categorias/agregar/', views.agregar_categorias, name='agregar_categorias'),
    path('admin/categorias/<int:pk>/editar/', views.actualizar_categorias, name='actualizar_categorias'),
    path('admin/categorias/<int:pk>/actualizar/', views.realizar_actualizacion_categorias, name='realizar_actualizacion_categorias'),
    path('admin/categorias/<int:pk>/eliminar/', views.borrar_categorias, name='borrar_categorias'),

    path('admin/productos/', views.ver_productos, name='ver_productos'),
    path('admin/productos/agregar/', views.agregar_productos, name='agregar_productos'),
    path('admin/productos/<int:pk>/editar/', views.actualizar_productos, name='actualizar_productos'),
    path('admin/productos/<int:pk>/actualizar/', views.realizar_actualizacion_productos, name='realizar_actualizacion_productos'),
    path('admin/productos/<int:pk>/eliminar/', views.borrar_productos, name='borrar_productos'),

    path('admin/promociones/', views.ver_promociones, name='ver_promociones'),
    path('admin/promociones/agregar/', views.agregar_promociones, name='agregar_promociones'),
    path('admin/promociones/<int:pk>/editar/', views.actualizar_promociones, name='actualizar_promociones'),
    path('admin/promociones/<int:pk>/actualizar/', views.realizar_actualizacion_promociones, name='realizar_actualizacion_promociones'),
    path('admin/promociones/<int:pk>/eliminar/', views.borrar_promociones, name='borrar_promociones'),

    path('admin/novedades/', views.ver_novedades, name='ver_novedades'),
    path('admin/novedades/agregar/', views.agregar_novedades, name='agregar_novedades'),
    path('admin/novedades/<int:pk>/editar/', views.actualizar_novedades, name='actualizar_novedades'),
    path('admin/novedades/<int:pk>/actualizar/', views.realizar_actualizacion_novedades, name='realizar_actualizacion_novedades'),
    path('admin/novedades/<int:pk>/eliminar/', views.borrar_novedades, name='borrar_novedades'),

    path('admin/productos-promociones/', views.ver_productos_promociones, name='ver_productos_promociones'),
    path('admin/productos-promociones/agregar/', views.agregar_productos_promociones, name='agregar_productos_promociones'),
    path('admin/productos-promociones/<int:pk>/editar/', views.actualizar_productos_promociones, name='actualizar_productos_promociones'),
    path('admin/productos-promociones/<int:pk>/actualizar/', views.realizar_actualizacion_productos_promociones, name='realizar_actualizacion_productos_promociones'),
    path('admin/productos-promociones/<int:pk>/eliminar/', views.borrar_productos_promociones, name='borrar_productos_promociones'),

    path('admin/carritos/', views.ver_carritos, name='ver_carritos'),
    path('admin/carritos/agregar/', views.agregar_carritos, name='agregar_carritos'),
    path('admin/carritos/<int:pk>/editar/', views.actualizar_carritos, name='actualizar_carritos'),
    path('admin/carritos/<int:pk>/actualizar/', views.realizar_actualizacion_carritos, name='realizar_actualizacion_carritos'),
    path('admin/carritos/<int:pk>/eliminar/', views.borrar_carritos, name='borrar_carritos'),

    path('admin/items-carrito/', views.ver_items_carrito, name='ver_items_carrito'),
    path('admin/items-carrito/agregar/', views.agregar_items_carrito, name='agregar_items_carrito'),
    path('admin/items-carrito/<int:pk>/editar/', views.actualizar_items_carrito, name='actualizar_items_carrito'),
    path('admin/items-carrito/<int:pk>/actualizar/', views.realizar_actualizacion_items_carrito, name='realizar_actualizacion_items_carrito'),
    path('admin/items-carrito/<int:pk>/eliminar/', views.borrar_items_carrito, name='borrar_items_carrito'),

    path('admin/pedidos/', views.ver_pedidos, name='ver_pedidos'),
    path('admin/pedidos/agregar/', views.agregar_pedidos, name='agregar_pedidos'),
    path('admin/pedidos/<int:pk>/editar/', views.actualizar_pedidos, name='actualizar_pedidos'),
    path('admin/pedidos/<int:pk>/actualizar/', views.realizar_actualizacion_pedidos, name='realizar_actualizacion_pedidos'),
    path('admin/pedidos/<int:pk>/eliminar/', views.borrar_pedidos, name='borrar_pedidos'),
    path('admin/pedidos/<int:pedido_id>/confirmar-entrega/', views.confirmar_entrega_admin, name='confirmar_entrega_admin'),

    path('admin/detalles-pedido/', views.ver_detalles_pedido, name='ver_detalles_pedido'),
    path('admin/detalles-pedido/agregar/', views.agregar_detalles_pedido, name='agregar_detalles_pedido'),
    path('admin/detalles-pedido/<int:pk>/editar/', views.actualizar_detalles_pedido, name='actualizar_detalles_pedido'),
    path('admin/detalles-pedido/<int:pk>/actualizar/', views.realizar_actualizacion_detalles_pedido, name='realizar_actualizacion_detalles_pedido'),
    path('admin/detalles-pedido/<int:pk>/eliminar/', views.borrar_detalles_pedido, name='borrar_detalles_pedido'),

    path('admin/mensajes-contacto/', views.ver_mensajes_contacto, name='ver_mensajes_contacto'),
    path('admin/mensajes-contacto/agregar/', views.agregar_mensajes_contacto, name='agregar_mensajes_contacto'),
    path('admin/mensajes-contacto/<int:pk>/editar/', views.actualizar_mensajes_contacto, name='actualizar_mensajes_contacto'),
    path('admin/mensajes-contacto/<int:pk>/actualizar/', views.realizar_actualizacion_mensajes_contacto, name='realizar_actualizacion_mensajes_contacto'),
    path('admin/mensajes-contacto/<int:pk>/eliminar/', views.borrar_mensajes_contacto, name='borrar_mensajes_contacto'),
]