---
title: CyberGuard API
emoji: "🛡️"
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
license: mit
---

<div align="center">

# 🛡️ CyberGuard - AI-Powered Cyberbullying Mitigation Platform

### Real-Time Multi-Platform Content Moderation with ML Ensemble & Gemini AI

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-3776AB.svg)](https://python.org)
[![React](https://img.shields.io/badge/react-19.2-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/typescript-5.x-3178C6.svg)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109-009688.svg)](https://fastapi.tiangolo.com)
[![HuggingFace](https://img.shields.io/badge/🤗%20HuggingFace-Spaces-yellow.svg)](https://huggingface.co/spaces)

**Created by Sidhartha Vyas**

[Live Demo](https://cyberguard-a-webapp-for-mitigating.vercel.app) · [Backend API](https://sidhartha2004-cyberguard.hf.space) · [Report Bug](https://github.com/Sidharthavyas/Cyberguard---A-webapp-for-mitigating-CyberBullying/issues)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [ML Models & AI Pipeline](#-ml-models--ai-pipeline)
- [OAuth Authentication Flows](#-oauth-authentication-flows)
- [Content Moderation System](#-content-moderation-system)
- [Real-Time Polling System](#-real-time-polling-system)
- [Redis & Data Storage](#-redis--data-storage)
- [WebSocket Communication](#-websocket-communication)
- [API Reference](#-api-reference)
- [Setup & Installation](#-setup--installation)
- [Deployment](#-deployment)
- [Configuration](#-configuration)
- [Contributing](#-contributing)

---

## 🌟 Overview

CyberGuard is an intelligent cyberbullying detection and mitigation platform that monitors social media platforms (Twitter, Discord) in real-time, analyzes content using advanced ML models, and automatically takes moderation actions on harmful content.

### Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Dual-Model ML Ensemble** | MuRIL (Multilingual) + Toxic-BERT with weighted voting |
| 🧠 **Gemini AI Fallback** | Google's Gemini 2.5 Flash for uncertain classifications |
| 🌐 **Multi-Platform Support** | Twitter & Discord monitoring and moderation |
| ⚡ **Real-Time Processing** | WebSocket-powered live dashboard updates |
| 🎯 **Auto-Moderation** | Configurable delete/flag thresholds |
| 📊 **Live Metrics** | Per-language breakdown with trend analysis |
| 🎨 **Premium UI** | Glassmorphic design with smooth animations |
| 💰 **100% Free Tier** | Runs entirely on free cloud services |

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CYBERGUARD ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌──────────────────────┐                    ┌──────────────────────────────┐   │
│  │    REACT FRONTEND    │                    │      FASTAPI BACKEND         │   │
│  │     (Vercel Free)    │                    │   (HuggingFace Spaces)       │   │
│  │                      │                    │                              │   │
│  │  ┌────────────────┐  │   WebSocket/       │  ┌─────────────────────┐     │   │
│  │  │   Dashboard    │◄─┼───HTTP REST────────┼─►│    Main API Server  │     │   │
│  │  │   Components   │  │      :7860         │  │   (/auth, /stats)   │     │   │
│  │  └────────────────┘  │                    │  └─────────┬───────────┘     │   │
│  │  ┌────────────────┐  │                    │            │                 │   │
│  │  │   Login Page   │  │                    │  ┌─────────▼───────────┐     │   │
│  │  │   (OAuth UI)   │  │                    │  │  Moderation Engine  │     │   │
│  │  └────────────────┘  │                    │  │  (process_tweet)    │     │   │
│  │  ┌────────────────┐  │                    │  └─────────┬───────────┘     │   │
│  │  │  Vercel API    │──┼──Discord OAuth────►│            │                 │   │
│  │  │(Discord OAuth) │  │   (bypasses DNS)   │  ┌─────────▼───────────┐     │   │
│  │  └────────────────┘  │                    │  │    ML Inference     │     │   │
│  └──────────────────────┘                    │  │  ┌───────┬───────┐  │     │   │
│                                              │  │  │ MuRIL │Toxic- │  │     │   │
│                                              │  │  │(Pri.) │BERT   │  │     │   │
│                                              │  │  └───┬───┴───┬───┘  │     │   │
│                                              │  │      │Gemini │      │     │   │
│                                              │  │      │(Fallback)    │     │   │
│                                              │  └──────┴──────────────┘     │   │
│                                              └──────────────────────────────┘   │
│                                                          │                      │
│      ┌───────────────────────────────────────────────────┼──────────────────┐  │
│      │                    EXTERNAL SERVICES              │                  │  │
│      │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────▼─────┐            │  │
│      │  │ Twitter │  │ Discord │  │ Upstash │  │    Google    │            │  │
│      │  │   API   │  │   API   │  │  Redis  │  │  Gemini API  │            │  │
│      │  └─────────┘  └─────────┘  └─────────┘  └──────────────┘            │  │
│      └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```mermaid
flowchart TD
    subgraph Frontend["🖥️ Frontend (Vercel)"]
        UI[Dashboard UI]
        WS[WebSocket Client]
        Login[Login Page]
    end

    subgraph Backend["⚙️ Backend (HuggingFace Spaces)"]
        API[FastAPI Server]
        Poller[Background Poller]
        Mod[Moderation Engine]
        ML[ML Pipeline]
        WSM[WebSocket Manager]
    end

    subgraph MLPipeline["🧠 ML Inference"]
        Primary[MuRIL Model]
        Secondary[Toxic-BERT]
        Gemini[Gemini 2.5 Flash]
    end

    subgraph External["🌐 External APIs"]
        Twitter[Twitter API v2]
        Discord[Discord API]
        Redis[Upstash Redis]
    end

    Login -->|OAuth| API
    API -->|Token| Redis
    Poller -->|Poll Every 25s| Twitter
    Poller -->|Poll Every 120s| Discord
    Twitter -->|Tweets| Mod
    Discord -->|Messages| Mod
    Mod -->|Analyze| ML
    ML --> Primary
    ML --> Secondary
    ML -.->|Fallback| Gemini
    Mod -->|Delete/Flag| Twitter
    Mod -->|Delete| Discord
    Mod -->|Broadcast| WSM
    WSM -->|Real-time| WS
    WS --> UI
```

---

## 🛠️ Tech Stack

### Backend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **FastAPI** | Async web framework | 0.109 |
| **Python** | Core language | 3.11 |
| **PyTorch** | ML inference (CPU) | 2.9.1 |
| **Transformers** | HuggingFace models | 4.57.6 |
| **Tweepy** | Twitter API client | 4.16.0 |
| **discord.py** | Discord API client | 2.3.2 |
| **aiohttp** | Async HTTP client | 3.9.1 |
| **Redis** | Token storage | 5.0.1 |
| **Uvicorn** | ASGI server | 0.27.0 |

### Frontend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **React** | UI library | 19.2 |
| **TypeScript** | Type safety | 5.x |
| **Vite** | Build tool | Latest |
| **React Router** | Client routing | 6.x |
| **Framer Motion** | Animations | Latest |
| **Axios** | HTTP client | Latest |

### Infrastructure (100% Free Tier)

| Service | Purpose | Cost |
|---------|---------|------|
| **HuggingFace Spaces** | Backend hosting (Docker) | Free |
| **Vercel** | Frontend hosting + Serverless | Free |
| **Upstash Redis** | Token storage | Free (10K requests/day) |
| **Twitter API v2** | Social media access | Free (Standard) |
| **Discord API** | Bot integration | Free |
| **Google Gemini** | AI fallback | Free (60 req/min) |

---

## 🧠 ML Models & AI Pipeline

### Model Architecture

CyberGuard uses a sophisticated ensemble approach with intelligent fallback:

```
                    ┌─────────────────────────────────┐
                    │         INPUT TEXT              │
                    │   "You're so stupid, go away"   │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │      LANGUAGE DETECTION       │
                    │     (langdetect library)      │
                    │    Detected: en, hi, te...    │
                    └───────────────┬───────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       │
    ┌───────────────┐       ┌───────────────┐               │
    │  PRIMARY MODEL │       │SECONDARY MODEL│               │
    │    (MuRIL)     │       │ (Toxic-BERT)  │               │
    │  Multilingual  │       │   English     │               │
    │   Threshold:   │       │  Threshold:   │               │
    │     0.4474     │       │    0.6023     │               │
    └───────┬───────┘       └───────┬───────┘               │
            │                       │                       │
            │ Label: 1 (76%)        │ Label: 1 (82%)        │
            │                       │                       │
            └───────────┬───────────┘                       │
                        ▼                                   │
            ┌───────────────────────┐                       │
            │   ENSEMBLE DECISION   │                       │
            │  Weighted Voting +    │                       │
            │  Confidence Analysis  │                       │
            └───────────┬───────────┘                       │
                        │                                   │
            ┌───────────▼───────────┐     Yes              │
            │  Models Disagree OR   ├─────────┐            │
            │  Low Confidence <0.7  │         │            │
            └───────────┬───────────┘         ▼            │
                        │ No          ┌─────────────┐      │
                        │             │ GEMINI 2.5  │      │
                        ▼             │   FLASH     │      │
            ┌───────────────────────┐ │ (Tiebreaker)│      │
            │    FINAL DECISION     │ └──────┬──────┘      │
            │  Label: BULLYING      │        │             │
            │  Confidence: 0.89     │◄───────┘             │
            │  Action: DELETE       │                      │
            └───────────────────────┘                      │
```

### Primary Model: MuRIL (Multilingual)

| Property | Value |
|----------|-------|
| **Model** | `Sidhartha2004/finetuned_cyberbullying_muril` |
| **Base** | Google's MuRIL (Multilingual Representations for Indian Languages) |
| **Languages** | Hindi, Telugu, English, Tamil, Bengali, + more |
| **Optimal Threshold** | 0.4474 (tuned for cyberbullying detection) |
| **Task** | Binary classification (Safe vs Bullying) |

### Secondary Model: Toxic-BERT

| Property | Value |
|----------|-------|
| **Model** | `unitary/toxic-bert` |
| **Base** | BERT fine-tuned on toxic comment dataset |
| **Languages** | Primarily English |
| **Optimal Threshold** | 0.6023 |
| **Task** | Toxicity detection |

### Gemini 2.5 Flash (Fallback)

| Property | Value |
|----------|-------|
| **Model** | `gemini-2.5-flash` |
| **Provider** | Google AI |
| **Purpose** | Tiebreaker when models disagree or have low confidence |
| **Rate Limit** | 60 requests/minute (free tier) |

### Ensemble Logic

```python
def _ensemble_decision(primary_label, primary_conf, secondary_label, secondary_conf):
    """
    1. If both agree with high confidence → Trust them
    2. If models disagree → Weighted voting by confidence
    3. If low overall confidence → Trigger Gemini fallback
    """
    if models_agree and min(primary_conf, secondary_conf) > 0.8:
        return primary_label, average_confidence
    
    if not models_agree:
        weighted_score = (primary_conf * 0.6 + secondary_conf * 0.4)
        return determine_by_weight(weighted_score)
    
    if should_trigger_gemini(confidence, models_agree, confidence_gap):
        return query_gemini_for_tiebreak(text)
```

---

## 🔐 OAuth Authentication Flows

### Twitter OAuth 2.0 (PKCE)

```
┌────────┐                                      ┌────────────┐                   ┌─────────────┐
│  USER  │                                      │  BACKEND   │                   │  TWITTER    │
│        │                                      │ (HF Spaces)│                   │    API      │
└───┬────┘                                      └─────┬──────┘                   └──────┬──────┘
    │                                                 │                                 │
    │ 1. Click "Login with Twitter"                   │                                 │
    ├────────────────────────────────────────────────►│                                 │
    │                                                 │                                 │
    │                2. Generate PKCE verifier + state│                                 │
    │                3. Store in pending_oauth dict   │                                 │
    │                                                 │                                 │
    │ 4. Redirect to Twitter authorize page           │                                 │
    │◄────────────────────────────────────────────────┤                                 │
    │                                                 │                                 │
    ├─────────────────────────────────────────────────┼────────────────────────────────►│
    │                                                 │     5. User authorizes app      │
    │                                                 │                                 │
    │◄────────────────────────────────────────────────┼─────────────────────────────────┤
    │           6. Redirect with ?code=xxx&state=yyy  │                                 │
    │                                                 │                                 │
    ├────────────────────────────────────────────────►│                                 │
    │        7. Callback to /auth/twitter/callback    │                                 │
    │                                                 │                                 │
    │                8. Verify state & pop verifier   │                                 │
    │                                                 │                                 │
    │                                                 │ 9. Exchange code for token      │
    │                                                 ├────────────────────────────────►│
    │                                                 │                                 │
    │                                                 │◄────────────────────────────────┤
    │                                                 │      10. Access + Refresh Token │
    │                                                 │                                 │
    │             11. Store tokens in Redis           │                                 │
    │                                                 │                                 │
    │ 12. Redirect to /callback with tokens           │                                 │
    │◄────────────────────────────────────────────────┤                                 │
    │                                                 │                                 │
    │ 13. Store in localStorage, redirect to dashboard│                                 │
    │                                                 │                                 │
```

### Discord OAuth 2.0 (via Vercel)

> ⚠️ Discord OAuth runs via **Vercel Serverless Functions** to bypass HuggingFace Spaces DNS restrictions for `discord.com`.

```
┌────────┐            ┌────────────┐            ┌───────────┐              ┌──────────┐
│  USER  │            │  VERCEL    │            │  DISCORD  │              │ FRONTEND │
│        │            │   (API)    │            │    API    │              │          │
└───┬────┘            └─────┬──────┘            └─────┬─────┘              └────┬─────┘
    │                       │                         │                         │
    │ 1. Click Discord      │                         │                         │
    ├──────────────────────►│                         │                         │
    │   GET /api/discord/login                        │                         │
    │                       │                         │                         │
    │   2. Generate state   │                         │                         │
    │   3. Set state cookie │                         │                         │
    │                       │                         │                         │
    │◄──────────────────────┤                         │                         │
    │   4. Redirect to Discord                        │                         │
    │                       │                         │                         │
    ├─────────────────────────────────────────────────►                         │
    │                       │      5. User authorizes │                         │
    │◄─────────────────────────────────────────────────                         │
    │   6. Redirect with code                         │                         │
    │                       │                         │                         │
    ├──────────────────────►│                         │                         │
    │   GET /api/discord/callback                     │                         │
    │                       │                         │                         │
    │   7. Verify state cookie                        │                         │
    │                       │                         │                         │
    │                       │  8. Exchange code       │                         │
    │                       ├────────────────────────►│                         │
    │                       │                         │                         │
    │                       │◄────────────────────────┤                         │
    │                       │  9. Access token        │                         │
    │                       │                         │                         │
    │                       │  10. GET /users/@me     │                         │
    │                       ├────────────────────────►│                         │
    │                       │◄────────────────────────┤                         │
    │                       │  11. User info          │                         │
    │                       │                         │                         │
    │◄──────────────────────┤                         │                         │
    │   12. Redirect to /callback?token=...           │────────────────────────►│
    │                       │                         │      13. Store & show   │
    │                       │                         │          dashboard      │
```

---

## 🛡️ Content Moderation System

### Moderation Pipeline

```python
class ModerationEngine:
    """
    Automated moderation based on ML classification results.
    """
    
    async def process_tweet(self, tweet):
        # 1. Run ML inference
        analysis = detector.analyze(tweet["text"])
        
        # 2. Update metrics
        metrics.increment_scanned(analysis["language"])
        
        # 3. Determine action
        if analysis["label"] == 1:  # Bullying detected
            if analysis["confidence"] >= DELETE_CONFIDENCE_THRESHOLD:
                # Delete the content
                deleted = twitter.delete_tweet(tweet["id"])
                metrics.increment_deleted()
            else:
                # Flag for manual review
                metrics.increment_flagged()
        
        # 4. Broadcast via WebSocket
        await manager.broadcast(event)
```

### Moderation Actions

| Classification | Confidence | Action | Result |
|----------------|------------|--------|--------|
| **Safe (Label 0)** | Any | Ignore | ✅ No action |
| **Bullying (Label 1)** | ≥ 0.80 | Delete | 🗑️ Content removed |
| **Bullying (Label 1)** | < 0.80 | Flag | ⚠️ Marked for review |

### Color-Coded Severity

| Label | Color | Description |
|-------|-------|-------------|
| 0 (Safe) | 🟢 Green | Safe content, no action needed |
| 1 (Bullying, low conf) | 🟡 Yellow | Flagged for manual review |
| 1 (Bullying, high conf) | 🔴 Red | Automatically deleted |

---

## 🔄 Real-Time Polling System

### Twitter Polling

```python
# poller.py - Background worker for Twitter monitoring

POLL_INTERVAL = 25  # seconds (respects rate limits)

async def poll_mentions():
    while True:
        # 1. Get mentions (@mentions of the user)
        mentions = twitter.get_recent_mentions(max_results=10)
        
        # 2. Search for replies
        replies = twitter.search_recent_tweets(f"to:{username}", max_results=10)
        
        # 3. Deduplicate and process
        for tweet in new_tweets:
            await moderation_engine.process_tweet(tweet)
        
        # 4. Wait before next poll
        await asyncio.sleep(POLL_INTERVAL)
```

### Discord Polling

```python
# discord_poller.py - Discord server monitoring

class DiscordPoller:
    poll_interval = 120  # 2 minutes
    
    async def _poll_once(self):
        # 1. Fetch recent messages from monitored channels
        messages = await self.client.get_recent_messages(limit=50)
        
        # 2. Process new messages through moderation
        for message in new_messages:
            await self._moderate_message(message)
```

### Rate Limit Handling

| Platform | Endpoint | Rate Limit | CyberGuard Interval |
|----------|----------|------------|---------------------|
| Twitter | Mentions | 75/15min | Every 25s |
| Twitter | Search | 450/15min | Every 25s |
| Discord | Messages | 50/1s | Every 120s |

---

## 💾 Redis & Data Storage

### Upstash Redis Usage

CyberGuard uses **Upstash Redis** (free tier) for:

| Data Type | Key Pattern | TTL | Purpose |
|-----------|-------------|-----|---------|
| OAuth Tokens | `twitter_token:{user_id}` | 30 days | Store access/refresh tokens |
| Discord Tokens | `discord_token:{user_id}` | 30 days | Store Discord credentials |
| User Session | `session:current_user` | 24 hours | Track logged-in user |

### Code Example

```python
# auth.py - Token storage

if redis_client:
    platform_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "username": username,
        "platform": "twitter"
    }
    
    redis_client.setex(
        f"twitter_token:{user_id}",
        30 * 24 * 60 * 60,  # 30 days TTL
        json.dumps(platform_data)
    )
```

### In-Memory Storage

| Data | Location | Persistence |
|------|----------|-------------|
| Metrics (scanned, flagged, deleted) | `metrics.py` | Resets on restart |
| OAuth pending states | `auth.py` (dict) | Cleared after use |
| Processed tweet IDs | `poller.py` (set) | Capped at 1000 IDs |

---

## 📡 WebSocket Communication

### Real-Time Event Broadcasting

```python
# websocket_manager.py

class ConnectionManager:
    async def broadcast(self, message: Dict):
        """Send event to all connected dashboard clients"""
        message["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))
```

### Event Schema

```json
{
    "tweet_id": "1234567890",
    "text": "Sample tweet content",
    "language": "en",
    "label": 1,
    "label_name": "BULLYING",
    "confidence": 0.89,
    "bullying_probability": 0.91,
    "action": "delete",
    "deleted": true,
    "primary_label": 1,
    "secondary_label": 1,
    "models_agree": true,
    "source": "ensemble",
    "platform": "twitter",
    "timestamp": "2026-02-02T12:30:45.123Z"
}
```

---

## 📚 API Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/twitter/login` | Initiate Twitter OAuth |
| GET | `/auth/twitter/callback` | Twitter OAuth callback |
| GET | `/auth/discord/login` | Initiate Discord OAuth |
| GET | `/auth/discord/callback` | Discord OAuth callback |
| POST | `/auth/logout/{user_id}` | Logout and clear tokens |

### Stats Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Get current metrics |
| POST | `/reset-metrics` | Reset all counters |
| GET | `/` | Health check |

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws` | Real-time event stream |

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- Git

### Backend Setup

```bash
# Clone repository
git clone https://github.com/Sidharthavyas/Cyberguard---A-webapp-for-mitigating-CyberBullying.git
cd Cyberguard---A-webapp-for-mitigating-CyberBullying

# Backend setup
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with API URLs
npm run dev
```

### Environment Variables

**Backend (.env):**

```env
# Twitter OAuth
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# Discord OAuth
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret

# Redis (Upstash)
REDIS_URL=redis://default:password@xxx.upstash.io:6379

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# Moderation
DELETE_CONFIDENCE_THRESHOLD=0.8
POLL_INTERVAL=25
```

---

## 🌐 Deployment

### Backend → HuggingFace Spaces

1. Create new Space with **Docker SDK**
2. Connect GitHub repository
3. Add environment variables in Settings
4. Space auto-deploys on push

### Frontend → Vercel

1. Import project from GitHub
2. Root directory: `frontend`
3. Add environment variables:
   - `VITE_API_URL=https://your-space.hf.space`
   - `VITE_WS_URL=wss://your-space.hf.space/ws`
4. Deploy!

### Discord OAuth Setup

1. Add redirect URI: `https://your-app.vercel.app/api/discord/callback`
2. Set Vercel env vars:
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`

---

## ⚙️ Configuration

### Moderation Thresholds

```env
DELETE_CONFIDENCE_THRESHOLD=0.8  # Delete if >= 80% confident
```

### Polling Intervals

```env
POLL_INTERVAL=25  # Twitter: every 25 seconds
# Discord: 120 seconds (hardcoded)
```

### ML Model Thresholds

Tuned for optimal F1-score:

- **MuRIL**: 0.4474
- **Toxic-BERT**: 0.6023

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Sidhartha Vyas**

- GitHub: [@Sidharthavyas](https://github.com/Sidharthavyas)
- HuggingFace: [Sidhartha2004](https://huggingface.co/Sidhartha2004)

---

## 🙏 Acknowledgments

- **HuggingFace** - Model hosting & Spaces
- **Vercel** - Frontend & serverless hosting
- **Upstash** - Free Redis database
- **Google** - Gemini AI API
- **Twitter/X** - API access
- **Discord** - Bot platform

---

<div align="center">

**Built with ❤️ for a safer internet**

🌟 If this helps you, please star the repository!

</div>
