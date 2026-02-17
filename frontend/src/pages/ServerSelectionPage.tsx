/**
 * Server selection page for Discord bot addition
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams, useNavigate } from 'react-router-dom';
import './ServerSelectionPage.css';

interface Guild {
    id: string;
    name: string;
    icon: string | null;
    permissions: number;
}

const ServerSelectionPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [guilds, setGuilds] = useState<Guild[]>([]);
    const [selectedGuilds, setSelectedGuilds] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const userId = searchParams.get('user_id');
    const username = searchParams.get('username');

    useEffect(() => {
        if (!userId) {
            navigate('/login');
            return;
        }

        // Fetch guilds from backend
        const fetchGuilds = async () => {
            try {
                const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const response = await fetch(`${BACKEND_URL}/auth/discord/guilds/${userId}`);
                
                if (!response.ok) {
                    throw new Error('Failed to fetch guilds');
                }

                const data = await response.json();
                setGuilds(data.guilds || []);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load servers');
            } finally {
                setLoading(false);
            }
        };

        fetchGuilds();
    }, [userId, navigate]);

    const handleGuildToggle = (guildId: string) => {
        setSelectedGuilds(prev => 
            prev.includes(guildId) 
                ? prev.filter(id => id !== guildId)
                : [...prev, guildId]
        );
    };

    const handleSelectAll = () => {
        if (selectedGuilds.length === guilds.length) {
            setSelectedGuilds([]);
        } else {
            setSelectedGuilds(guilds.map(g => g.id));
        }
    };

    const handleSubmit = async () => {
        if (selectedGuilds.length === 0) {
            setError('Please select at least one server');
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${BACKEND_URL}/auth/add-bot-to-servers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('discord_token')}`
                },
                body: JSON.stringify({
                    user_id: userId,
                    selected_guilds: selectedGuilds
                })
            });

            if (!response.ok) {
                throw new Error('Failed to generate OAuth URLs');
            }

            const data = await response.json();
            
            // Open OAuth URLs in new tabs
            data.oauth_urls.forEach((urlInfo: any, index: number) => {
                setTimeout(() => {
                    window.open(urlInfo.oauth_url, '_blank');
                }, index * 500); // Stagger opening to avoid popup blockers
            });

            // Redirect to success page
            navigate(`/callback?platform=discord&message=Please authorize the bot in each server tab that opened&servers_count=${data.total_servers}`);
            
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add bot to servers');
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="server-selection-container">
                <div className="loading-spinner">
                    <div className="spinner"></div>
                    <p>Loading your servers...</p>
                </div>
            </div>
        );
    }

    if (error && guilds.length === 0) {
        return (
            <div className="server-selection-container">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="error-container"
                >
                    <h2>❌ Error</h2>
                    <p>{error}</p>
                    <button onClick={() => navigate('/login')} className="back-button">
                        Back to Login
                    </button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="server-selection-container">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="server-selection-content"
            >
                <div className="header">
                    <h1>🤖 Select Servers</h1>
                    <p>
                        Welcome <strong>{username}</strong>! Choose which servers to add the CyberGuard bot to for automatic hate speech moderation.
                    </p>
                    <div className="stats">
                        <span>You have admin access to {guilds.length} servers</span>
                    </div>
                </div>

                {error && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="error-message"
                    >
                        {error}
                    </motion.div>
                )}

                <div className="controls">
                    <button 
                        onClick={handleSelectAll}
                        className="select-all-button"
                    >
                        {selectedGuilds.length === guilds.length ? 'Deselect All' : 'Select All'}
                    </button>
                    <span className="selected-count">
                        {selectedGuilds.length} of {guilds.length} selected
                    </span>
                </div>

                <div className="guilds-grid">
                    {guilds.map((guild) => (
                        <motion.div
                            key={guild.id}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            whileHover={{ scale: 1.02 }}
                            className={`guild-card ${selectedGuilds.includes(guild.id) ? 'selected' : ''}`}
                            onClick={() => handleGuildToggle(guild.id)}
                        >
                            <div className="guild-icon">
                                {guild.icon ? (
                                    <img src={guild.icon} alt={guild.name} />
                                ) : (
                                    <div className="default-icon">{guild.name.charAt(0).toUpperCase()}</div>
                                )}
                            </div>
                            <div className="guild-info">
                                <h3>{guild.name}</h3>
                                <span className="guild-id">ID: {guild.id}</span>
                            </div>
                            <div className="selection-indicator">
                                {selectedGuilds.includes(guild.id) && '✓'}
                            </div>
                        </motion.div>
                    ))}
                </div>

                {guilds.length === 0 && (
                    <div className="no-guilds">
                        <h3>🔍 No Servers Found</h3>
                        <p>You don't have admin permissions in any Discord servers.</p>
                        <p>Please ask a server admin to add the bot, or create your own server to test.</p>
                    </div>
                )}

                <div className="actions">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="skip-button"
                    >
                        Skip for Now
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={selectedGuilds.length === 0 || submitting}
                        className="submit-button"
                    >
                        {submitting ? (
                            <>
                                <div className="button-spinner"></div>
                                Adding Bot...
                            </>
                        ) : (
                            `Add Bot to ${selectedGuilds.length} Server${selectedGuilds.length !== 1 ? 's' : ''}`
                        )}
                    </button>
                </div>
            </motion.div>
        </div>
    );
};

export default ServerSelectionPage;
