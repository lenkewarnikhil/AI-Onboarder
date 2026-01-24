"""
Authentication UI Components for Streamlit
"""

import streamlit as st
import os
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
                
                # Check if running on Streamlit Cloud
                is_cloud = os.getenv('STREAMLIT_SERVER_HEADLESS') == 'true'
                
                if is_cloud:
                    st.warning("""
                    **On Streamlit Cloud? Check these:**
                    
                    1. **Callback URL in GitHub OAuth App**:
                       - Must be exactly: `https://yourusername-appname.streamlit.app/`
                       - ⚠️ Include trailing slash
                       - ⚠️ Use HTTPS (not HTTP)
                    
                    2. **Secrets configured**:
                       - Go to share.streamlit.io → Your App → Settings → Secrets
                       - Add: `SSO_CALLBACK_URL=https://yourusername-appname.streamlit.app`
                       - Add: `GITHUB_CLIENT_ID=your_id`
                       - Add: `GITHUB_CLIENT_SECRET=your_secret`
                    
                    3. **Check logs**:
                       - Go to share.streamlit.io → Your App → Manage app → View logs
                       - Look for error messages
                    
                    See STREAMLIT_CLOUD_SSO_FIX.md for detailed instructions.
                    """)
                else:
                    st.warning("""
                    **Common causes:**
                    - Session expired during login
                    - Multiple browser tabs open
                    - Browser cookies blocked
                    - Callback URL doesn't match OAuth app settings
                    
                    **Solutions:**
                    - Close other tabs and try again
                    - Clear browser cache/cookies
                    - Try in an incognito window
                    - Verify OAuth app settings match your URL
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
            
            # Show configuration info
            is_cloud = os.getenv('STREAMLIT_SERVER_HEADLESS') == 'true'
            if is_cloud:
                with st.expander("📋 Setup Guide for Streamlit Cloud"):
                    st.markdown("""
                    1. Create OAuth app at https://github.com/settings/developers
                    2. Go to share.streamlit.io → Your App → Settings → Secrets
                    3. Add these secrets:
                       ```
                       GITHUB_CLIENT_ID=your_id
                       GITHUB_CLIENT_SECRET=your_secret
                       SSO_CALLBACK_URL=https://yourusername-appname.streamlit.app
                       ```
                    4. Rerun the app
                    """)
            return
        
        st.markdown("### Sign in with:")
        
        # Render login buttons for each enabled provider
        for provider in auth.enabled_providers:
            config = get_provider_config(
                provider,
                auth.enabled_providers.get(provider, {}).get('domain')
            )
            
            login_url = auth.get_login_url(provider)
            
            # Debug: Show the OAuth URL in expandable section
            with st.expander(f"🔍 Debug: {config.name} OAuth URL", expanded=False):
                st.code(login_url, language="text")
                st.caption("Copy this URL and test it in a new tab if the button doesn't work")
            
            # Create a button that uses HTML link for better compatibility
            st.markdown(
                f"""
                <a href="{login_url}" style="text-decoration: none;">
                    <button style="
                        width: 100%;
                        padding: 10px;
                        background-color: #1f1f1f;
                        color: white;
                        border: 1px solid #555;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: 500;
                    ">
                        {config.icon} Sign in with {config.name}
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )
        
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
