from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import ProdutoSerializer, UsuarioSerializer
from .models import Produto, ItemCarrinho, Pedido, Avaliacao, CartaoCredito,Devolucao

# ---- REGISTRAR USUÁRIO ---- #
class RegistrarUsuarioView(generics.CreateAPIView):
    serializer_class = UsuarioSerializer


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

        if not itens_ids:
            return Response({"erro": "Nenhum item informado"}, status=400)

        itens = ItemCarrinho.objects.filter(id__in=itens_ids)

        if not itens.exists():
            return Response({"erro": "Nenhum item encontrado"}, status=400)

        # Validação específica para cartão
        numero = nome = validade = cvv = None
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

        if metodo_pagamento == "CARTAO":
            cartao = CartaoCredito.objects.create(
                usuario=request.user,
                numero=numero,
                nome=nome,
                validade=validade,
                cvv=cvv
            )
            pedido.cartao = cartao
            pedido.save()

        return Response({
            "mensagem": "Pedido criado com sucesso",
            "pedido_id": pedido.id,
            "valor_total": total
        }, status=201)



# ---- PERMISSÕES POR CARGO ---- #
PERMISSOES_STATUS = {
    "FINANCEIRO": ["PAGAMENTO_APROVADO", "PAGAMENTO_REPROVADO", "NOTA_FISCAL_EMITIDA"],
    "LOGISTICA": ["EM_PREPARACAO", "ENVIADO"],
    "CLIENTE": ["RECEBIDO", "SOLICITACAO_DEVOLUCAO"],
    "POS_VENDA": ["EM_DEVOLUCAO", "DEVOLVIDO", "DEVOLUCAO_CANCELADA"],
    "ADMIN": [status for status, _ in Pedido.StatusPedido.choices]
}


# ---- ATUALIZAR STATUS DO PEDIDO ---- #
class StatusPedidoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pedido_id = request.data.get("pedido_id")
        novo_status = request.data.get("status")
        usuario = request.user

        if not pedido_id or not novo_status:
            return Response({"erro": "Campos pedido_id e status são obrigatórios!"}, status=400)

        try:
            pedido = Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            return Response({"erro": "Pedido não encontrado"}, status=404)

        cargo = usuario.cargo.upper()
        status_atual = pedido.status

        # Permissões configuradas no dicionário
        permissoes = PERMISSOES_STATUS.get(cargo, [])

        if novo_status not in permissoes:
            return Response({"erro": "Você não tem permissão para mudar para este status!"}, status=403)

        # Cliente só pode alterar o próprio pedido
        # ---- REGRA ESPECÍFICA CLIENTE ---- #
        if cargo == "CLIENTE":
            if pedido.usuario != usuario:
                return Response({"erro": "Você não pode alterar pedido de outro usuário!"}, status=403)

            # Só pode marcar como RECEBIDO se já foi enviado
            if status_atual == "ENVIADO" and novo_status == "RECEBIDO":
                pedido.status = novo_status
                pedido.save()
                return Response({"mensagem": "Pedido marcado como recebido!"})

            # Só pode pedir devolução se já recebeu
            if status_atual == "RECEBIDO" and novo_status == "SOLICITACAO_DEVOLUCAO":
                pedido.status = novo_status
                pedido.save()
                return Response({"mensagem": "Solicitação de devolução registrada!"})

            return Response({"erro": "Você não pode alterar para este status nessa etapa!"}, status=403)


        # 🔒 Regras da Cadeia do Pedido (ordem obrigatória)
        regras_transicao = {
            "EM_PROCESSAMENTO": ["PAGAMENTO_APROVADO", "PAGAMENTO_REPROVADO"],
            "PAGAMENTO_APROVADO": ["NOTA_FISCAL_EMITIDA"],
            "NOTA_FISCAL_EMITIDA": ["EM_PREPARACAO"],
            "EM_PREPARACAO": ["ENVIADO"],
            "ENVIADO": ["RECEBIDO"],
            "RECEBIDO": ["SOLICITACAO_DEVOLUCAO"],
            "SOLICITACAO_DEVOLUCAO": ["EM_DEVOLUCAO"],
            "EM_DEVOLUCAO": ["DEVOLVIDO", "DEVOLUCAO_CANCELADA"]
        }

        if novo_status not in regras_transicao.get(status_atual, []):
            return Response({"erro": "Transição inválida conforme regras do pedido!"}, status=403)

        # 🧾 Quando emitir nota fiscal → deve gerar código de rastreio
        if novo_status == "NOTA_FISCAL_EMITIDA":
            import uuid
            pedido.codigo_rastreio = f"BR-{uuid.uuid4().hex[:10].upper()}"

        pedido.status = novo_status
        pedido.save()

        return Response({
            "mensagem": "Status atualizado com sucesso!",
            "novo_status": pedido.status,
            "codigo_rastreio": pedido.codigo_rastreio
        })


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

class RegistrarDevolucaoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pedido_id = request.data.get("pedido_id")
        item_id = request.data.get("item_id")
        motivo = request.data.get("motivo")

        if not motivo:
            return Response({"erro": "É obrigatório informar o motivo da devolução!"}, status=400)

        try:
            pedido = Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            return Response({"erro": "Pedido não encontrado!"}, status=404)

        # Cliente só pode criar devolução do próprio pedido
        if "Cliente" in request.user.groups.values_list("name", flat=True):
            if pedido.usuario != request.user:
                return Response({"erro": "Você não pode devolver pedido de outro usuário!"}, status=403)

            if pedido.status != "SOLICITACAO_DEVOLUCAO":
                return Response({"erro": "O pedido ainda não está em processo de devolução!"}, status=403)

        try:
            item = ItemCarrinho.objects.get(id=item_id)
        except ItemCarrinho.DoesNotExist:
            return Response({"erro": "Item não encontrado!"}, status=404)

        # Garantir que o item pertence ao pedido
        if item not in pedido.itens.all():
            return Response({"erro": "Esse item não pertence ao pedido informado!"}, status=403)

        # Evita criar devoluções duplicadas
        if Devolucao.objects.filter(pedido=pedido, item=item).exists():
            return Response({"erro": "Este item já está em devolução!"}, status=400)

        # Criar a devolução corretamente
        Devolucao.objects.create(
            pedido=pedido,
            item=item,
            motivo=motivo
        )

        return Response({
            "mensagem": "Devolução registrada com sucesso!"
        })