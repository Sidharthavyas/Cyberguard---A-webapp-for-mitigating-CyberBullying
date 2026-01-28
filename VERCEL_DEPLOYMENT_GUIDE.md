# 🚀 Frontend Deployment to Vercel

Complete guide to deploy your CyberGuard React frontend to Vercel.

## 📋 Prerequisites

- ✅ Backend deployed to HF Spaces
- ✅ Vercel account (sign up at https://vercel.com)
- ✅ Frontend environment updated with backend URLs
- ✅ Git repository (optional but recommended)

---

## \u003c🔧 Method 1: Vercel CLI (Quickest)

### Step 1: Install Vercel CLI

```powershell
npm install -g vercel
```

### Step 2: Login to Vercel

```powershell
vercel login
```

Follow the browser login flow.

### Step 3: Deploy

```powershell
cd "c:\Users\Sidhartha Vyas\Desktop\CM\frontend"
vercel --prod
```

Answer the prompts:
- **Set up and deploy?** → Y
- **Which scope?** → Your account
- **Link to existing project?** → N
- **Project name?** → cyberguard-frontend (or your choice)
- **Directory?** → `./` (current directory)
- **Override settings?** → N

Wait for deployment (1-2 minutes)...

**Done!** Your frontend will be live at: `https://cyberguard-frontend-xxx.vercel.app`

---

## 🌐 Method 2: Vercel Web Dashboard

### Step 1: Push to GitHub (if not already)

```powershell
cd "c:\Users\Sidhartha Vyas\Desktop\CM"

# Initialize git if needed
git init
git add .
git commit -m "Initial commit - CyberGuard app"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/cyberguard.git
git push -u origin main
```

### Step 2: Import to Vercel

1. Go to https://vercel.com/new
2. Click "Import Git Repository"
3. Select your GitHub repository
4. Configure project:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Step 3: Add Environment Variables

In Vercel project settings:
- `VITE_API_URL` = `https://sidhartha2004-cyberguard.hf.space`
- `VITE_WS_URL` = `wss://sidhartha2004-cyberguard.hf.space/ws`

### Step 4: Deploy

Click "Deploy" button.

---

## ✅ Post-Deployment Configuration

### 1. Get Your Vercel URL

After deployment, copy your Vercel URL:
- Format: `https://your-app-name.vercel.app`

### 2. Update Backend CORS

Go to HF Spaces Settings → Variables and secrets:

Add or update:
```
FRONTEND_URL=https://your-app-name.vercel.app
```

**Important**: Restart your HF Space after adding this!

### 3. Update Twitter OAuth Callback

1. Go to: https://developer.twitter.com/en/portal/projects-and-apps
2. Select your app
3. Go to "User authentication settings"  
4. Add callback URL: `https://your-app-name.vercel.app/callback`
5. Save changes

---

## 🧪 Testing Your Deployment

### Test Checklist

- [ ] Homepage loads: `https://your-app.vercel.app`
- [ ] Login page displays correctly
- [ ] Click "Login with Twitter" → redirects to Twitter
- [ ] After Twitter auth → returns to `/callback`
- [ ] Dashboard loads with user info
- [ ] WebSocket connection indicator shows "Connected"
- [ ] Real-time moderation events appear
- [ ] No console errors

### Common Issues

**Issue**: CORS errors
- **Fix**: Ensure `FRONTEND_URL` is set in HF Spaces and backend is restarted

**Issue**: OAuth callback fails
- **Fix**: Verify callback URL in Twitter Developer Portal matches Vercel URL exactly

**Issue**: WebSocket won't connect
- **Fix**: Check `VITE_WS_URL` uses `wss://` (not `ws://`)

**Issue**: 404 on page refresh
- **Fix**: Already fixed with `vercel.json` rewrites

---

## 🔄 Future Updates

After initial deployment, updates are automatic:

**With Vercel CLI:**
```powershell
cd frontend
vercel --prod
```

**With Git Integration:**
Just push to main branch:
```powershell
git add .
git commit -m "Update message"
git push
```
Vercel auto-deploys!

---

## 📊 Quick Reference

| Item | Value |
|------|-------|
| **Frontend (Vercel)** | https://your-app.vercel.app |
| **Backend (HF Spaces)** | https://sidhartha2004-cyberguard.hf.space |
| **Twitter Dev Portal** | https://developer.twitter.com/en/portal |
| **Vercel Dashboard** | https://vercel.com/dashboard |

---

## 🎉 You're All Set!

After completing these steps:
- ✅ Backend running on HF Spaces
- ✅ Frontend deployed on Vercel
- ✅ OAuth configured
- ✅ Real-time moderation active

**Your CyberGuard app is now live! 🚀**
