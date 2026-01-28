# 🚀 CyberGuard - Complete Deployment Guide (Single File)

**Deploy your ENTIRE backend to HuggingFace Spaces + Frontend to Vercel in 30 minutes!**

---

## 📋 What You'll Deploy

✅ **Entire FastAPI backend** with all files  
✅ **ML Models** (both MuRIL + Toxic-BERT, 16 GB RAM available!)  
✅ **Gemini AI fallback**  
✅ **WebSocket support** for real-time updates  
✅ **Background worker** for Twitter polling  
✅ **React frontend** on Vercel  
✅ **Redis database** (Upstash free tier)  

**Total Monthly Cost: $0** 🎉

---

## 🎯 Architecture

```
┌─────────────────────────────────────────┐
│  Frontend (Vercel - FREE)               │
│  https://cyberguard.vercel.app          │
└──────────────┬──────────────────────────┘
               │
               │ HTTPS/WSS
               ▼
┌─────────────────────────────────────────┐
│  Backend (HuggingFace Spaces - FREE)    │
│  https://USERNAME-cyberguard.hf.space   │
│                                          │
│  ├── FastAPI (main.py)                  │
│  ├── ML Models (models.py)              │
│  ├── Twitter Poller (poller.py)         │
│  ├── WebSocket Manager                  │
│  └── All other backend files            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Redis (Upstash - FREE)                 │
│  Session & token storage                │
└─────────────────────────────────────────┘
```

**All connected with just ONE URL!** ✅

---

## ⏱️ Time Required

- **Setup**: 10 minutes
- **Backend Deployment**: 15 minutes
- **Frontend Deployment**: 5 minutes
- **Testing**: 5 minutes
- **Total**: ~35 minutes

---

## 📦 Prerequisites (5 minutes)

### 1. Create HuggingFace Account
- Go to https://huggingface.co/join
- Sign up (free)
- Get token: https://huggingface.co/settings/tokens
  - Click "New token"
  - Name: "CyberGuard Deploy"
  - Type: "Write"
  - Copy token (starts with `hf_...`)

### 2. Create Vercel Account
- Go to https://vercel.com/signup
- Sign up with GitHub (recommended)

### 3. Create Upstash Redis
- Go to https://upstash.com/
- Sign up (free)
- Create database:
  - Name: cyberguard
  - Region: Choose closest
  - Copy **Redis URL** (looks like: `redis://default:xxx@xxx.upstash.io:6379`)

### 4. Get Twitter API Keys
- Go to https://developer.twitter.com/en/portal/dashboard
- Create app (if not done)
- Get:
  - Client ID
  - Client Secret
  - Bearer Token

### 5. Get Gemini API Key
- Go to https://aistudio.google.com/app/apikey
- Create API key
- Copy key

---

## 🔧 Part 1: Prepare Backend for HuggingFace Spaces (5 minutes)

### Step 1: Create Dockerfile

Create `Dockerfile` in your `backend` folder:

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY . .

# Expose port 7860 (HuggingFace Spaces default)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:7860/ || exit 1

# Start both FastAPI and background poller
CMD uvicorn main:app --host 0.0.0.0 --port 7860 & python poller.py
```

**Save this file as:** `C:\Users\Sidhartha Vyas\Desktop\CM\backend\Dockerfile`

---

### Step 2: Create Space README

Create `README.md` in your `backend` folder:

```markdown
---
title: CyberGuard API
emoji: 🛡️
colorFrom: red
colorTo: orange
sdk: docker
app_port: 7860
---

# 🛡️ CyberGuard Backend

Full-stack cyberbullying detection API with:
- FastAPI backend
- ML models (99.87% accuracy)
- WebSocket support
- Twitter integration
- Background polling

**Frontend:** Connect via HTTPS and WSS to this backend.
```

**Save this file as:** `C:\Users\Sidhartha Vyas\Desktop\CM\backend\README.md`

---

### Step 3: Update CORS Settings

Open `backend\main.py` and ensure CORS allows HuggingFace domain:

```python
# Add this to your CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "https://*.vercel.app",  # Allow all Vercel domains
        "https://*.hf.space",    # Allow HuggingFace
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🚀 Part 2: Deploy Backend to HuggingFace Spaces (15 minutes)

### Option A: Via Web Interface (Easiest - 10 minutes)

