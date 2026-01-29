/**
 * Multi-platform OAuth login page with platform selector.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import './LoginPage.css';

type Platform = 'twitter' | 'discord' | 'reddit';

const LoginPage: React.FC = () => {
    const [selectedPlatform, setSelectedPlatform] = useState<Platform>('twitter');

    const handleLogin = () => {
        // Use VITE_API_URL for production (Hugging Face) or localhost for dev
        const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        
        // Redirect to platform-specific OAuth endpoint
        const authUrls: Record<Platform, string> = {
            twitter: `${BACKEND_URL}/auth/twitter/login`,
            discord: `${BACKEND_URL}/auth/discord/login`,
            reddit: `${BACKEND_URL}/auth/reddit/login`
        };

        window.location.href = authUrls[selectedPlatform];
    };

    const platformInfo: Record<Platform, { icon: React.ReactNode; name: string; color: string }> = {
        twitter: {
            name: 'Twitter',
            color: 'var(--twitter-color, #1DA1F2)',
            icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.643 4.937c-.835.37-1.732.62-2.675.733.962-.576 1.7-1.49 2.048-2.578-.9.534-1.897.922-2.958 1.13-.85-.904-2.06-1.47-3.4-1.47-2.572 0-4.658 2.086-4.658 4.66 0 .364.042.718.12 1.06-3.873-.195-7.304-2.05-9.602-4.868-.4.69-.63 1.49-.63 2.342 0 1.616.823 3.043 2.072 3.878-.764-.025-1.482-.234-2.11-.583v.06c0 2.257 1.605 4.14 3.737 4.568-.392.106-.803.162-1.227.162-.3 0-.593-.028-.877-.082.593 1.85 2.313 3.198 4.352 3.234-1.595 1.25-3.604 1.995-5.786 1.995-.376 0-.747-.022-1.112-.065 2.062 1.323 4.51 2.093 7.14 2.093 8.57 0 13.255-7.098 13.255-13.254 0-.2-.005-.402-.014-.602.91-.658 1.7-1.477 2.323-2.41z" />
                </svg>
            )
        },
        discord: {
            name: 'Discord',
            color: '#5865F2',
            icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
            )
        },
        reddit: {
            name: 'Reddit',
            color: '#FF4500',
            icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 15.567c-.06.164-.168.28-.328.344-.157.062-.335.062-.492 0-.157-.063-.265-.18-.328-.344-.332-.887-1.157-1.687-2.477-2.403-1.195-.65-2.578-.974-4.146-.974s-2.95.325-4.146.975c-1.32.716-2.145 1.516-2.477 2.402-.063.165-.171.281-.328.344-.157.062-.335.062-.492 0-.16-.063-.268-.18-.328-.344-.332-.89-.158-1.668.516-2.338.675-.67 1.582-1.25 2.72-1.74 1.14-.49 2.432-.735 3.88-.735s2.74.245 3.88.734c1.138.49 2.045 1.07 2.72 1.74.674.67.848 1.45.516 2.34zm-2.53-6.03c0 .517-.19.96-.57 1.328-.38.367-.835.55-1.363.55-.527 0-.982-.183-1.363-.55-.38-.368-.57-.81-.57-1.328s.19-.96.57-1.328c.38-.367.836-.55 1.363-.55.528 0 .983.183 1.363.55.38.367.57.81.57 1.328zm-7.588 0c0 .517.19.96.57 1.328.38.367.835.55 1.363.55.527 0 .982-.183 1.363-.55.38-.368.57-.81.57-1.328s-.19-.96-.57-1.328c-.38-.367-.836-.55-1.363-.55-.528 0-.983.183-1.363.55-.38.368-.57.81-.57 1.328z" />
                </svg>
            )
        }
    };

    return (
        <div className="login-page">
            <motion.div
                className="login-container"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                <div className="logo">
                    CG
                </div>

                <h1 className="login-title">
                    CyberGuard
                </h1>

                <p className="login-subtitle">
                    Multi-platform AI-powered content moderation
                </p>

                <div className="feature-list">
                    <motion.div
                        className="feature"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1, duration: 0.4 }}
                    >
                        <span>AI-Powered Detection With Transformers</span>
                    </motion.div>

                    <motion.div
                        className="feature"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2, duration: 0.4 }}
                    >
                        <span>Multilingual Support</span>
                    </motion.div>

                    <motion.div
                        className="feature"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3, duration: 0.4 }}
                    >
                        <span>Real-time Moderation</span>
                    </motion.div>
                </div>

                {/* Platform Selector */}
                <motion.div
                    className="platform-selector"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4, duration: 0.3 }}
                >
                    <label className="selector-label">Select Platform</label>
                    <div className="platform-options">
                        {(Object.keys(platformInfo) as Platform[]).map((platform) => (
                            <motion.button
                                key={platform}
                                className={`platform-option ${selectedPlatform === platform ? 'selected' : ''}`}
                                onClick={() => setSelectedPlatform(platform)}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <div className="platform-icon" style={{ color: platformInfo[platform].color }}>
                                    {platformInfo[platform].icon}
                                </div>
                                <span className="platform-name">{platformInfo[platform].name}</span>
                            </motion.button>
                        ))}
                    </div>
                </motion.div>

                {/* Login Button */}
                <motion.button
                    className="btn btn-primary login-btn"
                    onClick={handleLogin}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    style={{
                        background: platformInfo[selectedPlatform].color
                    }}
                >
                    {platformInfo[selectedPlatform].icon}
                    <span style={{ marginLeft: '0.5rem' }}>
                        Connect with {platformInfo[selectedPlatform].name}
                    </span>
                </motion.button>
            </motion.div>
        </div>
    );
};

export default LoginPage;
