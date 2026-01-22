# 🔐 SSO (Single Sign-On) Setup Guide

This guide will help you configure SSO authentication for AI-Onboarder using OAuth 2.0 providers.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Provider Setup Guides](#provider-setup-guides)
  - [Google OAuth](#google-oauth)
  - [GitHub OAuth](#github-oauth)
  - [Microsoft Azure AD](#microsoft-azure-ad)
  - [Okta](#okta)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

SSO is **optional** for AI-Onboarder. By default, the application runs with open access. When SSO is configured, users must authenticate before accessing the application.

### Benefits of SSO

- 🔒 **Secure Access**: Control who can access your AI-Onboarder instance
- 👥 **User Management**: Track user activity and permissions
- 🔑 **No Passwords**: Use existing corporate identities
- 📊 **Audit Trail**: Monitor login activity

### Supported Providers

- **Google** - Sign in with Google accounts
- **GitHub** - Sign in with GitHub accounts
- **Microsoft** - Sign in with Microsoft/Azure AD accounts
- **Okta** - Enterprise SSO via Okta

---

## Quick Start

### Step 1: Choose Your Provider(s)

You can enable one or multiple OAuth providers. Most organizations choose one of:
- **Google** - For Gmail/Workspace users
- **GitHub** - For developer teams
- **Microsoft** - For Office 365 organizations
- **Okta** - For enterprise SSO

### Step 2: Register OAuth Application

Follow the provider-specific guide below to register your application and obtain:
- **Client ID**
- **Client Secret**
- **Redirect URI** (usually `http://localhost:8501/` for local dev)

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env` and add your OAuth credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials (see provider sections below).

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run the Application

```bash
streamlit run app.py
```

You'll now see a login screen instead of direct access!

---

## Provider Setup Guides

### Google OAuth

#### 1. Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google+ API**:
   - Navigate to **APIs & Services** > **Library**
   - Search for "Google+ API" and enable it

4. Create OAuth credentials:
   - Go to **APIs & Services** > **Credentials**
   - Click **Create Credentials** > **OAuth 2.0 Client ID**
   - Select **Web application**
   - Add these authorized redirect URIs:
     - `http://localhost:8501/` (for local development)
     - `https://yourdomain.com/` (for production)
   - Click **Create**

5. Copy your **Client ID** and **Client Secret**

#### 2. Configure .env

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SSO_CALLBACK_URL=http://localhost:8501
```

#### 3. Test

Run the app and click "Sign in with Google" 🔵

---

### GitHub OAuth

#### 1. Register OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in the details:
   - **Application name**: `AI-Onboarder`
   - **Homepage URL**: `http://localhost:8501`
   - **Authorization callback URL**: `http://localhost:8501/`
4. Click **Register application**
5. Click **Generate a new client secret**
6. Copy your **Client ID** and **Client Secret**

#### 2. Configure .env

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
SSO_CALLBACK_URL=http://localhost:8501
```

#### 3. Test

Run the app and click "Sign in with GitHub" 🔲

---

### Microsoft Azure AD

#### 1. Register Application

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: `AI-Onboarder`
   - **Supported account types**: Choose appropriate option
   - **Redirect URI**: 
     - Type: **Web**
     - URI: `http://localhost:8501/`
5. Click **Register**

6. Note your **Application (client) ID**

7. Create a client secret:
   - Go to **Certificates & secrets**
   - Click **New client secret**
   - Add description and expiry
   - Copy the **Value** (this is your client secret)

8. Configure API permissions:
   - Go to **API permissions**
   - Ensure these Microsoft Graph permissions are present:
     - `User.Read` (should be default)
     - `email`
     - `profile`
     - `openid`

#### 2. Configure .env

```bash
# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-application-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret-value
SSO_CALLBACK_URL=http://localhost:8501
```

#### 3. Test

Run the app and click "Sign in with Microsoft" 🔷

---

### Okta

#### 1. Create OIDC Application

1. Log in to your [Okta Admin Console](https://admin.okta.com/)
2. Go to **Applications** > **Applications**
3. Click **Create App Integration**
4. Choose:
   - **Sign-in method**: OIDC - OpenID Connect
   - **Application type**: Web Application
5. Configure:
   - **App integration name**: `AI-Onboarder`
   - **Sign-in redirect URIs**: `http://localhost:8501/`
   - **Sign-out redirect URIs**: `http://localhost:8501/`
   - **Assignments**: Choose who can access
6. Click **Save**
7. Copy your **Client ID** and **Client Secret**
8. Note your **Okta domain** (e.g., `dev-12345.okta.com`)

#### 2. Configure .env

```bash
# Okta OAuth
OKTA_DOMAIN=dev-12345.okta.com
OKTA_CLIENT_ID=your_okta_client_id
OKTA_CLIENT_SECRET=your_okta_client_secret
SSO_CALLBACK_URL=http://localhost:8501
```

#### 3. Test

Run the app and click "Sign in with Okta" 🟠

---

## Configuration

### Environment Variables

All SSO configuration is done via environment variables in `.env`:

```bash
# Required for OAuth callbacks
SSO_CALLBACK_URL=http://localhost:8501

# Session timeout (seconds) - default: 3600 (1 hour)
SESSION_TIMEOUT=3600

# Add credentials for one or more providers
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...

OKTA_DOMAIN=...
OKTA_CLIENT_ID=...
OKTA_CLIENT_SECRET=...
```

### Production Deployment

When deploying to production:

1. **Update callback URLs** in your OAuth app settings:
   ```
   https://your-production-domain.com/
   ```

2. **Update .env**:
   ```bash
   SSO_CALLBACK_URL=https://your-production-domain.com
   ```

3. **Use HTTPS**: OAuth requires HTTPS in production

4. **Secure secrets**: Use proper secret management (not plain .env files)

### Disabling SSO

To disable SSO and allow open access, simply remove or comment out all OAuth credentials in `.env`:

```bash
# GOOGLE_CLIENT_ID=  # Commented out = disabled
# GOOGLE_CLIENT_SECRET=
```

---

## Testing

### Test SSO Configuration

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Check for login page**: You should see SSO login buttons instead of direct access

3. **Test login flow**:
   - Click on a provider button
   - Authenticate with the provider
   - Should redirect back with user logged in

4. **Test logout**: Click the logout button in the sidebar

5. **Test session timeout**: 
   - Wait for `SESSION_TIMEOUT` seconds
   - Try to navigate - should redirect to login

### Debug Mode

Check application logs for authentication issues:
```bash
# Logs will show authentication events
[Auth] User email@example.com authenticated via google
[Auth] User email@example.com logged out
[Auth] Invalid OAuth state token
```

---

## Troubleshooting

### Common Issues

#### 1. "Provider not configured" error

**Problem**: OAuth credentials missing or incorrect

**Solution**: 
- Check `.env` file has correct Client ID and Secret
- Ensure no extra spaces or quotes around values
- Restart the application after changing `.env`

#### 2. "Invalid OAuth state token"

**Problem**: CSRF token mismatch (security check failed)

**Solution**:
- This can happen if you have multiple browser tabs open
- Clear browser cookies and try again
- Ensure `SSO_CALLBACK_URL` matches your OAuth app settings

#### 3. "Login failed. Please try again."

**Problem**: Token exchange or user info fetch failed

**Solution**:
- Check your Client Secret is correct
- Verify the OAuth app is enabled in the provider's console
- Check redirect URI matches exactly (including trailing `/`)
- Review application logs for specific error

#### 4. Redirect doesn't work

**Problem**: Callback URL mismatch

**Solution**:
- Ensure redirect URI in provider settings exactly matches your app URL
- Include trailing slash: `http://localhost:8501/`
- For production, use HTTPS: `https://yourdomain.com/`

#### 5. "User info fetch error"

**Problem**: Missing API permissions

**Solution**:
- **Google**: Enable Google+ API
- **Microsoft**: Add User.Read, email, profile, openid permissions
- **GitHub**: Ensure `user:email` scope is included

#### 6. Session expires too quickly

**Problem**: Default 1-hour timeout

**Solution**: Increase `SESSION_TIMEOUT` in `.env`:
```bash
SESSION_TIMEOUT=7200  # 2 hours
```

---

## Security Best Practices

1. **Never commit secrets**: Add `.env` to `.gitignore`
2. **Use HTTPS in production**: HTTP is only for local development
3. **Rotate secrets regularly**: Update Client Secrets periodically
4. **Limit redirect URIs**: Only add URLs you control
5. **Monitor access**: Review user login logs regularly
6. **Set appropriate session timeout**: Balance security and UX

---

## Support

For issues or questions:
- Check logs for specific error messages
- Review provider's OAuth documentation
- Open an issue on GitHub

---

## Next Steps

Once SSO is configured:
- ✅ Users must authenticate to access the app
- ✅ User profiles are stored in the database
- ✅ Activity can be tracked per user
- ✅ You can add role-based access control (RBAC) in the future

Happy onboarding! 🚀
