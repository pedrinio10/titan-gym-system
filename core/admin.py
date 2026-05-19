from django.contrib import admin
from .models import Membresia, Pago, Perfil, Asistencia

admin.site.register(Membresia)
admin.site.register(Pago)
admin.site.register(Perfil)
admin.site.register(Asistencia)