from django.db import models

class Registro(models.Model):
    tipo_documento = models.CharField(max_length=10, blank=True, default="")
    documento = models.CharField(max_length=32, blank=True, default="")
    nombre = models.CharField(max_length=200, blank=True, default="")
    producto = models.CharField(max_length=32, blank=True, default="")
    poliza = models.CharField(max_length=64, blank=True, default="")
    periodo = models.CharField(max_length=4, blank=True, default="")

    # valores grandes, permitimos decimales
    valor_asegurado = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    valor_prima = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    doc_cobro = models.CharField(max_length=64, blank=True, default="")
    fecha_ini = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)  # queda vacío por regla
    dias = models.IntegerField(null=True, blank=True)

    telefono_1 = models.CharField(max_length=32, blank=True, default="")
    telefono_2 = models.CharField(max_length=32, blank=True, default="")
    telefono_3 = models.CharField(max_length=32, blank=True, default="")

    ciudad = models.CharField(max_length=100, blank=True, default="")
    departamento = models.CharField(max_length=100, blank=True, default="")

    fecha_venta = models.DateField(null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    tipo_trans = models.CharField(max_length=8, blank=True, default="")
    beneficiarios = models.TextField(blank=True, default="")

    genero = models.CharField(max_length=4, blank=True, default="")
    sucursal = models.CharField(max_length=120, blank=True, default="")

    tipo_cuenta = models.CharField(max_length=32, blank=True, default="")  # vacío por regla
    ultimos_digitos_cuenta = models.CharField(max_length=32, blank=True, default="")
    entidad_bancaria = models.CharField(max_length=64, blank=True, default="")
    nombre_banco = models.CharField(max_length=120, blank=True, default="")
    estado_debito = models.CharField(max_length=32, blank=True, default="")
    causal_rechazo = models.CharField(max_length=120, blank=True, default="")

    codigo_canal = models.CharField(max_length=8, blank=True, default="")
    descripcion_canal = models.CharField(max_length=200, blank=True, default="")
    codigo_estrategia = models.CharField(max_length=64, blank=True, default="")
    tipo_estrategia = models.CharField(max_length=64, blank=True, default="")
    correo_electronico = models.EmailField(blank=True, default="")

    fecha_entrega_colmena = models.DateField(null=True, blank=True)
    mes_a_trabajar = models.CharField(max_length=2, blank=True, default="")
    nombre_db = models.CharField(max_length=120, blank=True, default="")

    # flags
    telefono = models.BooleanField(default=False)
    whatsapp = models.BooleanField(default=False)
    texto = models.BooleanField(default=False)
    email = models.BooleanField(default=False)
    fisica = models.BooleanField(default=False)

    mejor_canal = models.CharField(max_length=20, blank=True, default="")
    contactar_al = models.CharField(max_length=200, blank=True, default="")

    # id (vacío por regla) => usamos el PK autoincremental de Django
    created_at = models.DateTimeField(auto_now_add=True)
