from django.db import models
from django.contrib.auth.models import User


class Ingrediente(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Salada(models.Model):
    nome = models.CharField(max_length=100)
    ingredientes = models.ManyToManyField(Ingrediente)
    preco = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # <--- valor da salada
    personalizada = models.BooleanField(default=False)  # <--- customizada = 45 reais

    def save(self, *args, **kwargs):
        if self.personalizada:
            self.preco = 45.00
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    STATUS = (
        ('andamento', 'Em andamento'),
        ('producao', 'Em produção'),
        ('entregue', 'Entregue'),
    )

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    saladas = models.ManyToManyField(Salada)
    status = models.CharField(max_length=20, choices=STATUS, default='andamento')
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    criado_em = models.DateTimeField(auto_now_add=True)

    def calcular_total(self):
        soma = 0
        for s in self.saladas.all():
            soma += s.preco
        self.total = soma
        self.save()

    def __str__(self):
        return f"Pedido {self.id} - {self.usuario.username}"


class Avaliacao(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE)
    nota = models.IntegerField()
    comentario = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Avaliação do pedido {self.pedido.id}"

        from rest_framework import serializers
from .models import Ingrediente, Salada, Pedido, Avaliacao
from django.contrib.auth.models import User


class IngredienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingrediente
        fields = "__all__"


class SaladaSerializer(serializers.ModelSerializer):
    ingredientes_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Ingrediente.objects.all(), write_only=True
    )

    class Meta:
        model = Salada
        fields = ['id', 'nome', 'ingredientes', 'ingredientes_ids', 'preco', 'personalizada']
        read_only_fields = ['preco']

    def create(self, validated_data):
        ingredientes_ids = validated_data.pop('ingredientes_ids')
        salada = Salada.objects.create(**validated_data)
        salada.ingredientes.set(ingredientes_ids)
        salada.save()
        return salada


class PedidoSerializer(serializers.ModelSerializer):
    saladas_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Salada.objects.all(), write_only=True
    )

    class Meta:
        model = Pedido
        fields = ['id', 'usuario', 'saladas', 'saladas_ids', 'status', 'total', 'criado_em']
        read_only_fields = ['total']

    def create(self, validated_data):
        saladas_ids = validated_data.pop('saladas_ids')
        pedido = Pedido.objects.create(**validated_data)
        pedido.saladas.set(saladas_ids)
        pedido.calcular_total()
        return pedido


class AvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avaliacao
        fields = "__all__"

        from rest_framework import viewsets, permissions
from .models import Ingrediente, Salada, Pedido, Avaliacao
from .serializers import *
from rest_framework.permissions import IsAuthenticated


class IngredienteViewSet(viewsets.ModelViewSet):
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer


class SaladaViewSet(viewsets.ModelViewSet):
    queryset = Salada.objects.all()
    serializer_class = SaladaSerializer


class PedidoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

    def get_queryset(self):
        user = self.request.user

        if user.groups.filter(name='FUNCIONARIO').exists():
            return Pedido.objects.all()  # funcionário vê tudo
        return Pedido.objects.filter(usuario=user)  # cliente vê só dele


class AvaliacaoViewSet(viewsets.ModelViewSet):
    queryset = Avaliacao.objects.all()
    serializer_class = AvaliacaoSerializer

    from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from api.views import *

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'ingredientes', IngredienteViewSet)
router.register(r'saladas', SaladaViewSet)
router.register(r'pedidos', PedidoViewSet)
router.register(r'avaliacoes', AvaliacaoViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
]