#### 1. Create Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   ```
   Owner: YOUR_USERNAME
   Space name: cyberguard-api
   License: MIT
   Select SDK: Docker
   Space hardware: CPU basic (FREE)
   Visibility: Public
   ```
3. Click **"Create Space"**

#### 2. Upload Backend Files

On the "Files" tab, click "Add file" → "Upload files":

Upload ALL files from `backend` folder:
- ✅ `Dockerfile` (just created)
- ✅ `README.md` (just created)
- ✅ `main.py`
- ✅ `models.py`
- ✅ `poller.py`
- ✅ `auth.py`
- ✅ `twitter_client.py`
- ✅ `moderation.py`
- ✅ `metrics.py`
- ✅ `websocket_manager.py`
- ✅ `cyberbullying_filter.py`
- ✅ `requirements.txt`
- ✅ `.env.example` (optional)
- ✅ Any other Python files

**Drag and drop all files at once!**

#### 3. Configure Environment Variables

Click **"Settings"** tab → **"Repository secrets"** → **"New secret"**

Add these secrets ONE BY ONE:

| Secret Name | Value |
|-------------|-------|
| `TWITTER_CLIENT_ID` | Your Twitter Client ID |
| `TWITTER_CLIENT_SECRET` | Your Twitter Client Secret |
| `TWITTER_BEARER_TOKEN` | Your Twitter Bearer Token |
| `REDIS_URL` | Your Upstash Redis URL |
| `GEMINI_API_KEY` | Your Gemini API key |
| `FRONTEND_URL` | `https://YOUR_APP.vercel.app` (update later) |
| `DELETE_THRESHOLD` | `1` |
| `FLAG_THRESHOLD` | `1` |
| `POLL_INTERVAL` | `30` |

**Important:** Secret values are encrypted and not visible after saving.

#### 4. Wait for Build

- HuggingFace will automatically build your Docker container
- Watch the **"Build logs"** in the app
- Build takes ~10-15 minutes
- You'll see:
  ```
  Building Docker image...
  Installing requirements...
  Loading model Sidhartha2004/finetuned_cyberbullying_muril...
  ✓ Primary model loaded successfully
  ✓ Secondary model loaded successfully
  Running on http://0.0.0.0:7860
  ```

#### 5. Get Your Backend URL

Once deployed, your backend is live at:
```
https://YOUR_USERNAME-cyberguard-api.hf.space
```

**Copy this URL!** You'll need it for frontend deployment.

---

### Option B: Via Git (Advanced - 15 minutes)

#### 1. Install Git LFS (for large files)

```bash
# Download from: https://git-lfs.github.com/
git lfs install
```

#### 2. Clone Space Repository

```bash
cd C:\Users\Sidhartha Vyas\Desktop\CM

# Clone your space
git clone https://huggingface.co/spaces/YOUR_USERNAME/cyberguard-api
cd cyberguard-api
```

#### 3. Copy Backend Files

```bash
# Copy all backend files
xcopy ..\backend\* . /E /H /Y

# Verify Dockerfile exists
dir Dockerfile
```

#### 4. Create .env (for secrets)

HuggingFace Spaces reads from repository secrets, but you can also use `.env`:

```bash
echo TWITTER_CLIENT_ID=your_client_id > .env
echo TWITTER_CLIENT_SECRET=your_secret >> .env
echo TWITTER_BEARER_TOKEN=your_token >> .env
echo REDIS_URL=your_redis_url >> .env
echo GEMINI_API_KEY=your_gemini_key >> .env
echo FRONTEND_URL=https://YOUR_APP.vercel.app >> .env
echo DELETE_THRESHOLD=1 >> .env
echo FLAG_THRESHOLD=1 >> .env
echo POLL_INTERVAL=30 >> .env
```

⚠️ **Don't commit .env file!** Add to `.gitignore`:

```bash
echo .env >> .gitignore
```

Instead, add secrets via Space settings (more secure).

#### 5. Commit and Push

```bash
git add .
git commit -m "Deploy CyberGuard backend"
git push
```

#### 6. Wait for Build

Go to https://huggingface.co/spaces/YOUR_USERNAME/cyberguard-api

Watch build logs in the app interface.

---

## 🎨 Part 3: Deploy Frontend to Vercel (5 minutes)

### Step 1: Update Frontend Environment Variables

Edit `frontend\.env.production`:

```env
# Replace with your HuggingFace Space URL
VITE_API_URL=https://YOUR_USERNAME-cyberguard-api.hf.space
VITE_WS_URL=wss://YOUR_USERNAME-cyberguard-api.hf.space/ws
```

**Example:**
```env
VITE_API_URL=https://sidhartha2004-cyberguard-api.hf.space
VITE_WS_URL=wss://sidhartha2004-cyberguard-api.hf.space/ws
```

---

### Step 2: Deploy to Vercel

#### Option A: Vercel CLI (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to frontend
cd C:\Users\Sidhartha Vyas\Desktop\CM\frontend

