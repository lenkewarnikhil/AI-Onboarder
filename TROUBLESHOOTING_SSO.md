# 🔧 SSO Error: "Invalid OAuth state token"

## What This Error Means

This is a **security check failure** during OAuth login. The app generates a random "state" token when you click login, and verifies it when GitHub redirects back. If they don't match, the login is rejected for security reasons.

## 🎯 Quick Fixes (Try These First)

### Fix 1: Close Extra Tabs ⭐ **Most Effective**
1. Close ALL other tabs/windows of your AI-Onboarder
2. Keep only ONE tab open
3. Try logging in again

**Why**: Multiple tabs can interfere with session state.

---

### Fix 2: Clear & Retry
1. Click "Try Again" button on the error page
2. Or refresh the page (F5)
3. Try logging in again

**Why**: Clears the old session state.

---

### Fix 3: Clear Browser Cache
1. **Chrome/Edge**: Ctrl+Shift+Delete → Clear cookies
2. **Firefox**: Ctrl+Shift+Delete → Clear cookies
3. Try logging in again

**Why**: Old session cookies can cause conflicts.

---

### Fix 4: Use Incognito/Private Window
1. Open incognito/private browsing window
2. Go to your AI-Onboarder URL
3. Try logging in

**Why**: Fresh session without cached data.

---

### Fix 5: Restart the App
```bash
# Stop the app (Ctrl+C in terminal)
# Start it again
streamlit run app.py
```

**Why**: Clears server-side session state.

---

## 🔍 Why This Happens

### Streamlit Session Limitations
Streamlit's session state can be lost during OAuth redirects because:
- Redirects to external sites (GitHub) and back
- Session data stored in memory (not persistent)
- Multiple tabs share the same session
- Browser security policies

### OAuth Security
The error is **intentional** - it's a security feature called CSRF protection. It prevents attackers from hijacking your login.

---

## ✅ What I Fixed

I've improved the code to:

1. **Embed provider info in state token** - More reliable than session storage
2. **Better error messages** - Shows specific causes and solutions
3. **Fallback mechanisms** - Tries session state as backup
4. **Improved logging** - Shows what went wrong in console

---

## 🧪 Testing the Fix

1. **Restart your app**:
   ```bash
   streamlit run app.py
   ```

2. **Close all tabs except one**

3. **Try login again**:
   - Click "Sign in with GitHub"
   - Authorize on GitHub
   - Should redirect back successfully

---

## 🚨 Still Having Issues?

### Check Your Configuration

1. **Verify callback URL matches** in your GitHub OAuth App:
   ```
   http://localhost:8501/
   ```
   (Must include trailing slash!)

2. **Check .env file**:
   ```bash
   SSO_CALLBACK_URL=http://localhost:8501
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```

3. **No extra spaces** in .env values

### Check Browser Console

1. Press F12 to open DevTools
2. Go to "Console" tab
3. Look for errors during login
4. Share any error messages for debugging

### Check App Logs

The terminal running Streamlit shows detailed logs:
```
[Auth] User attempting login via github
[Auth] Invalid OAuth state token. Expected: github_abc123, Got: github_xyz789
```

---

## 📋 Best Practices

### For Reliable Login:

1. ✅ **Use one tab only** - Don't open multiple tabs
2. ✅ **Complete login in one flow** - Don't interrupt the process
3. ✅ **Enable cookies** - Required for OAuth
4. ✅ **Use modern browser** - Chrome, Firefox, Edge (updated)
5. ✅ **Allow redirects** - Don't block pop-ups

### For Production:

1. Use **HTTPS** (not HTTP)
2. Set **longer session timeout** in .env
3. Use **Redis** or database for session storage (advanced)
4. Monitor logs for failed login attempts

---

## 🔄 Alternative: Disable SSO Temporarily

If you need to access the app urgently:

1. **Edit .env**:
   ```bash
   # Comment out GitHub credentials
   # GITHUB_CLIENT_ID=...
   # GITHUB_CLIENT_SECRET=...
   ```

2. **Restart app**:
   ```bash
   streamlit run app.py
   ```

3. **App will allow open access** without login

4. **Re-enable later** by uncommenting the credentials

---

## 📞 Need More Help?

1. Check the app terminal logs for specific error details
2. Try the fixes above in order
3. Verify your GitHub OAuth App configuration
4. Test in incognito mode to rule out cache issues

The improved code should handle most cases better now. Try restarting the app and logging in with only one tab open! 🚀
