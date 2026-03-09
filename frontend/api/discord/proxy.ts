import type { VercelRequest, VercelResponse } from '@vercel/node';

/**
 * Discord API Proxy - Forwards Discord API requests from HF Spaces backend.
 * HF Spaces blocks outbound connections to discord.com, so the backend
 * routes API calls through this Vercel serverless function.
 *
 * Usage: POST /api/discord/proxy
 * Body: { method: "GET"|"POST"|..., path: "/api/v10/...", headers: {...}, body?: "..." }
 */
export default async function handler(req: VercelRequest, res: VercelResponse) {
    // Only accept POST (the proxy request itself is always POST)
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    // Simple auth: require a shared secret to prevent abuse
    const PROXY_SECRET = process.env.DISCORD_PROXY_SECRET;
    if (PROXY_SECRET) {
        const authHeader = req.headers['x-proxy-secret'];
        if (authHeader !== PROXY_SECRET) {
            return res.status(403).json({ error: 'Invalid proxy secret' });
        }
    }

    try {
        const { method, path, headers, body } = req.body;

        if (!method || !path) {
            return res.status(400).json({ error: 'Missing method or path' });
        }

        // Ensure path starts with /api
        const apiPath = path.startsWith('/') ? path : `/${path}`;
        const url = `https://discord.com${apiPath}`;

        // Forward the request to Discord
        const fetchOptions: RequestInit = {
            method: method.toUpperCase(),
            headers: {
                'Content-Type': 'application/json',
                ...headers,
            },
        };

        // Only include body for methods that support it
        if (body && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
            fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
        }

        const response = await fetch(url, fetchOptions);

        // Get response body
        const responseText = await response.text();
        let responseData;
        try {
            responseData = JSON.parse(responseText);
        } catch {
            responseData = responseText;
        }

        // Forward Discord's status code and headers
        // Forward rate limit headers so the client can handle them
        const rateLimitHeaders = [
            'x-ratelimit-limit',
            'x-ratelimit-remaining',
            'x-ratelimit-reset',
            'x-ratelimit-reset-after',
            'x-ratelimit-bucket',
            'retry-after',
        ];

        for (const header of rateLimitHeaders) {
            const value = response.headers.get(header);
            if (value) {
                res.setHeader(header, value);
            }
        }

        return res.status(response.status).json(responseData);

    } catch (err) {
        console.error('Discord proxy error:', err);
        return res.status(502).json({
            error: 'Proxy error',
            message: err instanceof Error ? err.message : 'Unknown error',
        });
    }
}
