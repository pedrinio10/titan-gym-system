from django.urls import path
from .views import inicio, registro, panel_usuario, pagar_membresia, pago_exitoso, dashboard_admin, editar_membresia, crear_socio, suspender_socio, reactivar_socio, verificar_socio
from .views import webhook_mercado_pago

urlpatterns = [
    path('', inicio, name='inicio'),
    path('registro/', registro, name='registro'),
    path('panel/', panel_usuario, name='panel_usuario'),
    path("pagar/<str:plan>/", pagar_membresia, name="pagar_membresia"),
    path("pago-exitoso/", pago_exitoso, name="pago_exitoso"),
    path("dashboard-admin/", dashboard_admin, name="dashboard_admin"),
    path("webhook/mercado-pago/", webhook_mercado_pago, name="webhook_mercado_pago"),
    path("editar-membresia/<int:user_id>/",editar_membresia,name="editar_membresia"),
    path("crear-socio/", crear_socio, name="crear_socio"),
    path("suspender-socio/<int:user_id>/",suspender_socio,name="suspender_socio"),
    path("reactivar-socio/<int:user_id>/",reactivar_socio,name="reactivar_socio"),
    path("verificar-socio/<int:user_id>/",verificar_socio,name="verificar_socio"),

]
