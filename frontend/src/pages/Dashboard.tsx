/**
 * Multi-Platform Dashboard with Sidebar, Platform Cards, and Feed Filter
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../hooks/useWebSocket';
import { authAPI } from '../services/api';
import TweetCard from '../components/TweetCard';
import MetricsPanel from '../components/MetricsPanel';
import ThemeToggle from '../components/ThemeToggle';
import Sidebar from '../components/Sidebar';
import PlatformCards from '../components/PlatformCards';
import './Dashboard.css';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
    const { isConnected, events, latestEvent, error } = useWebSocket();
    const username = localStorage.getItem('twitter_username') || 'User';
    const userId = localStorage.getItem('twitter_user_id');
    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const [platformFilter, setPlatformFilter] = useState<string>('all');
    const [activeView, setActiveView] = useState<'feed' | 'platforms'>('feed');

    const handleLogout = async () => {
        setIsLoggingOut(true);

        try {
            if (userId) {
                await authAPI.logout(userId);
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            localStorage.removeItem('twitter_access_token');
            localStorage.removeItem('twitter_user_id');
            localStorage.removeItem('twitter_username');
            navigate('/');
        }
    };

    return (
        <div className="dashboard">
            {/* Sidebar with Hamburger Menu */}
            <Sidebar currentPage={activeView} />

            <header className="dashboard-header">
                <div className="header-content container">
                    <div className="header-left">
                        <h1 className="dashboard-title">
                            CyberGuard
                        </h1>
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
                {/* View Toggle */}
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
                        <PlatformCards />
                    </section>
                )}

                {/* Moderation Feed */}
                {activeView === 'feed' && (
                    <section className="feed-section">
                        <div className="feed-header">
                            <h2 className="section-title">Moderation Feed</h2>

                            {/* Platform Filter */}
                            <select
                                className="platform-filter"
                                value={platformFilter}
                                onChange={(e) => setPlatformFilter(e.target.value)}
                            >
                                <option value="all">🌐 All Platforms</option>
                                <option value="twitter">𝕏 Twitter</option>
                                <option value="discord">💬 Discord</option>
                                <option value="reddit">🔴 Reddit</option>
                            </select>
                        </div>

                        <AnimatePresence mode="popLayout">
                            {events.filter(e => platformFilter === 'all' || e.platform === platformFilter || (platformFilter === 'twitter' && !e.platform)).length === 0 ? (
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
                                    {events
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
            </main>
        </div>
    );
};

export default Dashboard;
