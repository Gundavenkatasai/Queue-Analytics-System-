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
    const pollIntervalRef = useRef(null);
    
    useEffect(() => {
        const fetchLiveData = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/analytics/live');
                if (!response.ok) throw new Error('Failed to fetch');
                
                const apiResponse = await response.json();
                const data = apiResponse.data || apiResponse;
                
                setLiveData(data);
                setLoading(false);
                
                setHistory(prev => {
                    const updated = [...prev, {
                        timestamp: new Date(data.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}),
                        people_count: data.people_count,
                        occupancy: data.occupancy_percentage
                    }];
                    return updated.slice(-60);
                });
                
                if (data.people_count > 50) {
                    setAlert({
                        type: 'high_occupancy',
                        message: `High Occupancy Alert: ${data.people_count} people detected (Threshold: 50)`,
                        severity: 'high'
                    });
                } else if (data.queue_detected) {
                    setAlert({
                        type: 'queue_detected',
                        message: `Queue Formation Detected! Length: ${data.queue_length} people`,
                        severity: 'warning'
                    });
                } else {
                    setAlert(null);
                }
            } catch (error) {
                console.error('Live data error:', error);
                setLoading(false);
            }
        };
        
        fetchLiveData();
        pollIntervalRef.current = setInterval(fetchLiveData, 1000);
        
        return () => {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        };
    }, []);
    
    if (loading || !liveData) {
        return (
            <div className="h-full flex flex-col items-center justify-center space-y-4">
                <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-400 font-medium">Connecting to AI Surveillance Stream...</p>
            </div>
        );
    }
    
    return (
        <div className="space-y-6">
            {/* Header & Status */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
                <div>
                    <div className="flex items-center space-x-2">
                        <Camera className="text-primary w-5 h-5" />
                        <h2 className="text-lg font-semibold text-white">Camera 1 (Main Entrance)</h2>
                    </div>
                    <p className="text-gray-400 text-sm mt-1">YOLOv8 Detection Engine • 15 FPS</p>
                </div>
                
                <div className="flex items-center space-x-3 bg-black/40 px-4 py-2 rounded-lg border border-white/10">
                    <div className="flex space-x-1 items-end h-4">
                        <motion.div animate={{ height: [8, 16, 8] }} transition={{ repeat: Infinity, duration: 1 }} className="w-1 bg-green-500 rounded-full"></motion.div>
                        <motion.div animate={{ height: [12, 6, 12] }} transition={{ repeat: Infinity, duration: 1.2 }} className="w-1 bg-green-500 rounded-full"></motion.div>
                        <motion.div animate={{ height: [16, 10, 16] }} transition={{ repeat: Infinity, duration: 0.8 }} className="w-1 bg-green-500 rounded-full"></motion.div>
                    </div>
                    <span className="text-green-500 font-semibold text-sm tracking-wide">LIVE SYSTEM ACTIVE</span>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard 
                    title="Active People" 
                    value={liveData.people_count}
                    subtitle={liveData.people_count > 50 ? "Over capacity limit" : "Normal operating range"}
                    icon={<Users size={24} />}
                    alert={liveData.people_count > 50}
                />
                <StatCard 
                    title="Area Occupancy" 
                    value={`${(liveData.occupancy_percentage ?? 0).toFixed(1)}%`}
                    subtitle="Of maximum capacity"
                    icon={<Activity size={24} />}
                    alert={(liveData.occupancy_percentage ?? 0) > 85}
                />
                <StatCard 
                    title="Total Entries" 
                    value={liveData.entry_count}
                    subtitle="Cumulative today"
                    icon={<LogIn size={24} />}
                />
                <StatCard 
                    title="Queue Status" 
                    value={liveData.queue_detected ? `${liveData.queue_length} wait` : "Clear"}
                    subtitle="Current queue length"
                    icon={<Clock size={24} />}
                    alert={liveData.queue_detected}
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
                                    <span className="text-white font-medium">{(liveData.occupancy_percentage ?? 0).toFixed(1)}%</span>
                                </div>
                                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500 ease-out"
                                        style={{ width: `${Math.min(100, liveData.occupancy_percentage ?? 0)}%` }}
                                    />
                                </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4 mt-6">
                                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                    <p className="text-gray-500 text-xs mb-1">Total Exits</p>
                                    <p className="text-2xl font-bold text-white">{liveData.exit_count}</p>
                                </div>
                                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                                    <p className="text-gray-500 text-xs mb-1">Avg Dwell Time</p>
                                    <p className="text-2xl font-bold text-white">{(liveData.dwell_time_avg ?? 0).toFixed(1)}s</p>
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
