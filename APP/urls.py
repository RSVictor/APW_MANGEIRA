from django.urls import path
from .views import (
    ListaProdutosView,
    AddCarrinhoView,
    CriarPedidoView,
    StatusPedidoView,
    AvaliarProdutoView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
 
    path('produtos/', ListaProdutosView.as_view(), name='lista_produtos'),

   
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

   
    path('carrinho/add/', AddCarrinhoView.as_view(), name='add_carrinho'),
    path('pedido/criar/', CriarPedidoView.as_view(), name='criar_pedido'),
    path('pedido/status/', StatusPedidoView.as_view(), name='status_pedido'),

    
    path('produto/avaliar/', AvaliarProdutoView.as_view(), name='avaliar_produto'),
]
