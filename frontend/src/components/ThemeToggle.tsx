/**
 * Theme Toggle Button - Enhanced with animations
 */

import { motion } from 'framer-motion';
import { useTheme } from '../contexts/ThemeContext';
import './ThemeToggle.css';

const ThemeToggle: React.FC = () => {
    const { theme, toggleTheme } = useTheme();

    const isDark = theme === 'dark';

    return (
        <motion.button
            className={`theme-toggle ${isDark ? 'theme-toggle-dark' : 'theme-toggle-light'}`}
            onClick={toggleTheme}
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
        >
            <div className="theme-toggle-track">
                <motion.div
                    className="theme-toggle-thumb"
                    layout
                    transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                >
                    <span className="theme-toggle-icon" aria-hidden="true">
                        {isDark ? '🌙' : '☀️'}
                    </span>
                </motion.div>
                <span className="theme-toggle-label">
                    {isDark ? 'Dark' : 'Light'} mode
                </span>
            </div>
        </motion.button>
    );
};

export default ThemeToggle;
