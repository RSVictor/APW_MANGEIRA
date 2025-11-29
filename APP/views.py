from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import ProdutoSerializer
from .models import Produto, ItemCarrinho, Pedido, Avaliacao


# ---- LISTA PRODUTOS ---- #
class ListaProdutosView(generics.ListAPIView):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer


# ---- ADICIONA ITEM AO CARRINHO ---- #
class AddCarrinhoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        produto_id = request.data.get("produto_id")
        quantidade = request.data.get("quantidade", 1)

        try:
            produto = Produto.objects.get(id=produto_id)
        except Produto.DoesNotExist:
            return Response({"erro": "Produto não encontrado"}, status=404)

        item = ItemCarrinho.objects.create(
            produto=produto,
            quantidade=quantidade
        )

        return Response({
            "mensagem": "Item adicionado ao carrinho",
            "item_id": item.id
        })


# ---- CRIAR PEDIDO ---- #
class CriarPedidoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        itens_ids = request.data.get("itens")
        metodo_pagamento = request.data.get("metodo_pagamento")

        itens = ItemCarrinho.objects.filter(id__in=itens_ids)

        if not itens.exists():
            return Response({"erro": "Nenhum item no carrinho"}, status=400)
        
        if metodo_pagamento == "CARTAO":
            numero = request.data.get("numero_cartao")
            nome = request.data.get("nome_cartao")
            validade = request.data.get("validade")
            cvv = request.data.get("cvv")

            if not all([numero, nome, validade, cvv]):
                return Response({"erro": "Dados do cartão incompletos!"}, status=400)

        total = sum(i.produto.preco * i.quantidade for i in itens)

        pedido = Pedido.objects.create(
            usuario=request.user,
            valor_total=total,
            valor_desconto=0,
            metodo_pagamento=metodo_pagamento,
            status="EM_PROCESSAMENTO"
        )
        pedido.itens.set(itens)

        return Response({
            "mensagem": "Pedido criado com sucesso",
            "pedido_id": pedido.id,
            "valor_total": total
        })


# ---- PERMISSÕES DE STATUS ---- #
PERMISSOES_STATUS = {
    "FINANCEIRO": ["PAGAMENTO_APROVADO", "PAGAMENTO_REPROVADO", "NOTA_FISCAL_EMITIDA"],
    "LOGISTICA": ["EM_PREPARACAO", "ENVIADO"],
    "CLIENTE": ["RECEBIDO", "SOLICITACAO_DEVOLUCAO"],
    "POS_VENDA": ["EM_DEVOLUCAO", "DEVOLVIDO", "DEVOLUCAO_CANCELADA"],
}


# ---- ATUALIZAR STATUS DO PEDIDO ---- #
class StatusPedidoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pedido_id = request.data.get("pedido_id")
        novo_status = request.data.get("status")

        try:
            pedido = Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            return Response({"erro": "Pedido não encontrado"}, status=404)

        grupos = request.user.groups.values_list("name", flat=True)

        autorizado = any(
            g in PERMISSOES_STATUS and novo_status in PERMISSOES_STATUS[g]
            for g in grupos
        )

        if not autorizado:
            return Response({"erro": "Você não tem permissão para mudar para este status"}, status=403)

        pedido.status = novo_status
        pedido.save()

        return Response({"mensagem": "Status do pedido atualizado"})


# ---- AVALIAR PRODUTO ---- #
class AvaliarProdutoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pedido_id = request.data.get("pedido_id")
        produto_id = request.data.get("produto_id")
        nota = int(request.data.get("nota"))

        if nota < 1 or nota > 5:
            return Response({"erro": "A nota deve ser entre 1 e 5"}, status=400)

        try:
            pedido = Pedido.objects.get(id=pedido_id, usuario=request.user)
        except Pedido.DoesNotExist:
            return Response({"erro": "Esse pedido não pertence a você"}, status=403)

        try:
            produto = Produto.objects.get(id=produto_id)
        except Produto.DoesNotExist:
            return Response({"erro": "Produto não encontrado"}, status=404)

        Avaliacao.objects.create(
            pedido=pedido,
            produto=produto,
            nota=nota
        )

        avaliacoes = Avaliacao.objects.filter(produto=produto)
        total = avaliacoes.count()
        media = sum(a.nota for a in avaliacoes) / total

        produto.media_avaliacao = media
        produto.total_avaliacoes = total
        produto.save()

        return Response({
            "mensagem": "Avaliação registrada!",
            "media_atual": media,
            "total_avaliacoes": total
        })
