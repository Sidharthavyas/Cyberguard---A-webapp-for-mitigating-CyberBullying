/**
 * WebSocket hook for real-time event streaming.
 * Auto-reconnects on disconnect.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface ModerationEvent {
    tweet_id: string;
    text: string;
    language: string;
    label: number;  // 0=safe, 1=bullying
    label_name: string;  // "SAFE" or "BULLYING"
    confidence: number;
    bullying_probability: number;
    deleted: boolean;
    action: string;
    timestamp: string;
    models_agree?: boolean;
    confidence_gap?: number;
    platform?: string;  // Platform name: twitter, discord, reddit
    id?: string;  // Generic ID for non-Twitter platforms
    author?: string;  // Author username
    channel?: string;  // Discord channel or Reddit subreddit
    primary_label?: number;
    secondary_label?: number;
    source?: string;
}

interface ConnectionEvent {
    type: string;
    message: string;
    stats?: any;
    timestamp?: string;
}

type WebSocketMessage = ModerationEvent | ConnectionEvent;

interface UseWebSocketReturn {
    isConnected: boolean;
    events: ModerationEvent[];
    latestEvent: ModerationEvent | null;
    error: string | null;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000; // 3 seconds

export const useWebSocket = (): UseWebSocketReturn => {
    const [isConnected, setIsConnected] = useState(false);
    const [events, setEvents] = useState<ModerationEvent[]>([]);
    const [latestEvent, setLatestEvent] = useState<ModerationEvent | null>(null);
    const [error, setError] = useState<string | null>(null);

    const ws = useRef<WebSocket | null>(null);
    const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
    const shouldReconnect = useRef(true);

    const connect = useCallback(() => {
        try {
            console.log('Connecting to WebSocket...', WS_URL);
            ws.current = new WebSocket(WS_URL);

            ws.current.onopen = () => {
                console.log('✓ WebSocket connected');
                setIsConnected(true);
                setError(null);
            };

            ws.current.onmessage = (event) => {
                try {
                    const data: WebSocketMessage = JSON.parse(event.data);

                    // Handle connection event
                    if ('type' in data && data.type === 'connection') {
                        console.log('Connection established:', data.message);
                        return;
                    }

                    // Handle moderation event
                    const moderationEvent = data as ModerationEvent;
                    console.log('Received moderation event:', moderationEvent);

                    setLatestEvent(moderationEvent);

                    // Add event only if it doesn't already exist (prevent duplicates)
                    setEvents((prev) => {
                        const exists = prev.some(event => event.tweet_id === moderationEvent.tweet_id);
                        if (exists) {
                            console.log('Duplicate event detected, skipping:', moderationEvent.tweet_id);
                            return prev;
                        }
                        return [moderationEvent, ...prev].slice(0, 100); // Keep last 100
                    });
                } catch (err) {
                    console.error('Error parsing WebSocket message:', err);
                }
            };

            ws.current.onerror = (event) => {
                console.error('WebSocket error:', event);
                setError('WebSocket connection error');
            };

            ws.current.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                setIsConnected(false);

                // Attempt reconnection if not manually closed
                if (shouldReconnect.current) {
                    console.log(`Reconnecting in ${RECONNECT_DELAY / 1000}s...`);
                    reconnectTimeout.current = setTimeout(() => {
                        connect();
                    }, RECONNECT_DELAY);
                }
            };
        } catch (err) {
            console.error('Error creating WebSocket:', err);
            setError('Failed to connect to WebSocket');
        }
    }, []);

    const disconnect = useCallback(() => {
        shouldReconnect.current = false;

        if (reconnectTimeout.current) {
            clearTimeout(reconnectTimeout.current);
        }

        if (ws.current) {
            ws.current.close();
            ws.current = null;
        }

        setIsConnected(false);
    }, []);

    useEffect(() => {
        // Connect on mount
        shouldReconnect.current = true;
        connect();

        // Cleanup on unmount
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    return {
        isConnected,
        events,
        latestEvent,
        error
    };
};