# Login
vercel login

# Deploy
vercel

# Follow prompts:
# ? Set up and deploy? Y
# ? Which scope? [Your account]
# ? Link to existing project? N
# ? What's your project's name? cyberguard
# ? In which directory is your code located? ./
# ? Want to override the settings? N

# Production deployment
vercel --prod
```

#### Option B: Vercel Dashboard

1. Go to https://vercel.com/new
2. Import Git Repository:
   - Click "Import Git Repository"
   - Authorize GitHub
   - Select `cyberguard` repo
3. Configure:
   ```
   Framework Preset: Vite
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: dist
   Install Command: npm install
   ```
4. Add Environment Variables:
   - Click "Environment Variables"
   - Add:
     ```
     VITE_API_URL = https://YOUR_USERNAME-cyberguard-api.hf.space
     VITE_WS_URL = wss://YOUR_USERNAME-cyberguard-api.hf.space/ws
     ```
5. Click **"Deploy"**

---

### Step 3: Get Frontend URL

After deployment, Vercel gives you:
```
https://cyberguard.vercel.app
```

Or custom domain:
```
https://YOUR_PROJECT.vercel.app
```

**Copy this URL!**

---

## 🔄 Part 4: Update Backend with Frontend URL (2 minutes)

### Update HuggingFace Space Settings

1. Go to your Space: https://huggingface.co/spaces/YOUR_USERNAME/cyberguard-api
2. Click **"Settings"** → **"Repository secrets"**
3. Find `FRONTEND_URL` secret
4. Update value to: `https://cyberguard.vercel.app`
5. Save

**HuggingFace will auto-redeploy with new settings.**

---

### Update Twitter OAuth Callback

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Select your app → **"User authentication settings"**
3. Update **Callback URL**:
   ```
   https://YOUR_USERNAME-cyberguard-api.hf.space/auth/twitter/callback
   ```
   
   Example:
   ```
   https://sidhartha2004-cyberguard-api.hf.space/auth/twitter/callback
   ```

4. Update **Website URL**:
   ```
   https://cyberguard.vercel.app
   ```

5. **Save**

---

## ✅ Part 5: Test Everything (5 minutes)

### 1. Test Backend API

Open browser and test:

```
https://YOUR_USERNAME-cyberguard-api.hf.space
```

Should show:
```json
{"message": "CyberGuard API is running"}
```

Test stats endpoint:
```
https://YOUR_USERNAME-cyberguard-api.hf.space/stats
```

Should show:
```json
{
  "total_scanned": 0,
  "total_flagged": 0,
  "total_deleted": 0,
  "by_language": {}
}
```

Test API docs:
```
https://YOUR_USERNAME-cyberguard-api.hf.space/docs
```

Should show FastAPI Swagger UI.

---

### 2. Test Frontend

Open:
```
https://cyberguard.vercel.app
```

**Check:**
- ✅ Page loads
- ✅ "Login with Twitter" button works
- ✅ Click → Redirects to Twitter OAuth
- ✅ Authorize → Redirects back to dashboard
- ✅ Dashboard shows metrics
- ✅ WebSocket: Real-time connection indicator shows "Connected"

---

### 3. Test End-to-End Flow

1. **Login** with Twitter
2. **Post a tweet** from your Twitter account (any text)
3. **Wait 30 seconds** (polling interval)
4. **Check dashboard** - new tweet should appear!
5. **Check moderation** - tweet should be classified
6. **Verify action** - flagged or deleted based on content

---

### 4. Test WebSocket

Open browser console (F12) on dashboard:

Should see:
```
WebSocket connected to wss://YOUR_USERNAME-cyberguard-api.hf.space/ws
```

When new tweet arrives:
```
New tweet analyzed: {...}
```

---

## 🎉 Deployment Complete!

### Your Live URLs:

| Service | URL |
|---------|-----|
| **Frontend** | `https://cyberguard.vercel.app` |
| **Backend API** | `https://YOUR_USERNAME-cyberguard-api.hf.space` |
| **API Docs** | `https://YOUR_USERNAME-cyberguard-api.hf.space/docs` |
| **Redis** | `redis://xxx.upstash.io:6379` |

### What's Running:

✅ Full FastAPI backend on HuggingFace (16 GB RAM)  
✅ ML Models loaded (MuRIL + Toxic-BERT)  
✅ Gemini AI fallback  
✅ Background Twitter poller  
✅ WebSocket for real-time updates  
✅ React frontend on Vercel  
✅ Redis session storage on Upstash  

**Total Monthly Cost: $0** 🎊

---

