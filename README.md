# Cyberbullying Mitigation System 🛡️

A **100% free-tier** Twitter cyberbullying detection and mitigation system using multilingual AI models, real-time WebSocket streaming, and automated moderation—all without any infrastructure costs.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Cost](https://img.shields.io/badge/cost-FREE-success.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-19.2-blue.svg)

## 🌟 Features

- **🤖 Dual-Model ML Ensemble**: Primary (MuRIL) + Secondary (Toxic-BERT)
- **🌐 Multilingual Support**: Hindi, Telugu, English, and more
- **⚡ Real-time Processing**: WebSocket-powered live updates
- **🎯 Auto-Moderation**: Rule-based deletion (Level ≥4), flagging (Level =3)
- **📊 Live Metrics**: In-memory counters with per-language breakdown
- **🎨 Premium UI**: Glassmorphic design with vibrant colors and smooth animations
- **💰 100% Free**: No database, no GPU, no paid APIs

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  React Frontend │◄──WS────┤  FastAPI Backend │
│   (Vercel Free) │         │  (Render Free)   │
└─────────────────┘         └──────────────────┘
         │                          │
         │                   ┌──────┴──────┐
         │                   │             │
         │                   ▼             ▼
    Twitter OAuth      ML Inference    Twitter API
                       CPU-only        Standard v2
                                       (Free Tier)
```

### Tech Stack

**Backend:**
- FastAPI (Python 3.11)
- Transformers (HuggingFace)
- PyTorch (CPU-only)
- Tweepy (Twitter API v2)
- Upstash Redis (free tier, token storage)
- WebSockets

**Frontend:**
- React 19 + TypeScript
- Vite (build tool)
- React Router
- Axios
- Framer Motion (animations)

**ML Models (Local, Free):**
- Primary: `Sidhartha2004/finetuned_cyberbullying_muril`
- Secondary: `unitary/toxic-bert`

## 📋 Prerequisites

Before you begin, create free accounts for:

1. **Twitter Developer Account** - [Apply here](https://developer.twitter.com/en/portal/dashboard)
   - Create a Project and App
   - Enable OAuth 2.0
   - Get Client ID, Client Secret, and Bearer Token
   
2. **Upstash Redis** - [Sign up](https://upstash.com/)
   - Create a free Redis database
   - Copy the REST URL
   
3. **Render** - [Sign up](https://render.com/)
   - Free tier for backend deployment
   
4. **Vercel** - [Sign up](https://vercel.com/)
   - Free tier for frontend deployment

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/cyberbullying-mitigation.git
cd cyberbullying-mitigation
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Add your Twitter API keys, Upstash Redis URL, etc.
```

**Configure `.env`:**

```env
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
TWITTER_BEARER_TOKEN=your_bearer_token
REDIS_URL=redis://default:password@your-redis.upstash.io:6379
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
DELETE_THRESHOLD=4
FLAG_THRESHOLD=3
POLL_INTERVAL=25
```

**Run backend:**

```bash
# Start API server
python main.py

# In another terminal, start background poller
python poller.py
```

API will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env
# VITE_API_URL=http://localhost:8000
# VITE_WS_URL=ws://localhost:8000/ws

# Run development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 4. Twitter API Setup

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new App under your Project
3. Navigate to "User authentication settings"
4. Enable OAuth 2.0
5. Set Type: "Web App"
6. Set Callback URL: `http://localhost:8000/auth/twitter/callback` (for local dev)
7. Add permissions: `tweet.read`, `tweet.write`, `users.read`, `offline.access`
8. Save your Client ID and Client Secret

## 📦 Deployment

### Deploy Backend to Render

1. Create new "Web Service" on Render
2. Connect your GitHub repository
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.11
   
4. Add environment variables (from your `.env`)

5. Create a "Background Worker" for polling:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python poller.py`
   - Use same environment variables

### Deploy Frontend to Vercel

```bash
cd frontend
vercel
```

Or connect GitHub repository in Vercel dashboard.

**Environment Variables:**
- `VITE_API_URL`: Your Render backend URL (e.g., `https://your-app.onrender.com`)
- `VITE_WS_URL`: Your WebSocket URL (e.g., `wss://your-app.onrender.com/ws`)

**Update Twitter OAuth:**
- Update Callback URL to: `https://your-backend.onrender.com/auth/twitter/callback`

## 🎮 Usage

1. **Open the application** in your browser
2. **Click "Login with Twitter"**
3. **Authorize the app** (OAuth flow)
4. **View the dashboard** with:
   - Live tweet feed (real-time WebSocket updates)
   - Metrics panel (scanned, flagged, deleted counts)
   - Per-language breakdown
5. **Tweets are automatically**:
   - ✓ Ignored (Level 1-2)
   - ⚠️ Flagged (Level 3)
   - 🗑️ Deleted (Level 4-5)

## 🔧 Configuration

### Moderation Thresholds

Edit in `.env`:

```env
DELETE_THRESHOLD=4    # Tweets with level ≥4 are auto-deleted
FLAG_THRESHOLD=3      # Tweets with level =3 are flagged only
```

### Polling Interval

```env
POLL_INTERVAL=25      # Poll Twitter API every 25 seconds
```

### Model Configuration

Models are defined in `backend/models.py`. To use different models:

```python
self.primary_tokenizer = AutoTokenizer.from_pretrained("your-model")
self.primary_model = AutoModelForSequenceClassification.from_pretrained("your-model")
```

## 📊 API Endpoints

### Authentication

- `GET /auth/twitter/login` - Initiate OAuth flow
- `GET /auth/twitter/callback` - OAuth callback
- `POST /auth/logout/{user_id}` - Logout user

### Stats

- `GET /stats` - Get current metrics
- `POST /reset-metrics` - Reset all counters

### WebSocket

- `WS /ws` - Real-time event stream

## 🎨 Color Coding

Tweets are color-coded by severity:

- 🟢 **Level 1-2**: Green (Safe)
- 🟡 **Level 3**: Yellow (Flagged)
- 🔴 **Level 4**: Red (Deleted)
- ⚫ **Level 5**: Black (Severe - Deleted)

## ⚠️ Limitations

**Free Tier Constraints:**

- ❌ No persistent database (metrics reset on restart)
- ❌ CPU-only inference (slower than GPU)
- ❌ Twitter API rate limits (75 req/15min for mentions)
- ❌ Polling instead of streaming (20-30s intervals)
- ❌ Render free tier spins down after inactivity

**Acceptable Trade-offs:**

- ✅ Perfect for proof-of-concept
- ✅ Scales to moderate usage
- ✅ Zero infrastructure costs
- ✅ Easy to upgrade later

## 🔒 Security

- OAuth tokens stored in Upstash Redis (encrypted)
- Environment variables for sensitive data
- CORS protection
- No client-side token storage (except session localStorage)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push and create a Pull Request

## 📄 License

MIT License - feel free to use for personal or commercial projects.

## 🙏 Acknowledgments

- **HuggingFace** for free model hosting
- **Render** for free backend hosting
- **Vercel** for free frontend hosting
- **Upstash** for free Redis
- **Twitter** for free Standard API v2 access

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check the [DEPLOYMENT.md](./DEPLOYMENT.md) guide

---

**Built with ❤️ for a safer internet**

🌟 If this helps you, please  star the repository!
