import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, LogIn, Activity, AlertTriangle, Clock, Camera } from 'lucide-react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

const StatCard = ({ title, value, subtitle, icon, trend, alert }) => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-panel p-6 rounded-2xl relative overflow-hidden group ${
        alert ? 'border-destructive/50 shadow-destructive/10' : ''
      }`}
    >
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        {icon}
      </div>
      
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-gray-400 text-sm font-medium">{title}</p>
          <h3 className={`text-4xl font-bold mt-2 ${alert ? 'text-destructive' : 'text-white'}`}>
            {value}
          </h3>
        </div>
        <div className={`p-3 rounded-xl ${alert ? 'bg-destructive/20 text-destructive' : 'bg-primary/20 text-primary'}`}>
          {icon}
        </div>
      </div>
      
      <div className="flex items-center text-sm">
        {trend && (
          <span className={`px-2 py-1 rounded-md mr-2 font-medium ${
            trend > 0 ? 'bg-destructive/20 text-destructive' : 'bg-green-500/20 text-green-500'
          }`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
        <span className="text-gray-500">{subtitle}</span>
      </div>
      
      {alert && (
        <div className="absolute bottom-0 left-0 w-full h-1 bg-destructive animate-pulse" />
      )}
    </motion.div>
  );
};

const Dashboard = () => {
    const [liveData, setLiveData] = useState(null);
    const [history, setHistory] = useState([]);
    const [alert, setAlert] = useState(null);
    const [loading, setLoading] = useState(true);
    const [backendOnline, setBackendOnline] = useState(true);
    const [connectionError, setConnectionError] = useState(null);
    const [dataSource, setDataSource] = useState('laravel'); // 'laravel' | 'flask' | 'offline'
    const pollIntervalRef = useRef(null);
    const loadingTimeoutRef = useRef(null);
    
    useEffect(() => {
        // Stop the spinner after 8s regardless, so user sees an error instead of infinite spin
        loadingTimeoutRef.current = setTimeout(() => setLoading(false), 8000);

        const fetchLiveData = async () => {
            // ── Strategy 1: Try the Laravel backend (primary) ─────────────────
            try {
                const response = await fetch('http://localhost:8000/api/analytics/live', {
                    signal: AbortSignal.timeout(3000),
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const apiResponse = await response.json();
                const data = apiResponse.data || apiResponse;

                setConnectionError(null);
                setLoading(false);
                clearTimeout(loadingTimeoutRef.current);
                setDataSource('laravel');

                const isLive = data.is_live !== false;
                setBackendOnline(isLive);
                setLiveData(data);

                if (isLive) {
                    appendHistory(data);
                    checkAlerts(data);
                } else {
                    setAlert(null);
                }
                return; // success — skip fallback
            } catch (laravelErr) {
                // Laravel offline or error — try Flask ML API directly
            }

            // ── Strategy 2: Try Flask ML API directly (port 8001) ─────────────
            try {
                const response = await fetch('http://localhost:8001/api/stats', {
                    signal: AbortSignal.timeout(2000),
                });
                if (!response.ok) throw new Error(`Flask HTTP ${response.status}`);
                const flaskData = await response.json();
                const data = flaskData.data || flaskData;

                // Normalize Flask response to match Laravel's schema
                const normalizedData = {
                    camera_id: data.camera_id || 'camera_1',
                    people_count: data.people_count || 0,
                    occupancy_percentage: data.occupancy_percentage || 0,
                    entry_count: data.entry_count || 0,
                    exit_count: data.exit_count || 0,
                    queue_detected: data.queue_detected || false,
                    queue_length: data.queue_length || 0,
                    dwell_time_avg: data.dwell_time_avg || 0,
                    dwell_time_max: data.dwell_time_max || 0,
                    timestamp: data.timestamp || new Date().toISOString(),
                    is_live: true, // Flask always has live data
                    avg_wait_time: data.avg_wait_time || 0,
                };

                setConnectionError(null);
                setLoading(false);
                clearTimeout(loadingTimeoutRef.current);
                setDataSource('flask');
                setBackendOnline(true);
                setLiveData(normalizedData);
                appendHistory(normalizedData);
                checkAlerts(normalizedData);
                return;
            } catch (flaskErr) {
                // Both offline
            }

            // ── Both sources offline ──────────────────────────────────────────
            setBackendOnline(false);
            setDataSource('offline');
            setConnectionError('Both Laravel (port 8000) and ML Flask API (port 8001) are unreachable.');
            if (!liveData) setLoading(false);
        };

        const appendHistory = (data) => {
            if (!data.timestamp) return;
            setHistory(prev => {
                const timeStr = new Date(data.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                if (prev.length > 0 && prev[prev.length - 1].raw_ts === data.timestamp) return prev;
                const updated = [...prev, {
                    timestamp: timeStr,
                    raw_ts: data.timestamp,
                    people_count: data.people_count,
                    occupancy: data.occupancy_percentage
                }];
                return updated.slice(-60);
            });
        };

        const checkAlerts = (data) => {
            if (data.people_count > 50) {
                setAlert({ type: 'high_occupancy', message: `High Occupancy Alert: ${data.people_count} people detected (Threshold: 50)`, severity: 'high' });
            } else if (data.queue_detected) {
                setAlert({ type: 'queue_detected', message: `Queue Formation Detected! Length: ${data.queue_length} people`, severity: 'warning' });
            } else {
                setAlert(null);
            }
        };
        
        fetchLiveData();
        pollIntervalRef.current = setInterval(fetchLiveData, 2000);
        
        return () => {
            clearInterval(pollIntervalRef.current);
            clearTimeout(loadingTimeoutRef.current);
        };
    }, []);

    
    if (loading) {
        return (
            <div className="h-full flex flex-col items-center justify-center space-y-4">
                <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-400 font-medium">Connecting to AI Surveillance Stream...</p>
            </div>
        );
    }

    if (!liveData && connectionError) {
        return (
            <div className="h-full flex flex-col items-center justify-center space-y-4 p-8">
                <AlertTriangle className="text-destructive w-12 h-12" />
                <p className="text-white font-semibold text-lg">All Backends Offline</p>
                <div className="bg-black/30 border border-white/10 rounded-xl p-4 max-w-md w-full text-sm space-y-2">
                    <p className="text-gray-300 font-medium">Start both servers to see live data:</p>
                    <div className="space-y-1">
                        <p className="text-gray-400">① Laravel API: <code className="text-primary bg-black/40 px-1.5 py-0.5 rounded">php artisan serve</code> <span className="text-gray-600">(backend dir)</span></p>
                        <p className="text-gray-400">② ML Service: <code className="text-primary bg-black/40 px-1.5 py-0.5 rounded">python main.py</code> <span className="text-gray-600">(ml-service dir)</span></p>
                    </div>
                </div>
                <p className="text-gray-600 text-xs mt-1">{connectionError}</p>
            </div>
        );
    }

    // Show zeros placeholder if we have no data yet but backend is reachable
    const displayData = liveData || {
        people_count: 0, occupancy_percentage: 0, entry_count: 0, exit_count: 0,
        queue_detected: false, queue_length: 0, dwell_time_avg: 0, dwell_time_max: 0
    };

    return (
        <div className="space-y-6">
            {/* ML Service Offline Banner */}
            {!backendOnline && (
                <div className="flex items-center space-x-3 bg-yellow-500/10 border border-yellow-500/40 px-4 py-3 rounded-xl">
                    <AlertTriangle className="text-yellow-400 w-5 h-5 flex-shrink-0" />
                    <div>
                        <p className="text-yellow-300 font-semibold text-sm">ML Service Not Sending Data</p>
                        <p className="text-yellow-500/80 text-xs mt-0.5">
                            {connectionError
                                ? `Backend unreachable: ${connectionError}`
                                : 'The Python ML service has stopped streaming. Run python main.py in the ml-service directory.'}
                        </p>
                    </div>
                    <div className="ml-auto flex-shrink-0">
                        <span className="inline-flex items-center space-x-1.5 bg-yellow-500/20 px-2.5 py-1 rounded-md">
                            <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                            <span className="text-yellow-300 text-xs font-bold uppercase tracking-wider">Waiting for Stream</span>
                        </span>
                    </div>
                </div>
            )}

            {/* Header & Status */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
                <div>
                    <div className="flex items-center space-x-2">
                        <Camera className="text-primary w-5 h-5" />
                        <h2 className="text-lg font-semibold text-white">Camera 1 (Main Entrance)</h2>
                    </div>
                    <p className="text-gray-400 text-sm mt-1">
                        YOLOv8 Detection Engine • 15 FPS
                        {dataSource === 'flask' && (
                            <span className="ml-2 text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/30">via Flask ML API</span>
                        )}
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border ${
                        backendOnline ? 'bg-primary/10 border-primary/20' : 'bg-yellow-500/10 border-yellow-500/30'
                    }`}>
                        <span className={`w-2 h-2 rounded-full ${
                            backendOnline ? 'bg-primary animate-pulse' : 'bg-yellow-400'
                        }`}></span>
                        <span className={`font-bold text-xs tracking-widest uppercase ${
                            backendOnline ? 'text-primary' : 'text-yellow-400'
                        }`}>{backendOnline ? 'Detection Active' : 'Stream Paused'}</span>
                    </div>
                    
                    <div className="flex items-center space-x-3 bg-black/40 px-4 py-2 rounded-lg border border-white/10">
                        {backendOnline ? (
                            <>
                                <div className="flex space-x-1 items-end h-4">
                                    <motion.div animate={{ height: [8, 16, 8] }} transition={{ repeat: Infinity, duration: 1 }} className="w-1 bg-green-500 rounded-full"></motion.div>
                                    <motion.div animate={{ height: [12, 6, 12] }} transition={{ repeat: Infinity, duration: 1.2 }} className="w-1 bg-green-500 rounded-full"></motion.div>
                                    <motion.div animate={{ height: [16, 10, 16] }} transition={{ repeat: Infinity, duration: 0.8 }} className="w-1 bg-green-500 rounded-full"></motion.div>
                                </div>
                                <span className="text-green-500 font-semibold text-sm tracking-wide uppercase">System Live</span>
                                {liveData?.data_age_seconds != null && (
                                    <span className="text-green-600 text-xs opacity-70 ml-1">
                                        {liveData.data_age_seconds}s ago
                                    </span>
                                )}
                            </>
                        ) : (
                            <span className="text-gray-500 font-semibold text-sm tracking-wide uppercase">System Offline</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Alert Banner */}
            <AnimatePresence>
                {alert && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className={`overflow-hidden rounded-xl ${
                            alert.severity === 'high' ? 'bg-destructive/20 border border-destructive/50' : 'bg-yellow-500/20 border border-yellow-500/50'
                        }`}
                    >
                        <div className="p-4 flex items-center space-x-3">
                            <AlertTriangle className={alert.severity === 'high' ? 'text-destructive' : 'text-yellow-500'} />
                            <span className={`font-medium ${alert.severity === 'high' ? 'text-destructive' : 'text-yellow-500'}`}>
                                {alert.message}
                            </span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                <StatCard 
                    title="Active People" 
                    value={displayData.people_count}
                    subtitle={displayData.people_count > 50 ? "Over capacity limit" : "Normal operating range"}
                    icon={<Users size={24} />}
                    alert={displayData.people_count > 50}
                />
                <StatCard 
                    title="Area Occupancy" 
                    value={`${(displayData.occupancy_percentage ?? 0).toFixed(1)}%`}
                    subtitle="Of maximum capacity"
                    icon={<Activity size={24} />}
                    alert={(displayData.occupancy_percentage ?? 0) > 85}
                />
                <StatCard 
                    title="Total Entries" 
                    value={displayData.entry_count ?? 0}
                    subtitle="Cumulative today"
                    icon={<LogIn size={24} />}
                />
                <StatCard 
                    title="Total Exits" 
                    value={displayData.exit_count ?? 0}
                    subtitle="Cumulative today"
                    icon={<LogIn size={24} />}
                />
                <StatCard 
                    title="Queue Status" 
                    value={displayData.queue_detected ? `${displayData.queue_length} wait` : "Clear"}
                    subtitle="Current queue length"
                    icon={<Clock size={24} />}
                    alert={displayData.queue_detected}
                />
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="glass-panel p-6 rounded-2xl"
                >
                    <h3 className="text-lg font-semibold text-white mb-6">Real-time Occupancy Flow</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorPeople" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                                <XAxis dataKey="timestamp" stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip 
                                  contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                                  itemStyle={{ color: '#fff' }}
                                />
                                <Area type="monotone" dataKey="people_count" stroke="hsl(var(--primary))" strokeWidth={3} fillOpacity={1} fill="url(#colorPeople)" isAnimationActive={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                <div className="space-y-6">
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.1 }}
                      className="glass-panel p-6 rounded-2xl"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4">Live Traffic Distribution</h3>
                        <div className="space-y-4">
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="text-gray-400">Current Load</span>
                                    <span className="text-white font-medium">{(displayData.occupancy_percentage ?? 0).toFixed(1)}%</span>
                                </div>
                                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500 ease-out"
                                        style={{ width: `${Math.min(100, displayData.occupancy_percentage ?? 0)}%` }}
                                    />
                                </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4 mt-6">
                                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                    <p className="text-gray-500 text-xs mb-1">Total Exits</p>
                                    <p className="text-2xl font-bold text-white">{displayData.exit_count}</p>
                                </div>
                                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                    <p className="text-gray-500 text-xs mb-1">Avg Dwell Time</p>
                                    <p className="text-2xl font-bold text-white">{(displayData.dwell_time_avg ?? 0).toFixed(1)}s</p>
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    <motion.div 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.2 }}
                      className="glass-panel p-6 rounded-2xl border-l-4 border-l-primary"
                    >
                        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">System Status</h3>
                        <p className="text-white">AI Detection Pipeline Active.</p>
                        <p className="text-sm text-gray-500 mt-1">Processing frames with ByteTrack and YOLOv8m. Last sync: {new Date().toLocaleTimeString()}</p>
                    </motion.div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
