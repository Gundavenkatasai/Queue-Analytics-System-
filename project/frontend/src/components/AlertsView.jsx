import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, AlertTriangle, X, ShieldAlert, Clock, Settings, Camera, Filter, RefreshCw } from 'lucide-react';

const AlertsView = () => {
  const [alerts, setAlerts] = useState([]);
  const [cameraId, setCameraId] = useState('camera_1');
  const [timeRange, setTimeRange] = useState('24h');
  const [loading, setLoading] = useState(false);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/alerts?camera_id=${cameraId}&limit=100`
      );
      const data = await response.json();

      if (data.status === 'success' && Array.isArray(data.data)) {
        // Map MongoDB alert documents to display format
        const mapped = data.data
          .filter(a => !a.acknowledged) // Show unacknowledged only
          .map(a => ({
            id: a._id || a.id,
            type: a.alert_type || 'unknown',
            message: a.message || `${a.alert_type} alert`,
            description: a.message || 'Alert triggered by the ML detection pipeline.',
            timestamp: new Date(a.created_at || Date.now()),
            severity: a.severity === 'high' ? 'critical' : (a.severity || 'warning'),
            threshold: a.threshold ?? null,
            actual: a.value ?? a.people_count ?? null,
            cameraId: a.camera_id || cameraId,
            mongoId: a._id || a.id,
          }));
        setAlerts(mapped);
      } else {
        setAlerts([]);
      }
    } catch (error) {
      console.error('Error fetching alerts:', error);
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [cameraId]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const dismissAlert = async (alertId, mongoId) => {
    // Acknowledge in backend
    try {
      await fetch(`http://localhost:8000/api/alerts/${mongoId}/acknowledge`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (e) {
      console.warn('Failed to acknowledge alert in backend:', e);
    }
    setAlerts(prev => prev.filter(a => a.id !== alertId));
  };

  const getSeverityStyles = (severity) => {
    switch (severity) {
      case 'critical': return { bg: 'bg-destructive/10', border: 'border-destructive/50', text: 'text-destructive', icon: <ShieldAlert size={20} /> };
      case 'warning': return { bg: 'bg-yellow-500/10', border: 'border-yellow-500/50', text: 'text-yellow-500', icon: <AlertTriangle size={20} /> };
      case 'info': return { bg: 'bg-primary/10', border: 'border-primary/50', text: 'text-primary', icon: <Bell size={20} /> };
      default: return { bg: 'bg-gray-500/10', border: 'border-gray-500/50', text: 'text-gray-400', icon: <Bell size={20} /> };
    }
  };

  const getTimeDifference = (date) => {
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Bell className="text-primary" />
            Security & System Alerts
          </h2>
          <p className="text-sm text-gray-400 mt-1">Real-time threat detections from MongoDB Atlas.</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 bg-black/40 p-2 rounded-lg border border-white/10">
          <div className="flex items-center space-x-2 px-2">
            <Camera className="w-4 h-4 text-gray-400" />
            <select 
              value={cameraId} 
              onChange={(e) => setCameraId(e.target.value)}
              className="bg-transparent text-white border-none focus:ring-0 text-sm appearance-none outline-none cursor-pointer"
            >
              <option value="camera_1" className="bg-background">Camera 1 (Main)</option>
              <option value="camera_2" className="bg-background">Camera 2 (Exit)</option>
            </select>
          </div>
          
          <div className="w-px h-6 bg-white/10 hidden sm:block"></div>
          
          <div className="flex items-center space-x-2 px-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <select 
              value={timeRange} 
              onChange={(e) => setTimeRange(e.target.value)}
              className="bg-transparent text-white border-none focus:ring-0 text-sm appearance-none outline-none cursor-pointer"
            >
              <option value="1h" className="bg-background">Last Hour</option>
              <option value="24h" className="bg-background">Last 24 Hours</option>
              <option value="7d" className="bg-background">Last 7 Days</option>
            </select>
          </div>

          <div className="w-px h-6 bg-white/10 hidden sm:block"></div>

          <button 
            onClick={fetchAlerts}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
            title="Refresh"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Alert List */}
        <div className="lg:col-span-3 space-y-4">
          <div className="flex justify-between items-center mb-4 px-2">
            <h3 className="text-gray-400 font-semibold tracking-wide uppercase text-sm">Active Alerts</h3>
            <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded-md">{alerts.length} Pending</span>
          </div>

          <AnimatePresence>
            {loading && alerts.length === 0 ? (
              <div className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center space-y-4">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-400 text-sm">Loading from MongoDB Atlas...</p>
              </div>
            ) : alerts.length > 0 ? (
              alerts.map(alert => {
                const styles = getSeverityStyles(alert.severity);
                return (
                  <motion.div 
                    key={alert.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    layout
                    className={`glass-panel p-5 rounded-xl border-l-4 ${styles.border} flex flex-col sm:flex-row gap-4 relative group`}
                  >
                    <div className={`w-12 h-12 rounded-full ${styles.bg} ${styles.text} flex items-center justify-center flex-shrink-0`}>
                      {styles.icon}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1">
                        <h4 className="text-white font-bold text-lg truncate pr-8">{alert.message}</h4>
                        <span className="text-xs text-gray-500 whitespace-nowrap flex items-center gap-1">
                          <Clock size={12} />
                          {getTimeDifference(alert.timestamp)}
                        </span>
                      </div>
                      <p className="text-gray-400 text-sm mb-3">{alert.description}</p>
                      
                      {alert.threshold && (
                        <div className="flex gap-4 text-xs font-medium bg-black/40 w-max px-3 py-1.5 rounded-lg border border-white/5">
                          <span className="text-gray-500">Threshold: <span className="text-gray-300">{alert.threshold}</span></span>
                          <span className="text-gray-500">Actual: <span className={styles.text}>{alert.actual}</span></span>
                        </div>
                      )}
                    </div>

                    <button 
                      onClick={() => dismissAlert(alert.id, alert.mongoId)}
                      className="absolute top-4 right-4 p-2 text-gray-500 hover:text-white hover:bg-white/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                      title="Acknowledge Alert"
                    >
                      <X size={18} />
                    </button>
                  </motion.div>
                );
              })
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="glass-panel p-16 rounded-2xl flex flex-col items-center justify-center text-center border-dashed border-white/10"
              >
                <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center mb-4">
                  <ShieldAlert className="w-10 h-10 text-green-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">All Systems Clear</h3>
                <p className="text-gray-400">No active alerts requiring attention.</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel p-6 rounded-2xl"
          >
            <h3 className="text-lg font-semibold text-white mb-6">Alert Summary</h3>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-black/20 rounded-xl border border-white/5">
                <span className="text-gray-400">Total Active</span>
                <span className="text-2xl font-bold text-white">{alerts.length}</span>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-destructive/5 rounded-xl border border-destructive/20">
                <span className="text-destructive font-medium flex items-center gap-2"><ShieldAlert size={16}/> Critical</span>
                <span className="text-xl font-bold text-destructive">{alerts.filter(a => a.severity === 'critical').length}</span>
              </div>

              <div className="flex justify-between items-center p-3 bg-yellow-500/5 rounded-xl border border-yellow-500/20">
                <span className="text-yellow-500 font-medium flex items-center gap-2"><AlertTriangle size={16}/> Warnings</span>
                <span className="text-xl font-bold text-yellow-500">{alerts.filter(a => a.severity === 'warning').length}</span>
              </div>

              <div className="flex justify-between items-center p-3 bg-primary/5 rounded-xl border border-primary/20">
                <span className="text-primary font-medium flex items-center gap-2"><Bell size={16}/> Info</span>
                <span className="text-xl font-bold text-primary">{alerts.filter(a => a.severity === 'info').length}</span>
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-panel p-6 rounded-2xl"
          >
            <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Settings className="text-primary w-5 h-5" />
              Threshold Configuration
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Max Occupancy</label>
                <div className="relative">
                  <input type="number" defaultValue="50" className="input-field py-2 bg-black/40 text-sm" />
                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-xs">people</span>
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Max Wait Time</label>
                <div className="relative">
                  <input type="number" defaultValue="300" className="input-field py-2 bg-black/40 text-sm" />
                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-xs">seconds</span>
                </div>
              </div>

              <button className="btn-primary w-full mt-2 py-2 text-sm">Apply Changes</button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default AlertsView;
