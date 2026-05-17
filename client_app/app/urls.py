from django.urls import path

from .views.assets import (
    AssetExposeView,
    AssetSetupView,
    AssetsListView,
    AssetUseEndpoint,
)
from .views.config import ConfigPageView, IdentitySetView
from .views.wallets import (
    WalletAddVCEndpoint,
    WalletDetailView,
    WalletRegisterIssuerEndpoint,
    WalletSignCredentialEndpoint,
    WalletsListView,
)

# Two URL families:
#   * Page URLs: GET renders, POST handles the page's one primary form
#     (then redirects). Used when a page has at most one logical action.
#   * /api/... endpoints: POST-only, accept and return JSON. Used by JS
#     for pages where multiple distinct actions are possible.
urlpatterns = [
    # Assets (pages)
    path('', AssetsListView.as_view(), name='assets_page'),
    path('assets/setup/', AssetSetupView.as_view(), name='asset_setup'),
    path('assets/<int:pk>/expose/', AssetExposeView.as_view(), name='asset_expose'),

    # Wallets (pages)
    path('wallets/', WalletsListView.as_view(), name='wallets'),
    path('wallets/<int:pk>/', WalletDetailView.as_view(), name='wallet_detail'),

    # Config + identity (pages)
    path('config/', ConfigPageView.as_view(), name='config'),
    path('identity/set/', IdentitySetView.as_view(), name='identity_set'),

    # JSON endpoints
    path('api/assets/use/',
         AssetUseEndpoint.as_view(), name='api_asset_use'),
    path('api/wallets/<int:pk>/add-vc/',
         WalletAddVCEndpoint.as_view(), name='api_wallet_add_vc'),
    path('api/wallets/<int:pk>/register-issuer/',
         WalletRegisterIssuerEndpoint.as_view(), name='api_wallet_register_issuer'),
    path('api/wallets/<int:pk>/sign-credential/',
         WalletSignCredentialEndpoint.as_view(), name='api_wallet_sign_credential'),
]
