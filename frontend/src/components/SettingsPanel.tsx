/**
 * Settings Panel - basic moderation preferences stored via backend
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { settingsAPI } from '../services/api';
import './SettingsPanel.css';

interface Settings {
    realtime_enabled: boolean;
    auto_delete: boolean;
    language_filter: string;
}

const SettingsPanel: React.FC = () => {
    const userId = localStorage.getItem('twitter_user_id') || 'anonymous';
    const [settings, setSettings] = useState<Settings | null>(null);
    const [saving, setSaving] = useState(false);

    const loadSettings = async () => {
        const data = await settingsAPI.getSettings(userId);
        setSettings(data);
    };

    useEffect(() => {
        loadSettings();
    }, []);

    const updateField = (partial: Partial<Settings>) => {
        if (!settings) return;
        setSettings({ ...settings, ...partial });
    };

    const save = async () => {
        if (!settings) return;
        setSaving(true);
        try {
            const updated = await settingsAPI.updateSettings(userId, settings);
            setSettings(updated);
        } finally {
            setSaving(false);
        }
    };

    if (!settings) {
        return (
            <div className="settings-panel card">
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div className="settings-panel card">
            <div className="settings-header">
                <h2>Settings</h2>
                <p className="text-sm">Control how CyberGuard reacts to detected content.</p>
            </div>

            <div className="settings-grid">
                <div className="setting-item">
                    <div>
                        <div className="setting-title">Real-time updates</div>
                        <div className="setting-description text-sm">
                            When enabled, new events stream into the feed as they happen.
                        </div>
                    </div>
                    <button
                        className="btn btn-secondary setting-toggle"
                        onClick={() => updateField({ realtime_enabled: !settings.realtime_enabled })}
                    >
                        {settings.realtime_enabled ? 'On' : 'Off'}
                    </button>
                </div>

                <div className="setting-item">
                    <div>
                        <div className="setting-title">Auto-delete toxic content</div>
                        <div className="setting-description text-sm">
                            Automatically remove high-confidence bullying content from connected platforms.
                        </div>
                    </div>
                    <button
                        className="btn btn-secondary setting-toggle"
                        onClick={() => updateField({ auto_delete: !settings.auto_delete })}
                    >
                        {settings.auto_delete ? 'Enabled' : 'Disabled'}
                    </button>
                </div>

                <div className="setting-item">
                    <div>
                        <div className="setting-title">Language filter</div>
                        <div className="setting-description text-sm">
                            Limit moderation to specific languages or keep it global.
                        </div>
                    </div>
                    <select
                        className="settings-select"
                        value={settings.language_filter}
                        onChange={(e) => updateField({ language_filter: e.target.value })}
                    >
                        <option value="all">All languages</option>
                        <option value="en">English only</option>
                        <option value="es">Spanish only</option>
                    </select>
                </div>
            </div>

            <motion.button
                className="btn btn-primary settings-save-btn"
                onClick={save}
                whileHover={{ scale: saving ? 1 : 1.02 }}
                whileTap={{ scale: saving ? 1 : 0.98 }}
                disabled={saving}
            >
                {saving ? 'Saving...' : 'Save changes'}
            </motion.button>
        </div>
    );
};

export default SettingsPanel;

