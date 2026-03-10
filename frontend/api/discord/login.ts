import type { VercelRequest, VercelResponse } from '@vercel/node';

/**
 * Discord OAuth Login - Redirects user to Discord authorization page
 * This runs on Vercel Edge to bypass HuggingFace Spaces DNS restrictions
 */
export default async function handler(req: VercelRequest, res: VercelResponse) {
    const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;
    const FRONTEND_URL = (process.env.VITE_FRONTEND_URL || 'https://cyberguard-a-webapp-for-mitigating.vercel.app').replace(/\/$/, '');

    if (!DISCORD_CLIENT_ID) {
        return res.status(500).json({ error: 'Discord OAuth not configured' });
    }

    // Generate a random state for CSRF protection
    const state = Math.random().toString(36).substring(2, 15) +
        Math.random().toString(36).substring(2, 15);

    // Use a fixed callback URL to guarantee it matches exactly in callback.ts
    // (header-based construction can differ between Vercel serverless invocations)
    const callbackUrl = `${FRONTEND_URL}/api/discord/callback`;

    // Store state in a cookie for verification
    res.setHeader('Set-Cookie', `discord_oauth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`);

    // Build Discord OAuth URL
    const params = new URLSearchParams({
        client_id: DISCORD_CLIENT_ID,
        redirect_uri: callbackUrl,
        response_type: 'code',
        scope: 'identify guilds',
        state: state
    });

    const authUrl = `https://discord.com/api/oauth2/authorize?${params.toString()}`;

    console.log('Discord login - redirect_uri:', callbackUrl);

    // Redirect to Discord
    res.redirect(authUrl);
}
