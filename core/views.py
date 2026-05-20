from django.shortcuts import render, redirect
from .forms import RegistroUsuarioForm
import mercadopago
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from .models import Membresia, Pago, Perfil, Asistencia
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import TruncMonth
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib import messages
import qrcode
from io import BytesIO
from django.core.files import File
from django.core.files.base import ContentFile
import base64


def inicio(request):
    return render(request, "core/inicio.html")


def registro(request):
    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = RegistroUsuarioForm()

    return render(
        request,
        "registration/registro.html",
        {
            "form": form
        }
    )

@login_required
def panel_usuario(request):
    membresia = None

    try:
        membresia = Membresia.objects.get(usuario=request.user)
    except Membresia.DoesNotExist:
        pass

    pagos = Pago.objects.filter(usuario=request.user).order_by("-fecha")

    qr_base64 = None

    if membresia:
        qr_data = f"http://127.0.0.1:8000/verificar-socio/{request.user.id}/"

        qr = qrcode.make(qr_data)

        buffer = BytesIO()

        qr.save(buffer, format="PNG")

        qr_base64 = base64.b64encode(buffer.getvalue()).decode()


    return render(
        request,
        "core/panel_usuario.html",
        {
            "membresia": membresia,
            "pagos": pagos,
            "qr_base64": qr_base64,
        }
    )

@login_required
def pagar_membresia(request, plan):
    planes = {
        "diario": {
            "titulo": "Pase Diario Titan Gym",
            "precio": 3000,
        },
        "mensual": {
            "titulo": "Plan Mensual Titan Gym",
            "precio": 25000,
        },
        "bimestral": {
            "titulo": "Plan Bimestral Titan Gym",
            "precio": 45000,
        },
        "trimestral": {
            "titulo": "Plan Trimestral Titan Gym",
            "precio": 65000,
        },
    }

    if plan not in planes:
        return redirect("inicio")

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    preference_data = {
        "items": [
            {
                "title": planes[plan]["titulo"],
                "quantity": 1,
                "unit_price": planes[plan]["precio"],
                "currency_id": "ARS",
            }
        ],

        "external_reference": f"{request.user.id}-{plan}",

         "back_urls": {
             "success": f"http://127.0.0.1:8000/pago-exitoso/?plan={plan}",
             "failure": "http://127.0.0.1:8000/",
             "pending": "http://127.0.0.1:8000/",
         },



    }

    preference_response = sdk.preference().create(preference_data)

    print("RESPUESTA MERCADO PAGO:")
    print(preference_response)

    preference = preference_response.get("response", {})

    init_point = preference.get("init_point")

    if not init_point:
        print("ERROR MERCADO PAGO:")
        print(preference)
        return redirect("inicio")

    return redirect(init_point)

@login_required
def pago_exitoso(request):
    plan = request.GET.get("plan", "mensual")

    duraciones = {
        "diario": 1,
        "mensual": 30,
        "bimestral": 60,
        "trimestral": 90,
    }

    dias = duraciones.get(plan, 30)

    hoy = timezone.now().date()
    fecha_fin = hoy + timedelta(days=dias)

    membresia, creada = Membresia.objects.get_or_create(
        usuario=request.user,
        defaults={
            "plan": plan.upper(),
            "fecha_inicio": hoy,
            "fecha_fin": fecha_fin,
            "activa": True,
        }
    )

    if not creada:
        membresia.plan = plan.upper()
        membresia.fecha_inicio = hoy
        membresia.fecha_fin = fecha_fin
        membresia.activa = True
        membresia.save()

    precios = {
        "diario": 3000,
        "mensual": 25000,
        "bimestral": 45000,
        "trimestral": 65000,
    }

    Pago.objects.create(
        usuario=request.user,
        plan=plan.upper(),
        monto=precios.get(plan, 25000),
        estado="APROBADO",
    )

    return redirect("panel_usuario")


