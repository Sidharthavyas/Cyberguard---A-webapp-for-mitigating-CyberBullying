# 🚀 HF Spaces Deployment Guide

Complete guide to deploy your CyberGuard backend to Hugging Face Spaces.

## 📋 Prerequisites

- [x] Hugging Face account and Space created at `Sidhartha2004/CyberGuard`
- [x] HF access token with **write** permissions ([Get one here](https://huggingface.co/settings/tokens))
- [x] Git installed on your system
- [x] All backend files prepared in `backend/` directory

---

## 🔧 Step 1: Clone Your HF Space

Open PowerShell and run:

```powershell
# Navigate to a temporary directory
cd ~\Desktop

# Clone your HF Space repository
git clone https://huggingface.co/spaces/Sidhartha2004/CyberGuard
```

When prompted for password, use your **HF access token** (not your HF password).

---

## 📦 Step 2: Copy Backend Files

Copy all backend files to the HF Space directory:

```powershell
# Copy all backend files to HF Space
cd "c:\Users\Sidhartha Vyas\Desktop\CM"
Copy-Item backend\* ~\Desktop\CyberGuard\ -Recurse -Force

# Verify files were copied
cd ~\Desktop\CyberGuard
ls
```

You should see:
- `Dockerfile`
- `requirements.txt`
- `README.md`
- `main.py`
- `models.py`
- `auth.py`
- `poller.py`
- And all other backend `.py` files

---

## 🚫 Step 3: Clean Up Unnecessary Files

Remove files that shouldn't be deployed:

```powershell
cd ~\Desktop\CyberGuard

# Remove local environment file (we'll use Secrets instead)
Remove-Item .env -ErrorAction SilentlyContinue

# Remove Render-specific files
Remove-Item render.yaml -ErrorAction SilentlyContinue

# Remove test files
Remove-Item test_*.py -ErrorAction SilentlyContinue

# Keep only Python source files and config
```

---

## 🔐 Step 4: Configure Environment Secrets

Before pushing, prepare your environment variables:

1. **Go to:** https://huggingface.co/spaces/Sidhartha2004/CyberGuard/settings
2. **Click:** "Variables and secrets" tab
3. **Add these secrets** (one by one):

| Secret Name | Value (from your local .env) |
|------------|------------------------------|
| `HF_TOKEN` | `hf_xxxxxxxxxxxxxxxxxxxxx` (Get from https://huggingface.co/settings/tokens) |
| `GEMINI_API_KEY` | `AIzaSyxxxxxxxxxxxxxxxxxx` (Get from https://aistudio.google.com/app/apikey) |
| `TWITTER_CLIENT_ID` | Your Twitter OAuth Client ID |
| `TWITTER_CLIENT_SECRET` | Your Twitter OAuth Client Secret |
| `TWITTER_BEARER_TOKEN` | Your Twitter Bearer Token |
| `TWITTER_CONSUMER_KEY` | Your Twitter Consumer Key (API Key) |
| `TWITTER_CONSUMER_SECRET` | Your Twitter Consumer Secret (API Secret) |
| `TWITTER_ACCESS_TOKEN` | Your Twitter Access Token |
| `TWITTER_ACCESS_TOKEN_SECRET` | Your Twitter Access Token Secret |
| `UPSTASH_REDIS_REST_URL` | `https://your-redis.upstash.io` |
| `UPSTASH_REDIS_REST_TOKEN` | Your Upstash Redis REST Token |
| `REDIS_URL` | `rediss://default:xxxxx@your-redis.upstash.io:6379` |
| `FRONTEND_URL` | `https://your-frontend.vercel.app` (update after Vercel deployment) |
| `BACKEND_URL` | `https://your-username-cyberguard.hf.space` |

⚠️ **Important:** Copy exact values from your `backend/.env` file!

---

## 📤 Step 5: Push to HF Spaces

```powershell
cd ~\Desktop\CyberGuard

# Configure git (if needed)
git config user.email "your-email@example.com"
git config user.name "Your Name"

# Add all files
git add .

# Commit changes
git commit -m "Deploy full FastAPI backend with ML moderation"

# Push to HF Spaces (use access token as password)
git push
```

---

## 🔍 Step 6: Monitor Deployment

1. **Go to:** https://huggingface.co/spaces/Sidhartha2004/CyberGuard
2. **Watch the build logs** in real-time
3. **Wait for:** "Running" status (may take 3-5 minutes)

### Expected Build Process:
1. ✅ Building Docker image
2. ✅ Installing Python dependencies
3. ✅ Starting FastAPI server on port 7860
4. ✅ Loading ML models
5. ✅ Initializing background poller

---

## ✅ Step 7: Test Your Deployment

Once the Space shows "Running":

### Test Health Endpoint
```powershell
curl https://sidhartha2004-cyberguard.hf.space/
curl https://sidhartha2004-cyberguard.hf.space/health
```

You should see JSON responses with status information.

### Test in Browser
Open: https://sidhartha2004-cyberguard.hf.space

You should see:
```json
{
  "status": "online",
  "service": "Cyberbullying Mitigation API",
  "version": "1.0.0",
  ...
}
```

---

## 🎨 Step 8: Update Frontend

Update your frontend `.env` to point to the deployed backend:

```env
VITE_API_URL=https://sidhartha2004-cyberguard.hf.space
VITE_WS_URL=wss://sidhartha2004-cyberguard.hf.space/ws
```

Then deploy your frontend to Vercel!

---

## 🐛 Troubleshooting

### Build Failed
- Check build logs for errors
- Verify `requirements.txt` has all dependencies
- Ensure `Dockerfile` uses port 7860

### Runtime Errors
- Check application logs in HF Spaces
- Verify all secrets are added correctly
- Check if ML model downloads successfully

### Model Not Loading
- Verify `HF_TOKEN` secret is set
- Check logs for "Loading ML models..." message
- Ensure enough memory (upgrade hardware if needed)

### Twitter API Errors
- Verify all Twitter secrets are correct
- Check Twitter API rate limits
- Ensure OAuth callback URL is correct

---

## 📊 Quick Reference

| Item | Value |
|------|-------|
| **Space URL** | https://huggingface.co/spaces/Sidhartha2004/CyberGuard |
| **API URL** | https://sidhartha2004-cyberguard.hf.space |
| **WebSocket URL** | wss://sidhartha2004-cyberguard.hf.space/ws |
| **Health Endpoint** | https://sidhartha2004-cyberguard.hf.space/health |
| **Stats Endpoint** | https://sidhartha2004-cyberguard.hf.space/stats |

---

## 🎉 Next Steps

1. ✅ Backend deployed to HF Spaces
2. 📱 Deploy frontend to Vercel
3. 🔗 Update frontend API URLs
4. 🧪 Test entire flow end-to-end
5. 🌐 Share your project!

**Your backend is now live! 🚀**
