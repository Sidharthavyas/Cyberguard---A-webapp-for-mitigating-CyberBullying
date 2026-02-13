/**
 * Platform Cards component - Manage connected platforms
 */

import { useState, useEffect, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import './PlatformCards.css';

interface Platform {
    id: string;
    name: string;
    icon: ReactNode;
    color: string;
    enabled: boolean;
    status: 'active' | 'inactive';
}

const PlatformCards: React.FC = () => {
    const [platforms, setPlatforms] = useState<Platform[]>([
        {
            id: 'twitter',
            name: 'Twitter (X)',
            icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M18.901 2H21.5L15.75 8.52L22.5 18H17.374L13.212 12.38L8.41098 18H5.80998L11.935 11.08L5.5 2H10.749L14.539 7.169L18.901 2ZM17.999 16.4H19.411L10.088 3.5H8.57598L17.999 16.4Z" />
                </svg>
            ),
            color: '#000000',
            enabled: true,
            status: 'active'
        },
        {
            id: 'discord',
            name: 'Discord',
            icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
            ),
            color: '#5865F2',
            enabled: false,
            status: 'inactive'
        }
    ]);

    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        // Fetch connected platforms from API
        fetchPlatforms();
    }, []);

    const fetchPlatforms = async () => {
        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${API_URL}/platforms/connected`);
            const data = await response.json();

            // Update platform states based on API response
            setPlatforms(prev => prev.map(p => ({
                ...p,
                enabled: data.platforms[p.id]?.enabled || false,
                status: data.platforms[p.id]?.status || 'inactive'
            })));
        } catch (error) {
            console.error('Failed to fetch platforms:', error);
        }
    };

    const handleConnect = (platformId: string) => {
        // Redirect to OAuth
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        window.location.href = `${API_URL}/auth/${platformId}/login`;
    };

    const handleDisconnect = async (platformId: string) => {
        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            await fetch(`${API_URL}/platforms/${platformId}`, {
                method: 'DELETE'
            });

            // Refresh platforms
            fetchPlatforms();
        } catch (error) {
            console.error('Failed to disconnect platform:', error);
        }
    };

    return (
        <div className="platform-cards-container">
            <div className="platform-cards-header">
                <h2>Connected Platforms</h2>
                <button
                    className="btn btn-primary btn-sm"
                    onClick={() => setShowModal(true)}
                >
                    + Add Platform
                </button>
            </div>

            <div className="platform-cards-grid">
                {platforms.map((platform) => (
                    <motion.div
                        key={platform.id}
                        className={`platform-card ${platform.enabled ? 'connected' : 'disconnected'}`}
                        whileHover={{ y: -4 }}
                        transition={{ duration: 0.2 }}
                    >
                        <div className="platform-card-header">
                            <div
                                className="platform-card-icon"
                                style={{ color: platform.color }}
                            >
                                {platform.icon}
                            </div>
                            <div className="platform-card-info">
                                <h3>{platform.name}</h3>
                                <span className={`status-badge ${platform.status}`}>
                                    {platform.status === 'active' ? '🟢 Active' : '⚫ Inactive'}
                                </span>
                            </div>
                        </div>

                        <div className="platform-card-actions">
                            {platform.enabled ? (
                                <button
                                    className="btn btn-outline btn-sm"
                                    onClick={() => handleDisconnect(platform.id)}
                                >
                                    Disconnect
                                </button>
                            ) : (
                                <button
                                    className="btn btn-primary btn-sm"
                                    onClick={() => handleConnect(platform.id)}
                                    style={{ background: platform.color, borderColor: platform.color }}
                                >
                                    Connect
                                </button>
                            )}
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Add Platform Modal (simple version) */}
            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <motion.div
                        className="modal-content"
                        onClick={(e) => e.stopPropagation()}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                    >
                        <h3>Add Platform</h3>
                        <p>Select a platform to connect:</p>

                        <div className="modal-platforms">
                            {platforms.filter(p => !p.enabled).map(platform => (
                                <button
                                    key={platform.id}
                                    className="modal-platform-btn"
                                    onClick={() => {
                                        handleConnect(platform.id);
                                        setShowModal(false);
                                    }}
                                    style={{ borderColor: platform.color }}
                                >
                                    <span style={{ color: platform.color }}>{platform.icon}</span>
                                    <span>{platform.name}</span>
                                </button>
                            ))}
                        </div>

                        <button
                            className="btn btn-outline btn-sm"
                            onClick={() => setShowModal(false)}
                        >
                            Cancel
                        </button>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default PlatformCards;
