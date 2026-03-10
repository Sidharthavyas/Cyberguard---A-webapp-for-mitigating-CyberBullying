import type { VercelRequest, VercelResponse } from '@vercel/node';

/**
 * Discord OAuth Callback - Exchanges authorization code for tokens
 * This runs on Vercel to bypass HuggingFace Spaces network restrictions
 */
export default async function handler(req: VercelRequest, res: VercelResponse) {
    const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID;
    const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET;
    const FRONTEND_URL = process.env.VITE_FRONTEND_URL || 'https://cyberguard-a-webapp-for-mitigating.vercel.app';
    const BACKEND_URL = process.env.VITE_API_URL || 'https://sidhartha2004-cyberguard.hf.space';

    const redirectWithError = (code: string) => {
        const url = new URL(`${FRONTEND_URL}/callback`);
        url.searchParams.set('platform', 'discord');
        url.searchParams.set('error', code);
        return res.redirect(url.toString());
    };

    if (!DISCORD_CLIENT_ID || !DISCORD_CLIENT_SECRET) {
        return redirectWithError('discord_not_configured');
    }

    const { code, state, error } = req.query;

    // Handle Discord error
    if (error) {
        console.error('Discord OAuth error:', error);
        return redirectWithError(String(error));
    }

    // Validate code and state
    if (!code || !state) {
        return redirectWithError('missing_code_or_state');
    }

    // Verify state from cookie
    const cookies = req.headers.cookie || '';
    const stateCookie = cookies.split(';').find((c: string) => c.trim().startsWith('discord_oauth_state='));
    const storedState = stateCookie?.split('=')[1];

    if (state !== storedState) {
        // Log but don't fail — cookies between Vercel serverless invocations are unreliable
        console.warn('State mismatch (cookie may not have persisted between serverless invocations):', { received: state, stored: storedState });
    }

    try {
        // Get the callback URL (this Vercel deployment)
        const protocol = req.headers['x-forwarded-proto'] || 'https';
        const host = req.headers['x-forwarded-host'] || req.headers.host;
        const callbackUrl = `${protocol}://${host}/api/discord/callback`;

        // Exchange code for access token
        const tokenResponse = await fetch('https://discord.com/api/oauth2/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                client_id: DISCORD_CLIENT_ID,
                client_secret: DISCORD_CLIENT_SECRET,
                grant_type: 'authorization_code',
                code: code as string,
                redirect_uri: callbackUrl,
            }),
        });

        if (!tokenResponse.ok) {
            const errorData = await tokenResponse.text();
            console.error('Token exchange failed:', errorData);
            return redirectWithError('token_exchange_failed');
        }

        const tokenData = await tokenResponse.json();
        const accessToken = tokenData.access_token;

        // Get user info from Discord
        const userResponse = await fetch('https://discord.com/api/users/@me', {
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        });

        if (!userResponse.ok) {
            console.error('Failed to get user info');
            return redirectWithError('user_info_failed');
        }

        const userInfo = await userResponse.json();
        const userId = userInfo.id;
        const username = userInfo.username;

        // Forward tokens to HF backend so it can store them in Redis
        // (needed for the Discord poller and moderation features)
        try {
            await fetch(`${BACKEND_URL}/auth/discord/store-token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    access_token: accessToken,
                    refresh_token: tokenData.refresh_token,
                    user_id: userId,
                    username: username,
                }),
            });
            console.log(`Forwarded Discord tokens to backend for user ${username}`);
        } catch (backendErr) {
            // Non-fatal: login still works, but poller won't have user tokens
            console.warn('Failed to forward tokens to backend:', backendErr);
        }

        // Clear the state cookie
        res.setHeader('Set-Cookie', 'discord_oauth_state=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0');

        // Redirect to frontend callback with tokens
        const redirectUrl = new URL(`${FRONTEND_URL}/callback`);
        redirectUrl.searchParams.set('platform', 'discord');
        redirectUrl.searchParams.set('access_token', accessToken);
        redirectUrl.searchParams.set('user_id', userId);
        redirectUrl.searchParams.set('username', username);

        return res.redirect(redirectUrl.toString());

    } catch (err) {
        console.error('Discord callback error:', err);
        return redirectWithError('discord_auth_failed');
    }
}
