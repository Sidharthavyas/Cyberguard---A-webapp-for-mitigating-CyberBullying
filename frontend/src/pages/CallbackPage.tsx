/**
 * 
 * OAuth callback handler page.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import './CallbackPage.css';

const CallbackPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
    const [message, setMessage] = useState('Processing authentication...');

    useEffect(() => {
        const processCallback = () => {
            // Check for error
            const error = searchParams.get('error');
            if (error) {
                setStatus('error');
                setMessage(`Authentication failed: ${error}`);
                setTimeout(() => navigate('/'), 3000);
                return;
            }

            // Get tokens from URL
            const accessToken = searchParams.get('access_token');
            const userId = searchParams.get('user_id');
            const username = searchParams.get('username');

            if (!accessToken || !userId || !username) {
                setStatus('error');
                setMessage('Missing authentication data');
                setTimeout(() => navigate('/'), 3000);
                return;
            }

            // Store in localStorage
            localStorage.setItem('twitter_access_token', accessToken);
            localStorage.setItem('twitter_user_id', userId);
            localStorage.setItem('twitter_username', username);

            setStatus('success');
            setMessage(`Welcome, @${username}! Redirecting to dashboard...`);

            // Redirect to dashboard
            setTimeout(() => navigate('/dashboard'), 2000);
        };

        processCallback();
    }, [searchParams, navigate]);

    return (
        <div className="callback-page">
            <motion.div
                className="callback-container glass"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
            >
                {status === 'processing' && (
                    <>
                        <div className="spinner"></div>
                        <p className="callback-message">{message}</p>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <motion.div
                            className="success-icon"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: 'spring', stiffness: 200 }}
                        >
                            ✓
                        </motion.div>
                        <p className="callback-message success">{message}</p>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <motion.div
                            className="error-icon"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: 'spring', stiffness: 200 }}
                        >
                            ✗
                        </motion.div>
                        <p className="callback-message error">{message}</p>
                    </>
                )}
            </motion.div>
        </div>
    );
};

export default CallbackPage;
