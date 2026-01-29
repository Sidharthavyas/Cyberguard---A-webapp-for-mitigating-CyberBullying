/**
 * Professional Dashboard with clean UI and theme toggle
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../hooks/useWebSocket';
import { authAPI } from '../services/api';
import TweetCard from '../components/TweetCard';
import MetricsPanel from '../components/MetricsPanel';
import ThemeToggle from '../components/ThemeToggle';
import './Dashboard.css';

const Dashboard: React.FC = () => {
    const navigate = useNavigate();
    const { isConnected, events, latestEvent, error } = useWebSocket();
    const username = localStorage.getItem('twitter_username') || 'User';
    const userId = localStorage.getItem('twitter_user_id');
    const [isLoggingOut, setIsLoggingOut] = useState(false);

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
                            <span className="username">@{username}</span>
                        </div>
                        <button
                            className="btn btn-secondary"
                            onClick={handleLogout}
                            disabled={isLoggingOut}
                        >
                            {isLoggingOut ? 'Logging out...' : 'Logout'}
                        </button>
                    </div>
                </div>
            </header>

            <main className="dashboard-main container">
                {error && (
                    <div className="error-banner">
                        <span>⚠</span>
                        <span>{error}</span>
                    </div>
                )}

                <MetricsPanel latestEvent={latestEvent} />

                <div className="tweets-section">
                    <div className="section-header">
                        <div>
                            <h2 className="section-title">Live Feed</h2>
                            <p className="section-subtitle">Real-time content moderation activity</p>
                        </div>
                        {events.length > 0 && (
                            <div className="badge badge-primary">
                                {events.length} events
                            </div>
                        )}
                    </div>

                    <AnimatePresence mode="popLayout">
                        {events.length === 0 ? (
                            <motion.div
                                className="empty-state"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <div className="empty-icon">—</div>
                                <h3>Waiting for activity</h3>
                                <p>Tweets will appear here as they are analyzed in real-time</p>
                            </motion.div>
                        ) : (
                            <div className="tweets-grid">
                                {events.map((event, index) => (
                                    <TweetCard
                                        key={`${event.tweet_id}-${index}`}
                                        tweetId={event.tweet_id}
                                        text={event.text}
                                        language={event.language}
                                        label={event.label}
                                        labelName={event.label_name}
                                        confidence={event.confidence}
                                        bullyingProbability={event.bullying_probability}
                                        deleted={event.deleted}
                                        action={event.action}
                                        timestamp={event.timestamp}
                                    />
                                ))}
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
