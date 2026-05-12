/**
 * Helper Utilities
 */

/**
 * Format timestamp to readable time
 */
export const formatTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
};

/**
 * Format timestamp to full datetime
 */
export const formatDateTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
};

/**
 * Get relative time (e.g., "2 minutes ago")
 */
export const getRelativeTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    const now = new Date();
    const date = new Date(timestamp);
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) {
        return `${seconds}s ago`;
    }
    if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}m ago`;
    }
    if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)}h ago`;
    }
    return formatDateTime(timestamp);
};

/**
 * Generate color based on value severity
 */
export const getColorByValue = (value, thresholds = { low: 5, medium: 15, high: 30 }) => {
    if (value >= thresholds.high) return '#ff6b6b'; // Red
    if (value >= thresholds.medium) return '#ffd93d'; // Yellow
    if (value >= thresholds.low) return '#6bcf7f'; // Green
    return '#4ecdc4'; // Teal
};

/**
 * Format large numbers with commas
 */
export const formatNumber = (num) => {
    return Number(num).toLocaleString('en-US');
};

/**
 * Calculate statistics from array of values
 */
export const calculateStats = (values) => {
    if (!values || values.length === 0) {
        return {
            avg: 0,
            min: 0,
            max: 0,
            total: 0,
        };
    }

    return {
        avg: (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2),
        min: Math.min(...values),
        max: Math.max(...values),
        total: values.reduce((a, b) => a + b, 0),
    };
};

/**
 * Convert data for Recharts LineChart
 */
export const prepareChartData = (historyData) => {
    if (!historyData || !Array.isArray(historyData)) {
        return [];
    }

    return historyData.map((item) => ({
        time: formatTime(item.created_at),
        timestamp: new Date(item.created_at).getTime(),
        people_count: item.people_count,
        queue_length: item.queue_length,
        entry_count: item.entry_count,
        exit_count: item.exit_count,
    }));
};

/**
 * Check if data is stale (older than threshold)
 */
export const isDataStale = (timestamp, thresholdSeconds = 30) => {
    if (!timestamp) return true;
    const now = new Date();
    const date = new Date(timestamp);
    const seconds = Math.floor((now - date) / 1000);
    return seconds > thresholdSeconds;
};

/**
 * Retry function with exponential backoff
 */
export const retryWithBackoff = async (
    fn,
    maxRetries = 3,
    initialDelay = 1000
) => {
    let delay = initialDelay;

    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise((resolve) => setTimeout(resolve, delay));
            delay *= 2;
        }
    }
};
