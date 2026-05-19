from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Membresia(models.Model):

    TIPOS_PLAN = [
        ('DIARIO', 'Diario'),
        ('MENSUAL', 'Mensual'),
        ('BIMESTRAL', 'Bimestral'),
        ('TRIMESTRAL', 'Trimestral'),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    plan = models.CharField(
        max_length=20,
        choices=TIPOS_PLAN
    )

    fecha_inicio = models.DateField()

    fecha_fin = models.DateField()

    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.plan}"

    def dias_restantes(self):
        hoy = timezone.now().date()
        diferencia = self.fecha_fin - hoy
        return max(diferencia.days, 0)

    def porcentaje_restante(self):
        duraciones = {
            "DIARIO": 1,
            "MENSUAL": 30,
            "BIMESTRAL": 60,
            "TRIMESTRAL": 90,
        }

        duracion_total = duraciones.get(self.plan, 30)

        porcentaje = (self.dias_restantes() / duracion_total) * 100

        return min(max(porcentaje, 0), 100)

    def esta_vencida(self):
        hoy = timezone.now().date()
        return self.fecha_fin < hoy


class Pago(models.Model):

    ESTADOS_PAGO = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADO", "Aprobado"),
        ("RECHAZADO", "Rechazado"),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    plan = models.CharField(max_length=20)

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_PAGO,
        default="PENDIENTE"
    )

    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.plan} - ${self.monto}"


class Perfil(models.Model):

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.usuario.username



@receiver(post_save, sender=User)
def crear_perfil(sender, instance, created, **kwargs):

    if created:
        Perfil.objects.create(usuario=instance)

class Asistencia(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    fecha = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(
        max_length=20,
        default="PERMITIDO"
    )

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha}"
