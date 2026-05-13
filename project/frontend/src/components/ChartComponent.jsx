/**
 * ChartComponent
 * Displays real-time queue analytics using Recharts
 */

import React from 'react';
import {
    LineChart,
    Line,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import styles from './ChartComponent.module.css';

const ChartComponent = ({ data = [], isLoading = false, title = 'Analytics Chart' }) => {
    if (isLoading) {
        return (
            <div className={styles.container}>
                <h3 className={styles.title}>{title}</h3>
                <div className={styles.skeleton}>Loading chart...</div>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className={styles.container}>
                <h3 className={styles.title}>{title}</h3>
                <div className={styles.empty}>No data available yet</div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <h3 className={styles.title}>{title}</h3>

            <div className={styles.chartWrapper}>
                <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient
                                id="colorPeopleCount"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                                <stop offset="5%" stopColor="#667eea" stopOpacity={0.8} />
                                <stop offset="95%" stopColor="#667eea" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient
                                id="colorQueueLength"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                                <stop offset="5%" stopColor="#f093fb" stopOpacity={0.8} />
                                <stop offset="95%" stopColor="#f093fb" stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid strokeDasharray="3 3" stroke="#edf2f7" />
                        <XAxis
                            dataKey="time"
                            tick={{ fontSize: 12 }}
                            stroke="#a0aec0"
                        />
                        <YAxis tick={{ fontSize: 12 }} stroke="#a0aec0" />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#1a202c',
                                border: '1px solid #667eea',
                                borderRadius: '8px',
                                color: '#e2e8f0',
                            }}
                            cursor={{ stroke: '#667eea', strokeWidth: 2 }}
                        />
                        <Legend
                            wrapperStyle={{ paddingTop: '20px' }}
                            iconType="line"
                        />

                        <Area
                            type="monotone"
                            dataKey="people_count"
                            stroke="#667eea"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorPeopleCount)"
                            name="People Count"
                            isAnimationActive={true}
                        />
                        <Area
                            type="monotone"
                            dataKey="queue_length"
                            stroke="#f093fb"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorQueueLength)"
                            name="Queue Length"
                            isAnimationActive={true}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div className={styles.stats}>
                <div className={styles.statItem}>
                    <span className={styles.label}>Last Point:</span>
                    <span className={styles.value}>
                        {data[data.length - 1]?.time || 'N/A'}
                    </span>
                </div>
                <div className={styles.statItem}>
                    <span className={styles.label}>Data Points:</span>
                    <span className={styles.value}>{data.length}</span>
                </div>
                <div className={styles.statItem}>
                    <span className={styles.label}>Span:</span>
                    <span className={styles.value}>
                        {data.length > 1
                            ? `${Math.floor((data[data.length - 1].timestamp - data[0].timestamp) / 60000)} min`
                            : 'N/A'}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default ChartComponent;
