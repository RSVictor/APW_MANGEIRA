from django.contrib import admin
from .models import Categoria, Produto, ProdutoImagem, Peca, Usuario, Pedido, ItemCarrinho, Avaliacao, CartaoCredito, Devolucao

admin.site.register(Categoria)
admin.site.register(Produto)
admin.site.register(ProdutoImagem)
admin.site.register(Peca)
admin.site.register(Usuario)
admin.site.register(ItemCarrinho)
admin.site.register(Pedido)
admin.site.register(Avaliacao)
admin.site.register(CartaoCredito)
admin.site.register(Devolucao)
