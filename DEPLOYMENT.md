# Deployment Guide 🚀

Complete step-by-step guide to deploy the Cyberbullying Mitigation System to free-tier production.

## Prerequisites Checklist

Before deploying, ensure you have:

- [ ] Twitter Developer Account with OAuth 2.0 app
- [ ] Upstash Redis account with database created
- [ ] Render account
- [ ] Vercel account
- [ ] GitHub repository (optional, but recommended)

---

## Part 1: Twitter API Configuration

### 1.1 Create Twitter App

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new **Project** (if you don't have one)
3. Under the project, create a new **App**
4. Name your app (e.g., "Cyberbullying Monitor")

### 1.2 Configure OAuth 2.0

1. Click on your app
2. Go to "⚙️ Settings"
3. Scroll to "User authentication settings"
4. Click "Set up"
5. Configure:
   - **App permissions**: Read and Write
   - **Type of App**: Web App
   - **Callback URI**: `https://YOUR_BACKEND_URL.onrender.com/auth/twitter/callback`
     - For local dev: `http://localhost:8000/auth/twitter/callback`
   - **Website URL**: `https://YOUR_FRONTEND_URL.vercel.app`
   - **Scopes**: `tweet.read`, `tweet.write`, `users.read`, `offline.access`
6. Save and copy your:
   - **Client ID**
   - **Client Secret**

### 1.3 Get Bearer Token

1. In your app settings, go to "Keys and tokens"
2. Under "Authentication Tokens", click "Generate"
3. Copy the **Bearer Token**
4. Save these credentials securely!

---

## Part 2: Upstash Redis Setup

### 2.1 Create Redis Database

1. Go to [Upstash Console](https://console.upstash.com/)
2. Click "Create Database"
3. Configure:
   - **Name**: cyberbullying-tokens
   - **Type**: Regional
   - **Region**: Choose closest to your Render region
   - **TLS**: Enabled
4. Click "Create"

### 2.2 Get Connection URL

1. Open your database
2. Copy the **REST URL** from the dashboard
3. Format will be: `redis://default:PASSWORD@ENDPOINT.upstash.io:PORT`
4. Save this URL

---

## Part 3: Deploy Backend to Render

### 3.1 Create Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +"
3. Select "Web Service"
4. Connect your GitHub repository or use "Public Git repository"
5. Configure:
   - **Name**: `cyberbullying-backend`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### 3.2 Add Environment Variables

In "Environment" section, add:

```
TWITTER_CLIENT_ID=<your_client_id>
TWITTER_CLIENT_SECRET=<your_client_secret>
TWITTER_BEARER_TOKEN=<your_bearer_token>
REDIS_URL=<your_upstash_redis_url>
FRONTEND_URL=https://<your-vercel-app>.vercel.app
BACKEND_URL=https://<your-render-app>.onrender.com
DELETE_THRESHOLD=4
FLAG_THRESHOLD=3
POLL_INTERVAL=25
```

**Important:** Replace `<your-vercel-app>` with your actual Vercel URL (you'll get this in Part 4)

### 3.3 Deploy

1. Click "Create Web Service"
2. Wait for deployment (may take 5-10 minutes on first deploy due to model download)
3. Copy your backend URL: `https://your-app.onrender.com`

### 3.4 Create Background Worker

1. In Render, click "New +" again
2. Select "Background Worker"
3. Connect same repository
4. Configure:
   - **Name**: `twitter-poller`
   - **Region**: Same as web service
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python poller.py`
   - **Plan**: Free
5. Add the same environment variables as web service
6. Create worker

---

## Part 4: Deploy Frontend to Vercel

### 4.1 Deploy via CLI

```bash
cd frontend
npm install -g vercel
vercel login
vercel
```

Follow prompts:
- **Set up and deploy**: Yes
- **Project name**: cyberbullying-frontend
- **Directory**: ./
- **Build settings**: Auto-detected (Vite)

### 4.2 Configure Environment Variables

In Vercel dashboard:

1. Go to your project
2. Click "Settings" → "Environment Variables"
3. Add:

```
VITE_API_URL=https://your-backend.onrender.com
VITE_WS_URL=wss://your-backend.onrender.com/ws
```

4. Click "Add" for each
5. Redeploy: Go to "Deployments" → Click "..." → "Redeploy"

### 4.3 Alternative: Deploy via GitHub

1. Push your code to GitHub
2. Go to [Vercel Dashboard](https://vercel.com/new)
3. Import your repository
4. Vercel auto-detects Vite
5. Add environment variables (same as above)
6. Deploy

---

## Part 5: Final Configuration

### 5.1 Update Twitter OAuth Callback

Now that you have both URLs:

1. Go back to Twitter Developer Portal
2. Open your app → Settings → User authentication settings
3. Update **Callback URI** to: `https://your-backend.onrender.com/auth/twitter/callback`
4. Update **Website URL** to: `https://your-frontend.vercel.app`
5. Save

### 5.2 Update Backend Environment Variables

In Render:

1. Go to your web service
2. Click "Environment"
3. Update `FRONTEND_URL` to your Vercel URL
4. Click "Save Changes"
5. Render will auto-redeploy

### 5.3 Test the System

1. Open your Vercel URL: `https://your-app.vercel.app`
2. Click "Login with Twitter"
3. Authorize the app
4. You should be redirected to the dashboard
5. Check WebSocket connection status (should show "Live")

---

## Part 6: Verification

### 6.1 Test Backend Health

```bash
curl https://your-backend.onrender.com/health
```

Should return:
```json
{
  "status": "healthy",
  "active_websocket_connections": 0,
  "metrics": { ... }
}
```

### 6.2 Test WebSocket Connection

Open browser console on your dashboard:
- Look for: `✓ WebSocket connected`
- Check Network tab → WS → should show active connection

### 6.3 Test Tweet Processing

1. Tweet or reply to your Twitter account
2. Wait 25-30 seconds (polling interval)
3. Check dashboard for new tweet appearance
4. Verify color coding matches severity level

---

## Troubleshooting

### Backend Issues

**Issue**: Models not loading / 500 error on startup

**Solution**:
- Render free tier may timeout during first model download
- Refresh the page after 2-3 minutes
- Models are cached after first successful load

**Issue**: Background worker not running

**Solution**:
- Check worker logs in Render dashboard
- Ensure all environment variables are set
- Verify Twitter API credentials

### Frontend Issues

**Issue**: Can't connect to backend / CORS error

**Solution**:
- Verify `VITE_API_URL` is correct
- Check backend `FRONTEND_URL` includes your Vercel URL
- Redeploy both services after updating env vars

**Issue**: WebSocket won't connect

**Solution**:
- Ensure `VITE_WS_URL` uses `wss://` (not `ws://`) for production
- Check browser console for connection errors
- Verify backend WebSocket endpoint is accessible

### OAuth Issues

**Issue**: "Callback URL mismatch" error

**Solution**:
- Twitter callback must exactly match: `https://your-backend.onrender.com/auth/twitter/callback`
- No trailing slash
- Use HTTPS in production

**Issue**: "Invalid client" error

**Solution**:
- Double-check Client ID and Client Secret in Render env vars
- Regenerate keys in Twitter Developer Portal if needed

---

## Performance Optimization

### Reduce Cold Starts (Render)

Render free tier spins down after 15 minutes of inactivity.

**Options:**
1. Use a service like [UptimeRobot](https://uptimerobot.com/) (free) to ping your backend every 5 minutes
2. Upgrade to Render paid tier ($7/month for always-on)

### Speed Up Model Loading

1. **First deployment**: Be patient, models download once
2. **Subsequent deploys**: Models are cached, startup is faster
3. **Alternative**: Pre-build Docker image with models (advanced)

---

## Monitoring

### Check Logs

**Render Backend:**
- Dashboard → Your service → "Logs" tab
- Look for model loading messages
- Monitor for errors

**Render Worker:**
- Dashboard → Background worker → "Logs"
- Should show polling activity every 25s

**Vercel Frontend:**
- Dashboard → Project → "Logs"
- Check for build errors

### Monitor Usage

**Twitter API:**
- Developer Portal → Usage dashboard
- Watch rate limits (Free: 75 req/15min for mentions)

**Upstash Redis:**
- Console → Your database → "Metrics"
- Monitor storage usage (Free: 10MB)

**Render:**
- Dashboard shows build minutes used (Free: 750 hrs/month combined)

**Vercel:**
- Dashboard shows bandwidth usage (Free: 100GB/month)

---

## Scaling Considerations

### When to Upgrade

Consider paid tiers if you need:

- **More tweets**: Upgrade Twitter API to Basic ($100/month)
- **Faster inference**: Rent GPU server or use cloud ML APIs
- **Persistent data**: Add PostgreSQL or MongoDB
- **Always-on**: Upgrade Render plan

### Estimated Costs (if scaling)

| Service | Free Tier | Paid Tier | Monthly Cost |
|---------|-----------|-----------|--------------|
| Render | 750 hrs/month | Starter | $7 |
| Vercel | 100GB bandwidth | Pro | $20 |
| Upstash | 10MB storage | Pay-as-go | ~$5 |
| Twitter | 75 req/15min | Basic | $100 |
| **Total** | **$0** | - | **$132+** |

**Current system is free!**

---

## Maintenance

### Regular Tasks

1. **Monitor logs** weekly for errors
2. **Check Twitter API usage** to avoid rate limits
3. **Update dependencies** monthly:
   ```bash
   pip install --upgrade -r requirements.txt
   npm update
   ```

### Update Deployment

**Backend:**
```bash
git push origin main
# Render auto-deploys on push
```

**Frontend:**
```bash
git push origin main
# Vercel auto-deploys on push
```

Or manual:
```bash
cd frontend
vercel --prod
```

---

## Security Checklist

- [ ] All API keys in environment variables (not in code)
- [ ] `.env` files in `.gitignore`
- [ ] HTTPS enabled (automatic on Vercel/Render)
- [ ] CORS configured correctly
- [ ] OAuth redirect URIs exact match
- [ ] Redis password strong and unique
- [ ] Regular dependency updates

---

## Support

If you encounter issues:

1. Check logs in Render/Vercel
2. Review this guide from the beginning
3. Search GitHub issues
4. Open a new issue with:
   - Error messages
   - Logs
   - Steps to reproduce

---

**Congratulations! 🎉**

Your cyberbullying mitigation system is now live and completely free!

Access your app at: `https://your-app.vercel.app`
