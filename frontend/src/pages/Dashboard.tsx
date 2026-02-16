/**
 * Multi-Platform Dashboard with Sidebar, Platform Cards, and Feed Filter
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../hooks/useWebSocket';
import { authAPI, historyAPI } from '../services/api';
import TweetCard from '../components/TweetCard';
import MetricsPanel from '../components/MetricsPanel';
import ThemeToggle from '../components/ThemeToggle';
import Sidebar from '../components/Sidebar';
import PlatformCards from '../components/PlatformCards';
import AnalyticsPanel from '../components/AnalyticsPanel';
import SettingsPanel from '../components/SettingsPanel';
import './Dashboard.css';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
    const { isConnected, events, latestEvent, error } = useWebSocket();
    const username = localStorage.getItem('twitter_username') || localStorage.getItem('discord_username') || 'User';
    const userId = localStorage.getItem('twitter_user_id') || localStorage.getItem('discord_user_id');
    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const [platformFilter, setPlatformFilter] = useState<string>('all');
    const [activeView, setActiveView] = useState<'feed' | 'platforms' | 'analytics' | 'settings'>('feed');
    const [pollerStatus, setPollerStatus] = useState<string>("Initializing...");
    const [historicalEvents, setHistoricalEvents] = useState<any[]>([]);

    // Load historical events from MongoDB on mount
    useEffect(() => {
        const loadHistory = async () => {
            try {
                const data = await historyAPI.getEvents('all', 100);
                if (data.events && data.events.length > 0) {
                    setHistoricalEvents(data.events);
                }
            } catch (err) {
                console.warn('Could not load history:', err);
            }
        };
        loadHistory();
    }, []);

    // Merge live events with historical (live events take priority, dedup by platform_id)
    const allEvents = (() => {
        const liveIds = new Set(events.map((e: any) => e.tweet_id || e.id));
        const dedupedHistory = historicalEvents.filter(
            (h: any) => !liveIds.has(h.platform_id) && !liveIds.has(h.tweet_id)
        );
        // Map historical events to match TweetCard format
        const mappedHistory = dedupedHistory.map((h: any) => ({
            ...h,
            tweet_id: h.platform_id || h.tweet_id,
            id: h.platform_id || h.id,
        }));
        return [...events, ...mappedHistory];
    })();

    // Update status from events
    // Update status from events
    if (latestEvent && 'type' in latestEvent && latestEvent.type === 'status') {
        const statusEvent = latestEvent as { message: string };
        if (statusEvent.message !== pollerStatus) {
            setPollerStatus(statusEvent.message);
        }
    }

    const handleLogout = async () => {
        setIsLoggingOut(true);

        try {
            if (userId) {
                await authAPI.logout(userId);
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear all platform keys
            localStorage.removeItem('twitter_access_token');
            localStorage.removeItem('twitter_user_id');
            localStorage.removeItem('twitter_username');
            localStorage.removeItem('discord_access_token');
            localStorage.removeItem('discord_user_id');
            localStorage.removeItem('discord_username');
            navigate('/');
        }
    };

    return (
        <div className="dashboard">
            {/* Sidebar with Hamburger Menu */}
            <Sidebar
                currentPage={activeView}
                onNavigate={(pageId) => {
                    setActiveView(pageId as typeof activeView);
                }}
            />

            <header className="dashboard-header">
                <div className="header-content container">
                    <div className="header-left">
                        <h1 className="dashboard-title">
                            CyberGuard
                        </h1>
                        <div className="poller-status" style={{ fontSize: '0.8rem', color: '#888', marginLeft: '1rem' }}>
                            {pollerStatus && <span>🔄 {pollerStatus}</span>}
                        </div>
                        <div className="connection-status">
                            <span className={`status-dot status-${isConnected ? 'success' : 'warning'}`}></span>
                            <span className="status-text">
                                {isConnected ? 'Live' : 'Connecting...'}
                            </span>
                        </div>
                    </div>

                    <div className="header-right">
                        <ThemeToggle />
                        <div className="user-info">
                            <div className="user-avatar">
                                {username.charAt(0).toUpperCase()}
                            </div>
                            <div className="user-details">
                                <div className="user-name">@{username}</div>
                            </div>
                        </div>
                        <button
                            className="btn btn-outline logout-btn"
                            onClick={handleLogout}
                            disabled={isLoggingOut}
                        >
                            {isLoggingOut ? 'Logging out...' : 'Logout'}
                        </button>
                    </div>
                </div>
            </header>

            <main className="dashboard-main container">
                {/* View Toggle (for primary views) */}
                {(activeView === 'feed' || activeView === 'platforms') && (
                    <div className="view-toggle">
                        <button
                            className={`view-btn ${activeView === 'feed' ? 'active' : ''}`}
                            onClick={() => setActiveView('feed')}
                        >
                            📊 Feed
                        </button>
                        <button
                            className={`view-btn ${activeView === 'platforms' ? 'active' : ''}`}
                            onClick={() => setActiveView('platforms')}
                        >
                            🔗 Platforms
                        </button>
                    </div>
                )}

                {/* Error Banner */}
                {error && (
                    <div className="error-banner">
                        <span>⚠️</span>
                        <span>{error}</span>
                    </div>
                )}

                {/* Metrics Panel */}
                <section className="metrics-section">
                    <MetricsPanel latestEvent={latestEvent} />
                </section>

                {/* Platform Cards View */}
                {activeView === 'platforms' && (
                    <section className="platforms-section">
                        <div className="section-header">
                            <div>
                                <h2 className="section-title">Connected Platforms</h2>
                                <p className="section-subtitle">
                                    Control which sources CyberGuard listens to across your ecosystem.
                                </p>
                            </div>
                        </div>
                        <PlatformCards />
                    </section>
                )}

                {/* Moderation Feed */}
                {activeView === 'feed' && (
                    <section className="feed-section">
                        <div className="section-header feed-header">
                            <div>
                                <h2 className="section-title">Live Moderation Feed</h2>
                                <p className="section-subtitle">
                                    See content as it is analyzed in real time across all connected platforms.
                                </p>
                            </div>

                            {/* Platform Filter */}
                            <select
                                className="platform-filter"
                                value={platformFilter}
                                onChange={(e) => setPlatformFilter(e.target.value)}
                            >
                                <option value="all">🌐 All platforms</option>
                                <option value="twitter">𝕏 Twitter</option>
                                <option value="discord">💬 Discord</option>
                            </select>
                        </div>

                        <AnimatePresence mode="popLayout">
                            {allEvents.filter(e => platformFilter === 'all' || e.platform === platformFilter || (platformFilter === 'twitter' && !e.platform)).length === 0 ? (
                                <motion.div
                                    className="empty-state"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                >
                                    <div className="empty-icon">—</div>
                                    <h3>Waiting for activity</h3>
                                    <p>
                                        {platformFilter === 'all'
                                            ? 'Content will appear here as it is analyzed in real-time'
                                            : `No ${platformFilter} activity yet`}
                                    </p>
                                </motion.div>
                            ) : (
                                <div className="feed-grid">
                                    {allEvents
                                        .filter(e => platformFilter === 'all' || e.platform === platformFilter || (platformFilter === 'twitter' && !e.platform))
                                        .map((event, index) => (
                                            <TweetCard
                                                key={event.tweet_id || event.id || index}
                                                event={event}
                                                index={index}
                                            />
                                        ))}
                                </div>
                            )}
                        </AnimatePresence>
                    </section>
                )}

                {/* Analytics View */}
                {activeView === 'analytics' && (
                    <section className="analytics-section">
                        <AnalyticsPanel />
                    </section>
                )}

                {/* Settings View */}
                {activeView === 'settings' && (
                    <section className="settings-section">
                        <SettingsPanel />
                    </section>
                )}
            </main>
        </div>
    );
};

export default Dashboard;