## 📊 Performance & Monitoring

### Expected Performance:

| Metric | Value |
|--------|-------|
| **Backend Cold Start** | 10-15 seconds |
| **Model Load Time** | 30-60 seconds (first request) |
| **API Response** | 200-500ms (warm) |
| **ML Inference** | 1-2 seconds |
| **WebSocket Latency** | <100ms |
| **Uptime** | 99.9% |

### Monitor Your App:

#### 1. HuggingFace Spaces Logs

- Go to your Space
- Click **"Logs"** tab
- See real-time logs:
  ```
  INFO: Model loaded successfully
  INFO: Analyzing tweet: ...
  INFO: WebSocket client connected
  ```

#### 2. Vercel Logs

- Go to https://vercel.com/dashboard
- Select your project
- Click **"Deployments"** → Latest deployment → **"View Logs"**

#### 3. Uptime Monitoring (Optional)

Set up free monitoring with **UptimeRobot**:

1. Sign up: https://uptimerobot.com/
2. Create monitor:
   ```
   Type: HTTP(s)
   Name: CyberGuard API
   URL: https://YOUR_USERNAME-cyberguard-api.hf.space/stats
   Interval: 5 minutes
   ```
3. Get alerts if your app goes down

---

## 🔧 Common Issues & Solutions

### Issue 1: "Application Error" on HuggingFace

**Cause:** Environment variables missing or Docker build failed

**Solution:**
1. Check build logs for errors
2. Verify all secrets are set correctly
3. Check Dockerfile syntax
4. Rebuild: Settings → Factory reboot

---

### Issue 2: CORS Error on Frontend

**Error in browser console:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**

Update `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cyberguard.vercel.app"],  # Your exact Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy backend (commit change to Space).

---

### Issue 3: WebSocket Connection Failed

**Error:** `WebSocket connection to 'wss://...' failed`

**Solution:**

1. Verify WebSocket URL in frontend `.env`:
   ```env
   VITE_WS_URL=wss://YOUR_USERNAME-cyberguard-api.hf.space/ws
   ```
   
2. Check backend WebSocket endpoint is running:
   - Open `https://YOUR_USERNAME-cyberguard-api.hf.space/docs`
   - Look for `/ws` endpoint

3. Test WebSocket manually:
   ```javascript
   // In browser console
   const ws = new WebSocket('wss://YOUR_USERNAME-cyberguard-api.hf.space/ws');
   ws.onopen = () => console.log('Connected!');
   ws.onerror = (e) => console.error('Error:', e);
   ```

---

### Issue 4: Twitter OAuth Redirect Error

**Error:** "OAuth state mismatch" or "Callback URL mismatch"

**Solution:**

1. **Verify callback URL** in Twitter Developer Portal matches EXACTLY:
   ```
   https://YOUR_USERNAME-cyberguard-api.hf.space/auth/twitter/callback
   ```

2. **Check FRONTEND_URL** secret in HF Space:
   - Must be your actual Vercel URL
   - No trailing slash

3. **Clear Redis cache:**
   - Go to Upstash dashboard
   - Data Browser → Flush DB

---

### Issue 5: Model Loading Takes Too Long

**Symptom:** First API request times out

**Solution:**

HuggingFace caches models after first download. Future deploys are faster.

For first deployment:
1. Wait 2-3 minutes after "Running on..." appears in logs
2. Models download in background
3. Check logs for "Model loaded successfully"
4. Then test API

---

### Issue 6: Background Poller Not Working

**Symptom:** No tweets appearing in dashboard

**Solution:**

1. **Check poller is running:**
   - HF Space logs should show:
     ```
     INFO: Starting Twitter poller...
     INFO: Polling for new tweets every 30s
     ```

2. **Verify Twitter API credentials:**
   - Test manually: https://YOUR_USERNAME-cyberguard-api.hf.space/docs
   - Try `/auth/twitter/login` endpoint

3. **Check rate limits:**
   - Twitter free tier: 75 requests per 15 minutes
   - Increase `POLL_INTERVAL` to 60 seconds if hitting limits

---

## 🚀 Advanced: Custom Domain (Optional)

### Add Custom Domain to Vercel:

1. Go to Vercel dashboard → Your project → **Settings** → **Domains**
2. Add your domain (e.g., `cyberguard.com`)
3. Update DNS records as shown (Vercel provides instructions)
4. **Free SSL** included!

### Add Custom Domain to HuggingFace:

HuggingFace Spaces custom domains require **Pro plan** ($9/month).

Alternative: Use free `https://YOUR_USERNAME-cyberguard-api.hf.space` subdomain.

---

