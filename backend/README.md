---
title: CyberGuard API
emoji: "🛡️"
colorFrom: red
colorTo: orange
sdk: docker
app_file: main.py
pinned: false
license: mit
---

# CyberGuard - Cyberbullying Mitigation API

Real-time Twitter toxicity detection and auto-moderation with 99.87% accuracy.

## Features

- ML-Powered Moderation - Fine-tuned MuRIL model with 99.87% accuracy
- Multilingual Support - English, Hindi, Telugu, Tamil, and more
- Real-Time Monitoring - Background Twitter API polling
- WebSocket Streaming - Live moderation events
- Auto-Moderation - Automatic flagging and deletion based on thresholds
- Twitter OAuth - Full authentication flow

## API Endpoints

### Health & Status
- `GET /` - API info
- `GET /health` - Health check with metrics
- `GET /stats` - Current moderation statistics

### Authentication
- `GET /auth/twitter/login` - Initiate Twitter OAuth
- `GET /auth/discord/login` - Initiate Discord OAuth
- `GET /auth/twitter/callback` - OAuth callback
- `GET /auth/discord/callback` - Discord OAuth callback

### WebSocket
- `ws://your-space.hf.space/ws` - Real-time event stream

## Technology Stack

- **Backend**: FastAPI + Python 3.11
- **ML Model**: `Sidhartha2004/finetuned_cyberbullying_muril`
- **Twitter API**: v2 with OAuth 2.0
- **Database**: Upstash Redis (in-memory)
- **AI Fallback**: Google Gemini 2.0 Flash

## Required Secrets

Add these in Space Settings:

- `HF_TOKEN` - Hugging Face token
- `GEMINI_API_KEY` - Google Gemini API key
- `TWITTER_CLIENT_ID` - Twitter OAuth client ID
- `TWITTER_CLIENT_SECRET` - Twitter OAuth secret
- `DISCORD_CLIENT_ID` - Discord OAuth client ID
- `DISCORD_CLIENT_SECRET` - Discord OAuth secret
- `REDIS_URL` - Redis connection URL
- `FRONTEND_URL` - Your frontend URL
- `BACKEND_URL` - This Space URL

---

Built for a safer internet
