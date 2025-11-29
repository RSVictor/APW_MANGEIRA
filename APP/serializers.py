from rest_framework import serializers
from .models import Produto, Categoria, ProdutoImagem

class ProdutoImagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdutoImagem
        fields = ['imagem', 'ordem']

class ProdutoSerializer(serializers.ModelSerializer):
    imagens = ProdutoImagemSerializer(many=True)
    categoria = serializers.StringRelatedField()

    class Meta:
        model = Produto
        fields = [
            'id', 'nome', 'descricao', 'preco',
            'parcelas_max_sem_juros', 'media_avaliacao',
            'total_avaliacoes', 'categoria', 'imagens'
        ]
