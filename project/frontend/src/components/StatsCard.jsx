/**
 * StatsCard Component
 * Reusable card for displaying statistics
 */

import React from 'react';
import styles from './StatsCard.module.css';

const StatsCard = ({
    title,
    value,
    unit = '',
    icon: Icon,
    color = '#667eea',
    trend = null,
    isLoading = false,
    lastUpdated = null,
}) => {
    return (
        <div className={styles.card} style={{ borderLeftColor: color }}>
            <div className={styles.header}>
                <div className={styles.titleSection}>
                    <h3 className={styles.title}>{title}</h3>
                    {lastUpdated && (
                        <span className={styles.lastUpdated}>
                            Updated: {lastUpdated}
                        </span>
                    )}
                </div>
                {Icon && (
                    <div className={styles.icon} style={{ color }}>
                        <Icon size={24} />
                    </div>
                )}
            </div>

            <div className={styles.content}>
                {isLoading ? (
                    <div className={styles.skeleton}>Loading...</div>
                ) : (
                    <>
                        <div className={styles.value} style={{ color }}>
                            {value}
                            {unit && <span className={styles.unit}>{unit}</span>}
                        </div>

                        {trend !== null && (
                            <div
                                className={`${styles.trend} ${
                                    trend > 0 ? styles.up : styles.down
                                }`}
                            >
                                {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
                            </div>
                        )}
                    </>
                )}
            </div>

            <div className={styles.footer}>
                <div className={styles.pulse} style={{ backgroundColor: color }}></div>
                <span className={styles.status}>Real-time</span>
            </div>
        </div>
    );
};

export default StatsCard;
