# 🔧 Twitter OAuth 400 Error - Fix Guide

## 🐛 Problem Identified

Your Twitter OAuth is failing with a **400 Bad Request** error because the `redirect_uri` has an **unwanted space character**:

```
❌ WRONG: https://sidhartha2004-cyberguard.hf.space /auth/twitter/callback
                                                    ↑ Space here!

✅ CORRECT: https://sidhartha2004-cyberguard.hf.space/auth/twitter/callback
```

---

## 🎯 Root Cause

The `BACKEND_URL` environment variable in your **Hugging Face Spaces** is likely set with a trailing space or incorrect formatting.

---

## ✅ Solution: Fix Environment Variables

### Step 1: Update Hugging Face Spaces Environment Variable

1. **Go to:** https://huggingface.co/spaces/Sidhartha2004/CyberGuard/settings
2. **Click:** "Variables and secrets" tab
3. **Find:** `BACKEND_URL` variable
4. **Update it to EXACTLY:**
   ```
   https://sidhartha2004-cyberguard.hf.space
   ```
   
> [!CAUTION]
> Make sure there are **NO spaces** before or after the URL!

5. **Click:** "Save"
6. **Wait:** For the Space to rebuild (1-2 minutes)

---

### Step 2: Update Twitter App Callback URLs

You need to register **BOTH** callback URLs in your Twitter Developer Portal:

1. **Go to:** https://developer.twitter.com/en/portal/projects-and-apps
2. **Select your app:** CyberGuard
3. **Click:** "User authentication settings" → "Edit"
4. **In "Callback URI / Redirect URL" section, add BOTH:**

   ```
   https://sidhartha2004-cyberguard.hf.space/auth/twitter/callback
   https://cyberguard-a-webapp-for-mitigating.vercel.app/auth/twitter/callback
   ```

   > [!NOTE]
   > The first URL is for your **Hugging Face backend**
   > The second URL is for your **Vercel frontend** (if you're using frontend OAuth)

5. **Also update "Website URL" to:**
   ```
   https://cyberguard-a-webapp-for-mitigating.vercel.app
   ```

6. **Click:** "Save"

---

### Step 3: Verify Your Configuration

After updating, verify your environment variables are correct:

#### Check Hugging Face Spaces

1. Go to: https://huggingface.co/spaces/Sidhartha2004/CyberGuard
2. Check the logs for startup messages
3. Look for: `"Connected to Upstash Redis"` and `"Background poller started"`

#### Test the OAuth Flow

1. **Open:** https://sidhartha2004-cyberguard.hf.space/auth/twitter/login
2. **You should be redirected to Twitter** without errors
3. **After authorizing,** you should be redirected back to your frontend

---

## 🔍 Additional Checks

### Verify All Environment Variables

Make sure these are set correctly in **Hugging Face Spaces**:

| Variable | Correct Format | Example |
|----------|----------------|---------|
| `BACKEND_URL` | No trailing slash, no spaces | `https://sidhartha2004-cyberguard.hf.space` |
| `FRONTEND_URL` | No trailing slash, no spaces | `https://cyberguard-a-webapp-for-mitigating.vercel.app` |
| `REDIS_URL` | Must start with `rediss://` | `rediss://default:xxxxx@your-redis.upstash.io:6379` |

### Common Mistakes to Avoid

❌ **Don't do this:**
```
BACKEND_URL=https://sidhartha2004-cyberguard.hf.space /auth/twitter/callback
BACKEND_URL=https://sidhartha2004-cyberguard.hf.space/
BACKEND_URL= https://sidhartha2004-cyberguard.hf.space
```

✅ **Do this:**
```
BACKEND_URL=https://sidhartha2004-cyberguard.hf.space
```

---

## 🧪 Testing After Fix

### Test 1: Health Check
```bash
curl https://sidhartha2004-cyberguard.hf.space/health
```

Expected response:
```json
{
  "status": "healthy",
  "redis": "connected",
  "models": "loaded"
}
```

### Test 2: OAuth Login
1. Open: https://sidhartha2004-cyberguard.hf.space/auth/twitter/login
2. Should redirect to Twitter authorization page
3. After authorizing, should redirect to your frontend with tokens

### Test 3: Check Logs
1. Go to: https://huggingface.co/spaces/Sidhartha2004/CyberGuard
2. Click "Logs" tab
3. Look for any errors related to OAuth or Redis

---

## 📋 Twitter App Settings Checklist

Make sure your Twitter app has these settings:

- [x] **App permissions:** Read and write
- [x] **Type of App:** Web App, Automated App or Bot (Confidential client)
- [x] **Callback URI:** Both HF and Vercel URLs added
- [x] **Website URL:** Your Vercel frontend URL
- [x] **OAuth 2.0 is enabled**

---

## 🎉 Success Indicators

You'll know it's fixed when:

1. ✅ No 400 error when clicking "Login with Twitter"
2. ✅ Twitter authorization page loads correctly
3. ✅ After authorizing, you're redirected to your dashboard
4. ✅ You can see your tweets and moderation actions work

---

## 🆘 Still Having Issues?

If you still see errors after following these steps:

1. **Check HF Spaces logs** for detailed error messages
2. **Verify Twitter API credentials** are correct
3. **Test with curl** to isolate frontend vs backend issues
4. **Check Redis connection** - many OAuth issues are actually session storage problems

---

## 📝 Quick Fix Summary

1. Fix `BACKEND_URL` in HF Spaces (remove any spaces)
2. Add both callback URLs to Twitter app settings
3. Wait for HF Space to rebuild
4. Test OAuth flow
5. Celebrate! 🎉
