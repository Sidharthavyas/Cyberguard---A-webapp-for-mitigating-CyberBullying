---
title: CyberGuard API
emoji: 🛡️
colorFrom: red
colorTo: orange
sdk: docker
app_file: main.py
pinned: false
license: mit
---

# 🛡️ CyberGuard - Cyberbullying Mitigation API

Real-time Twitter toxicity detection and auto-moderation with 99.87% accuracy.

## Features

- 🤖 **ML-Powered Moderation** - Fine-tuned MuRIL model with 99.87% accuracy
- 🌍 **Multilingual Support** - English, Hindi, Telugu, Tamil, and more
- 🔄 **Real-Time Monitoring** - Background Twitter API polling
- ⚡ **WebSocket Streaming** - Live moderation events
- 🎯 **Auto-Moderation** - Automatic flagging and deletion based on thresholds
- 🔐 **Twitter OAuth** - Full authentication flow

## API Endpoints

### Health & Status
- `GET /` - API info
- `GET /health` - Health check with metrics
- `GET /stats` - Current moderation statistics

### Authentication
- `GET /auth/login` - Initiate Twitter OAuth
- `GET /auth/callback` - OAuth callback
- `GET /auth/me` - Get current user

### WebSocket
- `ws://your-space.hf.space/ws` - Real-time event stream

## Technology Stack

- **Backend**: FastAPI + Python 3.11
- **ML Model**: `Sidhartha2004/finetuned_cyberbullying_muril`
- **Twitter API**: v2 with OAuth 2.0
- **Database**: Upstash Redis (in-memory)
- **AI Fallback**: Google Gemini 2.0 Flash

## Model Performance

| Metric | Score |
|--------|-------|
| Accuracy | 99.87% |
| F1 Score | 99.88% |
| Precision | 99.93% |
| Recall | 99.84% |

## Setup

### Required Secrets

Add these in Space Settings → Variables and secrets:

- `HF_TOKEN` - Hugging Face token
- `GEMINI_API_KEY` - Google Gemini API key
- `TWITTER_CLIENT_ID` - Twitter OAuth client ID
- `TWITTER_CLIENT_SECRET` - Twitter OAuth secret
- `TWITTER_BEARER_TOKEN` - Twitter API bearer token
- `TWITTER_CONSUMER_KEY` - Twitter consumer key
- `TWITTER_CONSUMER_SECRET` - Twitter consumer secret
- `TWITTER_ACCESS_TOKEN` - Twitter access token
- `TWITTER_ACCESS_TOKEN_SECRET` - Twitter access token secret
- `UPSTASH_REDIS_REST_URL` - Upstash Redis REST URL
- `UPSTASH_REDIS_REST_TOKEN` - Upstash Redis token
- `REDIS_URL` - Full Redis connection URL
- `FRONTEND_URL` - Your frontend URL (for CORS)

## Frontend Integration

React frontend connects via:

```javascript
const API_URL = "https://sidhartha2004-cyberguard.hf.space";
const WS_URL = "wss://sidhartha2004-cyberguard.hf.space/ws";
```

## Links

- 🌐 [Frontend (Vercel)](https://your-frontend.vercel.app)
- 💻 [GitHub Repository](https://github.com/Sidhartha2004/cyberguard)
- 🤗 [ML Model Card](https://huggingface.co/Sidhartha2004/finetuned_cyberbullying_muril)

---

**Built with ❤️ for a safer internet**
