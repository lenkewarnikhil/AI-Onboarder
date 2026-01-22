"""
Authentication module for AI-Onboarder
Supports SSO via OAuth 2.0
"""

from .sso import get_auth_manager, login_required, get_current_user
from .providers import OAuthProvider

__all__ = ['get_auth_manager', 'login_required', 'get_current_user', 'OAuthProvider']
