/**
 * Platform Cards component - Manage connected platforms
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import './PlatformCards.css';

interface Platform {
    id: string;
    name: string;
    icon: string;
    color: string;
    enabled: boolean;
    status: 'active' | 'inactive';
}

const PlatformCards: React.FC = () => {
    const [platforms, setPlatforms] = useState<Platform[]>([
        { id: 'twitter', name: 'Twitter', icon: '𝕏', color: '#1DA1F2', enabled: true, status: 'active' },
        { id: 'discord', name: 'Discord', icon: '💬', color: '#5865F2', enabled: false, status: 'inactive' },
        { id: 'reddit', name: 'Reddit', icon: '🔴', color: '#FF4500', enabled: false, status: 'inactive' }
    ]);

    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        // Fetch connected platforms from API
        fetchPlatforms();
    }, []);

    const fetchPlatforms = async () => {
        try {
            const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${BACKEND_URL}/platforms/connected`);
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
        const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
        window.location.href = `${BACKEND_URL}/auth/${platformId}/login`;
    };

    const handleDisconnect = async (platformId: string) => {
        try {
            const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
            await fetch(`${BACKEND_URL}/platforms/${platformId}`, {
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
