"""
Authentication UI Components for Streamlit
"""

import streamlit as st
from typing import Callable
from lib.auth.sso import get_auth_manager
from lib.auth.providers import OAuthProvider, get_provider_config

def render_login_page():
    """Render the login page with SSO options"""
    auth = get_auth_manager()
    
    # Check for OAuth callback
    query_params = st.query_params
    if 'code' in query_params and 'state' in query_params:
        with st.spinner('Completing login...'):
            user = auth.handle_callback(
                code=query_params['code'],
                state=query_params['state']
            )
            if user:
                st.success(f'Welcome, {user["name"]}!')
                # Clear query params
                st.query_params.clear()
                st.rerun()
            else:
                st.error('❌ Login failed')
                st.warning("""
                **Common causes:**
                - Session expired during login
                - Multiple browser tabs open
                - Browser cookies blocked
                
                **Solutions:**
                - Close other tabs and try again
                - Clear browser cache/cookies
                - Try in an incognito window
                """)
                if st.button("Try Again"):
                    st.query_params.clear()
                    st.rerun()
    
    # Center the login UI
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔐 Sign In")
        st.markdown("---")
        
        if not auth.enabled_providers:
            st.warning("⚠️ SSO is not configured. Please contact your administrator.")
            st.info("To enable SSO, configure OAuth providers in your environment variables.")
            return
        
        st.markdown("### Sign in with:")
        
        # Render login buttons for each enabled provider
        for provider in auth.enabled_providers:
            config = get_provider_config(
                provider,
                auth.enabled_providers.get(provider, {}).get('domain')
            )
            
            if st.button(
                f"{config.icon} Sign in with {config.name}",
                key=f"login_{provider.value}",
                use_container_width=True
            ):
                login_url = auth.get_login_url(provider)
                st.markdown(f'<meta http-equiv="refresh" content="0;url={login_url}">', unsafe_allow_html=True)
        
        st.markdown("---")
        st.caption("🔒 Your data is secure. We only access your basic profile information.")

def render_user_menu():
    """Render user menu in the sidebar"""
    auth = get_auth_manager()
    user = auth.get_current_user()
    
    if not user:
        return
    
    with st.sidebar:
        st.markdown("---")
        
        # User profile section
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if user.get('picture'):
                st.image(user['picture'], width=50)
            else:
                st.markdown("👤")
        
        with col2:
            st.markdown(f"**{user['name']}**")
            st.caption(user['email'])
        
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()

def require_auth(render_func: Callable):
    """
    Wrapper for page render functions that require authentication
    
    Usage:
        @require_auth
        def render(navigate_to):
            st.write("Protected content")
    """
    def wrapper(*args, **kwargs):
        auth = get_auth_manager()
        
        # If SSO is not enabled, allow access
        if not auth.is_enabled():
            return render_func(*args, **kwargs)
        
        # Check authentication
        if not auth.is_authenticated():
            render_login_page()
            st.stop()
        
        # Render user menu
        render_user_menu()
        
        # Render the actual content
        return render_func(*args, **kwargs)
    
    return wrapper

def show_auth_banner():
    """Show authentication status banner"""
    auth = get_auth_manager()
    
    if not auth.is_enabled():
        return
    
    user = auth.get_current_user()
    if user:
        st.info(f"👤 Logged in as **{user['name']}** ({user['email']})")
