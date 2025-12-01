from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings

class Categoria(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome
    
class Produto(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    parcelas_max_sem_juros = models.PositiveIntegerField(default=1)
    media_avaliacao = models.FloatField(default=0)
    total_avaliacoes = models.PositiveIntegerField(default=0)

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="produtos"
    )

    def __str__(self):
        return self.nome


class ProdutoImagem(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.URLField()  
    ordem = models.PositiveIntegerField(default=0)

class Peca(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='pecas')
    nome = models.CharField(max_length=100)
    medida = models.CharField(max_length=100)  
    peso = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f'{self.nome} ({self.produto.nome})'

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O usuário deve ter um email')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    CARGOS = [
        ("CLIENTE", "Cliente"),
        ("FINANCEIRO", "Financeiro"),
        ("LOGISTICA", "Logística"),
        ("POS_VENDA", "Pós Venda"),
        ("ADMIN", "Administrador"),
    ]

    username = None
    email = models.EmailField(unique=True)

    nome = models.CharField(max_length=150)
    endereco = models.TextField()
    cpf = models.CharField(max_length=11, unique=True)

    cargo = models.CharField(
        max_length=20,
        choices=CARGOS,
        default="CLIENTE"  
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'cpf']

    def __str__(self):
        return self.nome
    
class ItemCarrinho(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.produto} x {self.quantidade}'

class Pedido(models.Model):

    class MetodosPagamento(models.TextChoices):
        PIX = "PIX"
        BOLETO = "BOLETO"
        CARTAO = "CARTAO_DE_CREDITO"

    class StatusPedido(models.TextChoices):
        PROCESSAMENTO = "EM_PROCESSAMENTO"
        APROVADO = "PAGAMENTO_APROVADO"
        REPROVADO = "PAGAMENTO_REPROVADO"
        NOTA_FISCAL = "NOTA_FISCAL_EMITIDA"
        PREPARACAO = "EM_PREPARACAO"
        ENVIADO = "ENVIADO"
        RECEBIDO = "RECEBIDO"
        SOLIC_DEV = "SOLICITACAO_DEVOLUCAO"
        EM_DEV = "EM_DEVOLUCAO"
        DEVOLVIDO = "DEVOLVIDO"
        DEV_CANCEL = "DEVOLUCAO_CANCELADA"
        CANCELADO = "CANCELADO"

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    itens = models.ManyToManyField(ItemCarrinho)

    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    metodo_pagamento = models.CharField(max_length=30, choices=MetodosPagamento.choices)
    cartao = models.ForeignKey('CartaoCredito', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')
    status = models.CharField(max_length=40, choices=StatusPedido.choices)

    codigo_rastreio = models.CharField(max_length=50, null=True, blank=True)

    data_criacao = models.DateTimeField(auto_now_add=True)


class CartaoCredito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cartoes')
    numero = models.CharField(max_length=16)
    nome = models.CharField(max_length=100)
    validade = models.CharField(max_length=5)
    cvv = models.CharField(max_length=4)

    def __str__(self):
        return f"**** **** **** {self.numero[-4:]}"

class Devolucao(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    item = models.ForeignKey(ItemCarrinho, on_delete=models.CASCADE)
    motivo = models.TextField()
    data_solicitacao = models.DateField(auto_now_add=True)

class Avaliacao(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    nota = models.IntegerField()

    class Meta:
        unique_together = ('pedido', 'produto')
