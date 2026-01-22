/**
 * Professional Tweet Card with Clean White UI
 */

import { motion } from 'framer-motion';
import './TweetCard.css';

interface TweetCardProps {
    tweetId: string;
    text: string;
    language: string;
    label: number;  // 0=safe, 1=bullying
    labelName: string;  // "SAFE" or "BULLYING"
    confidence: number;
    bullyingProbability: number;
    deleted: boolean;
    action: string;
    timestamp?: string;
}

const TweetCard: React.FC<TweetCardProps> = ({
    tweetId,
    text,
    language,
    label,
    labelName,
    confidence,
    bullyingProbability,
    deleted,
    action,
    timestamp
}) => {


    const getActionIcon = (action: string) => {
        switch (action) {
            case 'delete':
                return '🗑️';
            case 'flag':
                return '⚠️';
            case 'ignore':
                return '✅';
            default:
                return '•';
        }
    };

    return (
        <motion.div
            className={`tweet-card label-${label}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{
                type: 'spring',
                stiffness: 300,
                damping: 25
            }}
        >
            <div className="tweet-header">
                <div className="tweet-meta">
                    <span className="tweet-id">#{tweetId.slice(-8)}</span>
                    <span className="tweet-language">{language.toUpperCase()}</span>
                </div>
                <div className={`level-badge label-${label}`}>
                    {labelName}
                </div>
            </div>

            <div className="tweet-content">
                <p className="tweet-text">{text}</p>
            </div>

            <div className="divider"></div>

            <div className="tweet-footer">
                <div className="tweet-stats">
                    <div className="stat">
                        <span className="stat-label">Confidence</span>
                        <span className="stat-value">{(confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="stat">
                        <span className="stat-label">Bullying Risk</span>
                        <span className="stat-value">{(bullyingProbability * 100).toFixed(0)}%</span>
                    </div>
                    <div className="stat">
                        <span className="stat-label">Action</span>
                        <span className="stat-value action-value">
                            {getActionIcon(action)} {action.charAt(0).toUpperCase() + action.slice(1)}
                        </span>
                    </div>
                </div>
                {deleted && (
                    <motion.div
                        className="deleted-badge"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 200 }}
                    >
                        Deleted
                    </motion.div>
                )}
                {timestamp && (
                    <div className="tweet-time">
                        {new Date(timestamp).toLocaleTimeString()}
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default TweetCard;
