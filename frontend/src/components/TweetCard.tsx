/**
 * Professional Tweet/Feed Card with Multi-Platform Support
 */

import { motion } from 'framer-motion';
import './TweetCard.css';

interface ModerationEvent {
    tweet_id: string;
    text: string;
    language: string;
    label: number;
    label_name: string;
    confidence: number;
    bullying_probability: number;
    deleted: boolean;
    action: string;
    timestamp: string;
    platform?: string;
    id?: string;
    author?: string;
    channel?: string;
}

interface TweetCardProps {
    event: ModerationEvent;
    index: number;
}

const TweetCard: React.FC<TweetCardProps> = ({ event, index }) => {
    // Destructure event properties
    const {
        tweet_id,
        text,
        label,
        label_name: labelName,
        confidence,
        bullying_probability: bullyingProbability,
        deleted,
        action,
        timestamp,
        platform = 'twitter',
        id,
        author,
        channel
    } = event;

    const tweetId = id || tweet_id;


    const getActionLabel = (action: string) => {
        switch (action) {
            case 'delete':
                return 'Deleted';
            case 'flag':
                return 'Flagged';
            case 'ignore':
                return 'Safe';
            default:
                return action;
        }
    };

    const getPlatformEmoji = (platform: string) => {
        switch (platform.toLowerCase()) {
            case 'discord': return '💬';
            case 'reddit': return '🔴';
            case 'twitter':
            default: return '𝕏';
        }
    };

    return (
        <motion.div
            className={`tweet-card label-${label}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
        >
            {/* Card Header */}
            <div className="card-header">
                <div className="header-left">
                    <span className="platform-badge" title={platform}>
                        {getPlatformEmoji(platform)}
                    </span>
                    <span className="tweet-id">
                        {author || channel || `ID: ${tweetId.slice(0, 10)}...`}
                    </span>
                </div>
                <div className="header-right">
                    {timestamp && (
                        <span className="timestamp">
                            {new Date(timestamp).toLocaleTimeString()}
                        </span>
                    )}
                    <div className={`level-badge label-${label}`}>
                        {labelName}
                    </div>
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
                            {getActionLabel(action)}
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
            </div>
        </motion.div>
    );
};

export default TweetCard;
