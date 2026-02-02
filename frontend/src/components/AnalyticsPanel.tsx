/**
 * Analytics Panel - dedicated view for deeper metrics
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { analyticsAPI } from '../services/api';
import './AnalyticsPanel.css';

interface LanguageStats {
    scanned: number;
    flagged: number;
    deleted: number;
}

interface AnalyticsSummary {
    total_scanned: number;
    total_flagged: number;
    total_deleted: number;
    per_language: Record<string, LanguageStats>;
}

const AnalyticsPanel: React.FC = () => {
    const [data, setData] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchSummary = async () => {
        try {
            const summary = await analyticsAPI.getSummary();
            setData(summary);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSummary();
    }, []);

    if (loading) {
        return (
            <div className="analytics-panel card">
                <div className="spinner"></div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="analytics-panel card">
                <p className="text-sm">No analytics available yet.</p>
            </div>
        );
    }

    const languages = Object.entries(data.per_language || {});

    return (
        <div className="analytics-panel card">
            <div className="analytics-header">
                <h2>Analytics</h2>
                <p className="text-sm">High-level trends across all moderated content.</p>
            </div>

            <div className="analytics-summary-grid">
                <motion.div
                    className="analytics-summary-card"
                    whileHover={{ y: -3 }}
                >
                    <span className="summary-label">Scanned</span>
                    <span className="summary-value">{data.total_scanned.toLocaleString()}</span>
                </motion.div>
                <motion.div
                    className="analytics-summary-card"
                    whileHover={{ y: -3 }}
                >
                    <span className="summary-label">Flagged</span>
                    <span className="summary-value">{data.total_flagged.toLocaleString()}</span>
                </motion.div>
                <motion.div
                    className="analytics-summary-card"
                    whileHover={{ y: -3 }}
                >
                    <span className="summary-label">Deleted</span>
                    <span className="summary-value">{data.total_deleted.toLocaleString()}</span>
                </motion.div>
            </div>

            {languages.length > 0 && (
                <div className="analytics-language-section">
                    <h3 className="text-sm font-semibold">By language</h3>
                    <div className="analytics-language-table">
                        <div className="table-header">
                            <span>Language</span>
                            <span>Scanned</span>
                            <span>Flagged</span>
                            <span>Deleted</span>
                        </div>
                        {languages.map(([lang, stats]) => (
                            <div key={lang} className="table-row">
                                <span>{lang.toUpperCase()}</span>
                                <span>{stats.scanned}</span>
                                <span>{stats.flagged}</span>
                                <span>{stats.deleted}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnalyticsPanel;

