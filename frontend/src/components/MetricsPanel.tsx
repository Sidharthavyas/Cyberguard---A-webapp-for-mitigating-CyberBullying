/**
 * Professional Metrics Panel - Clean White UI
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { statsAPI } from '../services/api';
import './MetricsPanel.css';

interface Stats {
    total_scanned: number;
    total_flagged: number;
    total_deleted: number;
    per_language: Record<string, {
        scanned: number;
        flagged: number;
        deleted: number;
    }>;
    status: string;
    warning?: string;
}

interface MetricsPanelProps {
    latestEvent?: any;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({ latestEvent }) => {
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = async () => {
        try {
            const data = await statsAPI.getStats();
            setStats(data);
            setLoading(false);
        } catch (error) {
            console.error('Error fetching stats:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 5000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (latestEvent) {
            fetchStats();
        }
    }, [latestEvent]);

    if (loading) {
        return (
            <div className="metrics-panel">
                <div className="spinner"></div>
            </div>
        );
    }

    if (!stats) {
        return (
            <div className="metrics-panel">
                <p>No metrics available</p>
            </div>
        );
    }

    const languageData = Object.entries(stats.per_language || {});

    return (
        <div className="metrics-panel">
            <div className="panel-header">
                <h2 className="panel-title">Overview</h2>
                {stats.status && (
                    <div className="badge badge-success">
                        {stats.status}
                    </div>
                )}
            </div>

            {stats.warning && (
                <div className="metrics-warning">
                    <span className="warning-icon">⚠️</span>
                    <span>{stats.warning}</span>
                </div>
            )}

            <div className="metrics-grid">
                <motion.div
                    className="metric-card"
                    whileHover={{ y: -4 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                >
                    <div className="metric-header">
                        <span className="metric-icon">🔍</span>
                        <span className="metric-label">Scanned</span>
                    </div>
                    <div className="metric-value">{stats.total_scanned.toLocaleString()}</div>
                    <div className="metric-footer">
                        <span className="metric-subtitle">Total analyzed</span>
                    </div>
                </motion.div>

                <motion.div
                    className="metric-card metric-flagged"
                    whileHover={{ y: -4 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                >
                    <div className="metric-header">
                        <span className="metric-icon">⚠️</span>
                        <span className="metric-label">Flagged</span>
                    </div>
                    <div className="metric-value">{stats.total_flagged.toLocaleString()}</div>
                    <div className="metric-footer">
                        <span className="metric-subtitle">Potentially toxic</span>
                    </div>
                </motion.div>

                <motion.div
                    className="metric-card metric-deleted"
                    whileHover={{ y: -4 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                >
                    <div className="metric-header">
                        <span className="metric-icon">🗑️</span>
                        <span className="metric-label">Deleted</span>
                    </div>
                    <div className="metric-value">{stats.total_deleted.toLocaleString()}</div>
                    <div className="metric-footer">
                        <span className="metric-subtitle">Auto-removed</span>
                    </div>
                </motion.div>
            </div>

            {languageData.length > 0 && (
                <div className="language-breakdown">
                    <h3 className="breakdown-title">Language Breakdown</h3>
                    <div className="language-grid">
                        {languageData.map(([lang, data]) => (
                            <motion.div
                                key={lang}
                                className="language-card"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <div className="language-header">
                                    <span className="language-name">{lang.toUpperCase()}</span>
                                </div>
                                <div className="language-stats">
                                    <div className="lang-stat">
                                        <span className="lang-stat-label">Scanned</span>
                                        <span className="lang-stat-value">{data.scanned}</span>
                                    </div>
                                    <div className="lang-stat flagged">
                                        <span className="lang-stat-label">Flagged</span>
                                        <span className="lang-stat-value">{data.flagged}</span>
                                    </div>
                                    <div className="lang-stat deleted">
                                        <span className="lang-stat-label">Deleted</span>
                                        <span className="lang-stat-value">{data.deleted}</span>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MetricsPanel;
