from django.urls import path

from .views.assets import (
    AssetDashboardView,
    AssetDeployGuardianEndpoint,
    AssetExposeView,
    AssetRegisterPolicyIssuerEndpoint,
    AssetSetupView,
    AssetsListView,
    AssetUpdatePolicyDataEndpoint,
    AssetUseEndpoint,
)
from .views.channel_keys import ChannelKeyGenerateEndpoint
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
#
# Wallets/assets are addressed by their on-ledger contract_id. Because
# PDO contract ids are base64 hashes (containing `/`, `+`, `=`), we
# carry them through URL paths under their URL-safe encoding
# (`app.url_safe_id`) bound to the `cid_url` kwarg. Views decode it
# back to the raw contract_id at the boundary.
urlpatterns = [
    # Assets (pages)
    path("", AssetsListView.as_view(), name="assets_page"),
    path("assets/setup/", AssetSetupView.as_view(), name="asset_setup"),
    path(
        "assets/<str:cid_url>/",
        AssetDashboardView.as_view(),
        name="asset_dashboard",
    ),
    path(
        "assets/<str:cid_url>/expose/",
        AssetExposeView.as_view(),
        name="asset_expose",
    ),
    # Wallets (pages)
    path("wallets/", WalletsListView.as_view(), name="wallets"),
    path(
        "wallets/<str:cid_url>/",
        WalletDetailView.as_view(),
        name="wallet_detail",
    ),
    # Config + identity (pages)
    path("config/", ConfigPageView.as_view(), name="config"),
    path("identity/set/", IdentitySetView.as_view(), name="identity_set"),
    # Channel key
    path(
        "api/channel-key/generate/",
        ChannelKeyGenerateEndpoint.as_view(),
        name="api_channel_key_generate",
    ),
    # JSON endpoints
    path("api/assets/use/", AssetUseEndpoint.as_view(), name="api_asset_use"),
    path(
        "api/assets/<str:cid_url>/deploy-guardian/",
        AssetDeployGuardianEndpoint.as_view(),
        name="api_asset_deploy_guardian",
    ),
    path(
        "api/assets/<str:cid_url>/register-policy-issuer/",
        AssetRegisterPolicyIssuerEndpoint.as_view(),
        name="api_asset_register_policy_issuer",
    ),
    path(
        "api/assets/<str:cid_url>/update-policy-data/",
        AssetUpdatePolicyDataEndpoint.as_view(),
        name="api_asset_update_policy_data",
    ),
    path(
        "api/wallets/<str:cid_url>/add-vc/",
        WalletAddVCEndpoint.as_view(),
        name="api_wallet_add_vc",
    ),
    path(
        "api/wallets/<str:cid_url>/register-issuer/",
        WalletRegisterIssuerEndpoint.as_view(),
        name="api_wallet_register_issuer",
    ),
    path(
        "api/wallets/<str:cid_url>/sign-credential/",
        WalletSignCredentialEndpoint.as_view(),
        name="api_wallet_sign_credential",
    ),
]
