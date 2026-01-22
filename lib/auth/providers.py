"""
OAuth Provider configurations for SSO
"""

from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass

class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    OKTA = "okta"

@dataclass
class ProviderConfig:
    """Configuration for an OAuth provider"""
    name: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list
    icon: str

# Provider configurations
PROVIDER_CONFIGS: Dict[OAuthProvider, ProviderConfig] = {
    OAuthProvider.GOOGLE: ProviderConfig(
        name="Google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
        scopes=["openid", "email", "profile"],
        icon="🔵"
    ),
    OAuthProvider.GITHUB: ProviderConfig(
        name="GitHub",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        scopes=["read:user", "user:email"],
        icon="🔲"
    ),
    OAuthProvider.MICROSOFT: ProviderConfig(
        name="Microsoft",
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/v1.0/me",
        scopes=["openid", "email", "profile"],
        icon="🔷"
    ),
    OAuthProvider.OKTA: ProviderConfig(
        name="Okta",
        authorize_url="",  # Set via OKTA_DOMAIN env var
        token_url="",      # Set via OKTA_DOMAIN env var
        userinfo_url="",   # Set via OKTA_DOMAIN env var
        scopes=["openid", "email", "profile"],
        icon="🟠"
    )
}

def get_provider_config(provider: OAuthProvider, okta_domain: str = None) -> ProviderConfig:
    """Get configuration for a specific provider"""
    config = PROVIDER_CONFIGS[provider]
    
    # Special handling for Okta which needs domain
    if provider == OAuthProvider.OKTA and okta_domain:
        config.authorize_url = f"https://{okta_domain}/oauth2/default/v1/authorize"
        config.token_url = f"https://{okta_domain}/oauth2/default/v1/token"
        config.userinfo_url = f"https://{okta_domain}/oauth2/default/v1/userinfo"
    
    return config
