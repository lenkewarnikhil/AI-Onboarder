# 🔲 GitHub SSO Setup - Simple 5-Minute Guide

The easiest way to add authentication to AI-Onboarder! GitHub OAuth is perfect for developer tools.

## Why GitHub SSO?

- ✅ **Quick Setup** - 5 minutes, no complex configuration
- ✅ **Developer-Friendly** - Your users already have GitHub accounts
- ✅ **Free** - No cost for OAuth apps
- ✅ **Secure** - Industry-standard OAuth 2.0
- ✅ **Simple** - Just Client ID and Secret needed

---

## 📋 Setup Steps

### Step 1: Register OAuth App on GitHub (2 minutes)

1. **Go to GitHub Developer Settings**
   - Visit: https://github.com/settings/developers
   - Or: Click your avatar → Settings → Developer settings → OAuth Apps

2. **Create New OAuth App**
   - Click **"New OAuth App"** button
   
3. **Fill in the Details**
   ```
   Application name:       AI-Onboarder
   Homepage URL:          http://localhost:8501
   Application description: (optional) AI-powered repository onboarding
   Authorization callback URL: http://localhost:8501/
   ```
   ⚠️ **Important**: Include the trailing slash in callback URL: `http://localhost:8501/`

4. **Register Application**
   - Click **"Register application"**

5. **Generate Client Secret**
   - Click **"Generate a new client secret"**
   - Copy both **Client ID** and **Client Secret** immediately
   - ⚠️ Secret is shown only once!

---

### Step 2: Configure AI-Onboarder (1 minute)

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file**
   Open `.env` and add your GitHub credentials:
   ```bash
   # Required for AI features
   GOOGLE_API_KEY=your_gemini_api_key_here
   
   # SSO Configuration
   SSO_CALLBACK_URL=http://localhost:8501
   SESSION_TIMEOUT=3600
   
   # GitHub OAuth
   GITHUB_CLIENT_ID=your_github_client_id_here
   GITHUB_CLIENT_SECRET=your_github_client_secret_here
   ```

3. **Save the file**

---

### Step 3: Install & Run (2 minutes)

1. **Install dependencies** (if not already done)
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the application**
   ```bash
   streamlit run app.py
   ```

3. **Test it!**
   - Open http://localhost:8501
   - You should see a login page
   - Click **"🔲 Sign in with GitHub"**
   - Authorize the app
   - You're in! 🎉

---

## 🎯 What You'll See

### Before Login
```
┌─────────────────────────────────┐
│        🔐 Sign In               │
│  ───────────────────────────    │
│                                 │
│  Sign in with:                  │
│                                 │
│  ┌───────────────────────────┐ │
│  │ 🔲 Sign in with GitHub     │ │
│  └───────────────────────────┘ │
│                                 │
│  🔒 Your data is secure         │
└─────────────────────────────────┘
```

### After Login
- Your name and avatar in the sidebar
- 🚪 Logout button
- Full access to all features

---

## 🔧 Configuration Options

### Change Session Timeout
```bash
SESSION_TIMEOUT=7200  # 2 hours (default is 1 hour)
```

### Production Deployment
When deploying to production:

1. **Update GitHub OAuth App**
   - Go back to https://github.com/settings/developers
   - Click your app
   - Change URLs to your production domain:
     ```
     Homepage URL: https://yourdomain.com
     Callback URL: https://yourdomain.com/
     ```

2. **Update `.env`**
   ```bash
   SSO_CALLBACK_URL=https://yourdomain.com
   ```

---

## 🚪 Disable SSO (Return to Open Access)

To disable authentication and allow open access:

1. **Remove credentials from `.env`**
   ```bash
   # Comment out or delete these lines
   # GITHUB_CLIENT_ID=...
   # GITHUB_CLIENT_SECRET=...
   ```

2. **Restart the app**
   ```bash
   streamlit run app.py
   ```

App will work without login again!

---

## 🐛 Troubleshooting

### "Provider not configured" Error
**Problem**: GitHub credentials not found

**Solution**:
- Check `.env` file exists (not `.env.example`)
- Verify Client ID and Secret are correct
- No extra spaces or quotes around values
- Restart the app after editing `.env`

---

### "Invalid OAuth state token" Error
**Problem**: CSRF security check failed

**Solution**:
- Clear browser cookies/cache
- Close extra tabs
- Try in incognito/private mode
- Restart the app

---

### Login Redirects to Blank Page
**Problem**: Callback URL mismatch

**Solution**:
- Check GitHub OAuth App settings
- Callback URL must be exactly: `http://localhost:8501/`
- Include the trailing slash `/`
- Match `SSO_CALLBACK_URL` in `.env`

---

### "Rate limit exceeded" Error
**Problem**: Too many OAuth requests

**Solution**:
- Wait a few minutes
- GitHub has rate limits (usually 5000/hour for authenticated users)
- Check your GitHub OAuth app isn't being abused

---

## 📊 User Management

View authenticated users in the database:

```python
# Open Python shell
python

# Check users
from lib.database import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT email, name, last_login FROM users")
print(cursor.fetchall())
```

---

## 🔒 Security Notes

1. **Never commit `.env`** - It contains secrets!
   - `.env` is in `.gitignore` by default
   
2. **Rotate secrets regularly**
   - Generate new client secret every 6-12 months
   
3. **Use HTTPS in production**
   - HTTP is only for local development
   
4. **Monitor access**
   - Check database for unexpected logins

---

## ✨ What Users Experience

### First-Time User Flow

1. User visits your AI-Onboarder
2. Sees login page with GitHub button
3. Clicks "Sign in with GitHub"
4. Redirected to GitHub.com
5. Reviews permissions (read profile)
6. Clicks "Authorize application"
7. Redirected back to your app - logged in!
8. Profile shows in sidebar

### Returning User Flow

1. User visits your AI-Onboarder
2. Sees login page
3. Clicks "Sign in with GitHub"
4. Already authorized - instant redirect back
5. Logged in automatically!

---

## 🎉 You're Done!

That's it! Your AI-Onboarder now has secure GitHub authentication in just 3 simple steps.

### What You Have Now:
- ✅ Secure OAuth 2.0 authentication
- ✅ User profiles in database
- ✅ Session management
- ✅ Login tracking
- ✅ Easy logout

### Optional: Add More Providers Later
If you need Google, Microsoft, or Okta later, see [SSO_SETUP.md](SSO_SETUP.md).

---

## 📚 Related Documentation

- [SSO_SETUP.md](SSO_SETUP.md) - Complete guide for all providers
- [QUICK_START_SSO.md](QUICK_START_SSO.md) - Implementation details
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)

---

**Questions?** Check the troubleshooting section above or review the logs when running the app.

Happy authenticating! 🚀
