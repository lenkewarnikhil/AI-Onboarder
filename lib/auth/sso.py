"""
SSO Authentication Manager for Streamlit
Implements OAuth 2.0 flow with multiple providers
"""

import streamlit as st
import os
from typing import Optional, Dict, Any, Callable
import secrets
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
import json

from lib.logger import create_logger
from lib.auth.providers import OAuthProvider, get_provider_config

log = create_logger('Auth')

class AuthManager:
    """Manages SSO authentication for the application"""
    
    def __init__(self):
        self.enabled_providers = self._load_enabled_providers()
        self.callback_url = self._get_callback_url()
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour default
    
    def _get_callback_url(self) -> str:
        """Get the OAuth callback URL, with support for Streamlit Cloud"""
        # First, check if explicitly set in environment
        if os.getenv('SSO_CALLBACK_URL'):
            return os.getenv('SSO_CALLBACK_URL')
        
        # Try to detect if running on Streamlit Cloud
        # Streamlit Cloud sets specific environment variables
        if os.getenv('STREAMLIT_SERVER_HEADLESS') == 'true':
            # Running on Streamlit Cloud
            # Construct URL from app URL if available
            app_url = os.getenv('STREAMLIT_RUNTIME_APP_URL')
            if app_url:
                log.info(f'Detected Streamlit Cloud deployment: {app_url}')
                return app_url
        
        # Default to localhost for local development
        return 'http://localhost:8501'
        
    def _load_enabled_providers(self) -> Dict[OAuthProvider, Dict[str, str]]:
        """Load enabled OAuth providers from environment variables"""
        providers = {}
        
        # Google OAuth
        if os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'):
            providers[OAuthProvider.GOOGLE] = {
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET')
            }
            
        # GitHub OAuth
        if os.getenv('GITHUB_CLIENT_ID') and os.getenv('GITHUB_CLIENT_SECRET'):
            providers[OAuthProvider.GITHUB] = {
                'client_id': os.getenv('GITHUB_CLIENT_ID'),
                'client_secret': os.getenv('GITHUB_CLIENT_SECRET')
            }
            
        # Microsoft OAuth
        if os.getenv('MICROSOFT_CLIENT_ID') and os.getenv('MICROSOFT_CLIENT_SECRET'):
            providers[OAuthProvider.MICROSOFT] = {
                'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
                'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET')
            }
            
        # Okta OAuth
        if os.getenv('OKTA_CLIENT_ID') and os.getenv('OKTA_CLIENT_SECRET') and os.getenv('OKTA_DOMAIN'):
            providers[OAuthProvider.OKTA] = {
                'client_id': os.getenv('OKTA_CLIENT_ID'),
                'client_secret': os.getenv('OKTA_CLIENT_SECRET'),
                'domain': os.getenv('OKTA_DOMAIN')
            }
            
        return providers
    
    def is_enabled(self) -> bool:
        """Check if SSO is enabled"""
        return len(self.enabled_providers) > 0
    
    def get_login_url(self, provider: OAuthProvider) -> str:
        """Generate OAuth login URL for the provider"""
        if provider not in self.enabled_providers:
            raise ValueError(f"Provider {provider} is not configured")
        
        config = get_provider_config(
            provider,
            self.enabled_providers.get(provider, {}).get('domain')
        )
        credentials = self.enabled_providers[provider]
        
        # Generate state token for CSRF protection
        # Include provider name in state for reliable callback handling
        state = f"{provider.value}_{secrets.token_urlsafe(32)}"
        st.session_state.oauth_state = state
        st.session_state.oauth_provider = provider.value
        
        # Build authorization URL
        redirect_uri = f"{self.callback_url}/" if not self.callback_url.endswith('/') else self.callback_url
        params = {
            'client_id': credentials['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(config.scopes),
            'state': state
        }
        
        login_url = f"{config.authorize_url}?{urlencode(params)}"
        
        # Log for debugging (sensitive data not included)
        log.info(f'=== OAuth Login URL Generation ===')
        log.info(f'Generated login URL successfully')
        
        return login_url
    
    def handle_callback(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """Handle OAuth callback and exchange code for token"""
        # Extract provider from state token (format: provider_randomtoken)
        try:
            provider_name = state.split('_')[0] if '_' in state else None
            if not provider_name or provider_name not in [p.value for p in self.enabled_providers]:
                # Fallback to session state
                saved_state = st.session_state.get('oauth_state')
                provider_name = st.session_state.get('oauth_provider')
                
                # Verify state token
                if state != saved_state:
                    log.error(f'Invalid OAuth state token. Expected: {saved_state}, Got: {state}')
                    log.info('This can happen if session was lost. Try logging in again.')
                    return None
            
            provider = OAuthProvider(provider_name)
            if provider not in self.enabled_providers:
                log.error(f'Provider {provider} not configured')
                return None
        except Exception as e:
            log.error(f'Error parsing OAuth callback: {str(e)}')
            return None
        
        config = get_provider_config(
            provider,
            self.enabled_providers.get(provider, {}).get('domain')
        )
        credentials = self.enabled_providers[provider]
        
        # Prepare callback URL (ensure trailing slash)
        redirect_uri = f"{self.callback_url}/" if not self.callback_url.endswith('/') else self.callback_url
        
        # Exchange code for access token
        token_data = {
            'client_id': credentials['client_id'],
            'client_secret': credentials['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        try:
            log.info(f'Exchanging OAuth code for {provider.value} token')
            log.debug(f'Token endpoint: {config.token_url}')
            log.debug(f'Redirect URI: {redirect_uri}')
            
            headers = {'Accept': 'application/json'} if provider == OAuthProvider.GITHUB else {}
            response = requests.post(config.token_url, data=token_data, headers=headers, timeout=10)
            
            if not response.ok:
                error_msg = response.text
                log.error(f'OAuth token exchange failed: HTTP {response.status_code}')
                log.error(f'Response: {error_msg}')
                return None
            
            response.raise_for_status()
            token_response = response.json()
            
            access_token = token_response.get('access_token')
            if not access_token:
                log.error('No access token in response')
                log.debug(f'Response: {token_response}')
                return None
            
            log.info(f'Successfully obtained access token for {provider.value}')
            
            # Get user info
            user_info = self._get_user_info(provider, access_token, config)
            if user_info:
                # Store in session
                self._create_session(user_info, provider)
                return user_info
            
        except requests.exceptions.Timeout:
            log.error(f'OAuth token exchange timeout. Check your internet connection.')
            return None
        except requests.exceptions.ConnectionError as e:
            log.error(f'Connection error during OAuth token exchange: {str(e)}')
            log.error(f'This may indicate a network issue or firewall blocking the connection.')
            return None
        except Exception as e:
            log.error(f'OAuth callback error: {str(e)}')
            import traceback
            log.debug(traceback.format_exc())
            return None
    
    def _get_user_info(self, provider: OAuthProvider, access_token: str, config) -> Optional[Dict[str, Any]]:
        """Fetch user information from provider"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(config.userinfo_url, headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            # Normalize user data across providers
            normalized = self._normalize_user_data(provider, user_data)
            return normalized
            
        except Exception as e:
            log.error(f'Error fetching user info: {str(e)}')
            return None
    
    def _normalize_user_data(self, provider: OAuthProvider, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize user data across different providers"""
        if provider == OAuthProvider.GOOGLE:
            return {
                'id': data.get('id'),
                'email': data.get('email'),
                'name': data.get('name'),
                'picture': data.get('picture'),
                'provider': provider.value
            }
        elif provider == OAuthProvider.GITHUB:
            return {
                'id': str(data.get('id')),
                'email': data.get('email') or f"{data.get('login')}@github.user",
                'name': data.get('name') or data.get('login'),
                'picture': data.get('avatar_url'),
                'provider': provider.value
            }
        elif provider == OAuthProvider.MICROSOFT:
            return {
                'id': data.get('id'),
                'email': data.get('mail') or data.get('userPrincipalName'),
                'name': data.get('displayName'),
                'picture': None,  # Microsoft Graph requires separate call for photo
                'provider': provider.value
            }
        elif provider == OAuthProvider.OKTA:
            return {
                'id': data.get('sub'),
                'email': data.get('email'),
                'name': data.get('name'),
                'picture': None,
                'provider': provider.value
            }
        return data
    
    def _create_session(self, user_info: Dict[str, Any], provider: OAuthProvider):
        """Create authenticated session"""
        from lib.database import create_or_update_user
        
        # Save/update user in database
        user = create_or_update_user(
            provider_id=user_info['id'],
            provider=provider.value,
            email=user_info['email'],
            name=user_info['name'],
            picture=user_info.get('picture')
        )
        
        # Store in session
        st.session_state.authenticated = True
        st.session_state.user = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'picture': user.get('picture'),
            'provider': user['provider']
        }
        st.session_state.auth_timestamp = datetime.now().isoformat()
        
        log.info(f'User {user["email"]} authenticated via {provider.value}')
    
    def logout(self):
        """Logout user and clear session"""
        if 'user' in st.session_state:
            log.info(f'User {st.session_state.user.get("email")} logged out')
        
        # Clear auth-related session state
        for key in ['authenticated', 'user', 'auth_timestamp', 'oauth_state', 'oauth_provider']:
            if key in st.session_state:
                del st.session_state[key]
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if not st.session_state.get('authenticated'):
            return False
        
        # Check session timeout
        auth_time = st.session_state.get('auth_timestamp')
        if auth_time:
            auth_dt = datetime.fromisoformat(auth_time)
            if datetime.now() - auth_dt > timedelta(seconds=self.session_timeout):
                log.info('Session expired')
                self.logout()
                return False
        
        return True
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        if self.is_authenticated():
            return st.session_state.get('user')
        return None

# Singleton instance
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get the auth manager singleton"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager

def get_current_user() -> Optional[Dict[str, Any]]:
    """Helper function to get current user"""
    return get_auth_manager().get_current_user()

def login_required(func: Callable) -> Callable:
    """Decorator to require authentication for a function"""
    def wrapper(*args, **kwargs):
        auth = get_auth_manager()
        if not auth.is_enabled():
            # SSO not configured, allow access
            return func(*args, **kwargs)
        
        if not auth.is_authenticated():
            st.warning('Please log in to access this page')
            st.stop()
        
        return func(*args, **kwargs)
    return wrapper