@staff_member_required
def dashboard_admin(request):

    total_socios = Membresia.objects.filter(
        activa=True
    ).count()

    ingresos_totales = Pago.objects.filter(
        estado="APROBADO"
    ).aggregate(
        total=Sum("monto")
    )["total"] or 0

    pagos_totales = Pago.objects.count()

    membresias_vencidas = Membresia.objects.filter(
        activa=False
    ).count()

    pagos_recientes = Pago.objects.order_by("-fecha")[:5]

    ingresos_por_mes = (
        Pago.objects.filter(estado="APROBADO")
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    labels_grafico = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", ]
    datos_grafico = [0, 0, 0, 0, 0, 0]
    meses = {"January": 0, "February": 1, "March": 2, "April": 3, "May": 4, "June": 5, }

    for item in ingresos_por_mes:

        mes_nombre = item["mes"].strftime("%B")

        if mes_nombre in meses:

            index = meses[mes_nombre]

            datos_grafico[index] = float(item["total"])

    busqueda = request.GET.get("q", "")

    socios = User.objects.filter(is_staff=False)

    if busqueda:
        socios = socios.filter(
            username__icontains=busqueda
        ) | socios.filter(
            email__icontains=busqueda
        )

    socios = socios.order_by("username")

    hoy = timezone.now().date()

    proximos_vencimientos = Membresia.objects.filter(
        fecha_fin__gte=hoy,
        fecha_fin__lte=hoy + timedelta(days=7)
    ).order_by("fecha_fin")

    socios_suspendidos = User.objects.filter(
        is_staff=False,
        is_active=False
    ).count()

    socios_activos = User.objects.filter(
        is_staff=False,
        is_active=True
    ).count()


    asistencias_recientes = Asistencia.objects.order_by(
        "-fecha"
    )[:10]


    context = {
        "total_socios": total_socios,
        "ingresos_totales": ingresos_totales,
        "pagos_totales": pagos_totales,
        "membresias_vencidas": membresias_vencidas,
        "pagos_recientes": pagos_recientes,
        "labels_grafico": json.dumps(labels_grafico),
        "datos_grafico": json.dumps(datos_grafico),
        "socios": socios,
        "busqueda": busqueda,
        "proximos_vencimientos": proximos_vencimientos,
        "socios_suspendidos": socios_suspendidos,
        "socios_activos": socios_activos,
        "asistencias_recientes": asistencias_recientes,
    }

    return render(
        request,
        "core/dashboard_admin.html",
        context
    )

@csrf_exempt
def webhook_mercado_pago(request):
    print("WEBHOOK RECIBIDO")
    print(request.GET)
    print(request.body)

    return JsonResponse({"status": "ok"})

@staff_member_required
def editar_membresia(request, user_id):

    usuario = get_object_or_404(User, id=user_id)

    membresia = Membresia.objects.filter(usuario=usuario).first()

    if request.method == "POST":

        plan = request.POST.get("plan")
        fecha_fin = request.POST.get("fecha_fin")

        hoy = timezone.now().date()

        if membresia:
            membresia.plan = plan
            membresia.fecha_fin = fecha_fin
            membresia.activa = True
            membresia.save()

        else:
            Membresia.objects.create(
                usuario=usuario,
                plan=plan,
                fecha_inicio=hoy,
                fecha_fin=fecha_fin,
                activa=True,
            )

        messages.success(request, "Membresía actualizada correctamente.")

        return redirect("dashboard_admin")

    context = {
        "usuario": usuario,
        "membresia": membresia,
    }

    return render(
        request,
        "core/editar_membresia.html",
        context
    )


@staff_member_required
def crear_socio(request):

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        telefono = request.POST.get("telefono")

        usuario = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        usuario.perfil.telefono = telefono
        usuario.perfil.save()


        messages.success(request, "Socio creado correctamente.")

        return redirect("dashboard_admin")

    messages.success(request, "Socio creado correctamente.")

    return render(request, "core/crear_socio.html")


@staff_member_required
def suspender_socio(request, user_id):

    usuario = get_object_or_404(User, id=user_id)

    usuario.is_active = False
    usuario.save()
    messages.warning(request, "Socio suspendido correctamente.")

    return redirect("dashboard_admin")


@staff_member_required
def reactivar_socio(request, user_id):

    usuario = get_object_or_404(User, id=user_id)

    usuario.is_active = True
    usuario.save()
    messages.success(request, "Socio reactivado correctamente.")

    return redirect("dashboard_admin")


def verificar_socio(request, user_id):

    usuario = get_object_or_404(User, id=user_id)

    membresia = Membresia.objects.filter(
        usuario=usuario
    ).first()

    if membresia and not membresia.esta_vencida():
        Asistencia.objects.create(
            usuario=usuario,
            estado="PERMITIDO"
        )
    else:
        Asistencia.objects.create(
            usuario=usuario,
            estado="DENEGADO"
        )

    context = {
        "usuario": usuario,
        "membresia": membresia,
    }

    return render(
        request,
        "core/verificar_socio.html",
        context
    )