## 📈 Scaling (When You Grow)

### When to Upgrade:

| Metric | Free Tier Limit | Upgrade Trigger |
|--------|----------------|-----------------|
| **Concurrent Users** | 10-50 | >50 users |
| **API Requests** | Unlimited | Slow performance |
| **Model Inference** | CPU-only | Need faster responses |
| **Cold Starts** | 10-15s | Want instant responses |

### Upgrade Options:

#### HuggingFace Spaces Pro ($9/month):
- Persistent hardware (no cold starts)
- Custom domains
- More CPU power
- Private spaces

#### Google Cloud Run ($10-20/month):
- GPU support for faster inference
- Auto-scaling
- 99.95% uptime SLA
- Enterprise features

#### Render Starter ($7/month):
- Always-on (no spin-down)
- More RAM (2 GB)
- Faster builds

---

## 🎯 Quick Reference Card

**Copy this for easy access:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CYBERGUARD - DEPLOYMENT INFO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FRONTEND URL:
https://cyberguard.vercel.app

BACKEND URL:
https://YOUR_USERNAME-cyberguard-api.hf.space

API DOCS:
https://YOUR_USERNAME-cyberguard-api.hf.space/docs

TWITTER CALLBACK:
https://YOUR_USERNAME-cyberguard-api.hf.space/auth/twitter/callback

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DASHBOARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HuggingFace Space:
https://huggingface.co/spaces/YOUR_USERNAME/cyberguard-api

Vercel Dashboard:
https://vercel.com/dashboard

Upstash Redis:
https://console.upstash.com/

Twitter Developer:
https://developer.twitter.com/en/portal/dashboard

Gemini API:
https://aistudio.google.com/app/apikey

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 USEFUL COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test backend:
curl https://YOUR_USERNAME-cyberguard-api.hf.space/stats

Redeploy frontend:
cd frontend && vercel --prod

View backend logs:
# Go to HF Space → Logs tab

View frontend logs:
# Go to Vercel → Deployments → Logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎊 Success Checklist

After deployment, verify:

- [ ] Backend responds at `https://YOUR_USERNAME-cyberguard-api.hf.space`
- [ ] API docs accessible at `/docs`
- [ ] Frontend loads at `https://cyberguard.vercel.app`
- [ ] Twitter OAuth login works
- [ ] Dashboard shows after login
- [ ] WebSocket shows "Connected"
- [ ] Posting tweet triggers moderation (~30s delay)
- [ ] Metrics update in dashboard
- [ ] Background poller running (check logs)
- [ ] ML models loaded successfully
- [ ] Redis connection working
- [ ] No CORS errors in browser console
- [ ] Mobile responsive (test on phone)

**All checked?** 🎉 **You're live!**

---

## 💡 Pro Tips

1. **Keep Your Secrets Safe**
   - Never commit `.env` files
   - Use HF Space secrets and Vercel environment variables
   - Rotate API keys regularly

2. **Monitor Your Usage**
   - Check Upstash Redis usage (free tier: 10,000 commands/day)
   - Monitor Twitter API rate limits (75 req/15min)
   - Watch Gemini API usage (1,500 req/day free)

3. **Optimize Performance**
   - Enable caching for repeated tweets
   - Increase `POLL_INTERVAL` to reduce API calls
   - Use Gemini only for low-confidence predictions

4. **Update Regularly**
   - Keep dependencies updated
   - Monitor HuggingFace for model updates
   - Check for security patches

5. **Backup Your Config**
   - Save all environment variables in password manager
   - Document custom changes
   - Keep deployment guide handy

---

## 🤝 Need Help?

**If something doesn't work:**

1. Check this guide's **Common Issues** section
2. Review build logs on HuggingFace
3. Check browser console for errors (F12)
4. Verify all environment variables are set
5. Test each component individually (backend, frontend, Redis)

**Still stuck?**
- Open an issue on GitHub
- Check HuggingFace Spaces documentation
- Ask in Vercel community

---

## 🎉 Congratulations!

You've successfully deployed CyberGuard with:

✅ Full-stack application  
✅ State-of-the-art ML models (99.87% accuracy)  
✅ Real-time WebSocket updates  
✅ Twitter integration  
✅ Professional UI  
✅ **$0 monthly cost!**  

**Share your deployment:**
- Tweet about it with #CyberGuard
- Add to your portfolio
- Demo to potential employers or clients

---

**Built with ❤️ for a safer internet**

🌟 **Next Steps:**
- Customize the UI with your branding
- Add more features (user management, analytics, etc.)
- Scale when you get users
- Share your impact!

**Happy deploying!** 🚀🛡️
