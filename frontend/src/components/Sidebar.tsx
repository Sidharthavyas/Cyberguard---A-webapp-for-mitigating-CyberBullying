/**
 * Sidebar component with hamburger menu for navigation
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './Sidebar.css';

interface SidebarProps {
    currentPage?: string;
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage = 'feed' }) => {
    const [isOpen, setIsOpen] = useState(false);

    const toggleSidebar = () => {
        setIsOpen(!isOpen);
    };

    const menuItems = [
        { id: 'feed', label: 'Feed', icon: '📊' },
        { id: 'platforms', label: 'Platforms', icon: '🔗' },
        { id: 'analytics', label: 'Analytics', icon: '📈' },
        { id: 'settings', label: 'Settings', icon: '⚙️' }
    ];

    return (
        <>
            {/* Hamburger Button */}
            <button
                className="hamburger-btn"
                onClick={toggleSidebar}
                aria-label="Toggle menu"
            >
                <motion.div
                    animate={isOpen ? 'open' : 'closed'}
                    className="hamburger-icon"
                >
                    <motion.span
                        variants={{
                            closed: { rotate: 0, y: 0 },
                            open: { rotate: 45, y: 8 }
                        }}
                    />
                    <motion.span
                        variants={{
                            closed: { opacity: 1 },
                            open: { opacity: 0 }
                        }}
                    />
                    <motion.span
                        variants={{
                            closed: { rotate: 0, y: 0 },
                            open: { rotate: -45, y: -8 }
                        }}
                    />
                </motion.div>
            </button>

            {/* Overlay */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        className="sidebar-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={toggleSidebar}
                    />
                )}
            </AnimatePresence>

            {/* Sidebar */}
            <AnimatePresence>
                {isOpen && (
                    <motion.nav
                        className="sidebar"
                        initial={{ x: -280 }}
                        animate={{ x: 0 }}
                        exit={{ x: -280 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                    >
                        <div className="sidebar-header">
                            <div className="sidebar-logo">CG</div>
                            <h2 className="sidebar-title">CyberGuard</h2>
                        </div>

                        <ul className="sidebar-menu">
                            {menuItems.map((item) => (
                                <li key={item.id}>
                                    <button
                                        className={`menu-item ${currentPage === item.id ? 'active' : ''}`}
                                        onClick={() => {
                                            // Navigate to page (implement routing later)
                                            console.log(`Navigate to ${item.id}`);
                                            setIsOpen(false);
                                        }}
                                    >
                                        <span className="menu-icon">{item.icon}</span>
                                        <span className="menu-label">{item.label}</span>
                                    </button>
                                </li>
                            ))}
                        </ul>

                        <div className="sidebar-footer">
                            <button
                                className="logout-btn"
                                onClick={() => {
                                    localStorage.removeItem('twitter_access_token');
                                    window.location.href = '/';
                                }}
                            >
                                <span>🚪</span>
                                <span>Logout</span>
                            </button>
                        </div>
                    </motion.nav>
                )}
            </AnimatePresence>
        </>
    );
};

export default Sidebar;
