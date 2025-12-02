from rest_framework import serializers
from .models import Produto, Categoria, ProdutoImagem
from django.contrib.auth import get_user_model

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



User = get_user_model()

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "password", "nome", "endereco", "cpf", "cargo"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
