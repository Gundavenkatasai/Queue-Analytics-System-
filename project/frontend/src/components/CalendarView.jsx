import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Calendar, ChevronLeft, ChevronRight, Camera, Clock, Video, Activity, BarChart2 } from 'lucide-react';

const CalendarView = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [timelineData, setTimelineData] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cameraId, setCameraId] = useState('camera_1');

  const [stats, setStats] = useState({ avgPeople: 0, maxQueue: 0 });

  const fetchTimelineData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Fetch raw timeline data
      const response = await fetch(`http://localhost:8000/api/analytics/timeline?camera_id=${cameraId}&date=${selectedDate}`);
      const data = await response.json();
      
      if (Array.isArray(data.data)) {
        setTimelineData(data.data);
      } else {
        setTimelineData([]);
      }

      // Fetch aggregated occupancy data (for Avg People)
      const occResponse = await fetch(`http://localhost:8000/api/analytics/occupancy?camera_id=${cameraId}&date=${selectedDate}`);
      const occData = await occResponse.json();

      // Fetch queue history data (for Max Queue)
      const queueResponse = await fetch(`http://localhost:8000/api/analytics/queue?camera_id=${cameraId}&date=${selectedDate}`);
      const queueData = await queueResponse.json();

      setStats({
        avgPeople: occData.avg_occupancy ? occData.avg_occupancy.toFixed(1) : 0,
        maxQueue: queueData.max_queue_length || 0
      });
      
    } catch (error) {
      console.error('Error fetching timeline or stats:', error);
      setTimelineData([]);
      setStats({ avgPeople: 0, maxQueue: 0 });
    } finally {
      setLoading(false);
    }
  }, [cameraId, selectedDate]);

  const fetchRecordings = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/recordings?camera_id=${cameraId}&date=${selectedDate}`);
      const data = await response.json();
      // API returns { status, count, data }
      if (data.status === 'success' && Array.isArray(data.data)) {
        setRecordings(data.data);
      } else {
        setRecordings([]);
      }
    } catch (error) {
      console.error('Error fetching recordings:', error);
      setRecordings([]);
    }
  }, [cameraId, selectedDate]);

  useEffect(() => {
    fetchTimelineData();
    fetchRecordings();
  }, [fetchTimelineData, fetchRecordings]);

  const handlePreviousDay = () => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() - 1);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  const handleNextDay = () => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() + 1);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  const { avgPeople, maxQueue } = stats;

  const displayDate = new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Calendar className="text-primary" />
            Calendar &amp; Timeline
          </h2>
          <p className="text-sm text-gray-400 mt-1">Analyse historical occupancy and recordings by date.</p>
        </div>

        <div className="flex items-center gap-3 bg-black/40 p-2 rounded-lg border border-white/10">
          <div className="flex items-center space-x-2 px-2">
            <Camera className="w-4 h-4 text-gray-400" />
            <select
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              className="bg-transparent text-white border-none focus:ring-0 text-sm appearance-none outline-none cursor-pointer"
            >
              <option value="camera_1" className="bg-background">Camera 1 (Main)</option>
              <option value="camera_2" className="bg-background">Camera 2 (Exit)</option>
              <option value="camera_3" className="bg-background">Camera 3</option>
            </select>
          </div>
        </div>
      </div>

      {/* Date Selector */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-4 rounded-2xl flex items-center justify-between"
      >
        <button
          onClick={handlePreviousDay}
          className="p-2.5 rounded-xl bg-white/5 hover:bg-primary/20 hover:text-primary text-gray-400 transition-all"
        >
          <ChevronLeft size={20} />
        </button>

        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-white font-bold text-lg">{displayDate}</p>
            <p className="text-gray-500 text-sm">{recordings.length} recordings • {timelineData.length} data points</p>
          </div>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="bg-black/40 text-white border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 [color-scheme:dark]"
          />
        </div>

        <button
          onClick={handleNextDay}
          className="p-2.5 rounded-xl bg-white/5 hover:bg-primary/20 hover:text-primary text-gray-400 transition-all"
        >
          <ChevronRight size={20} />
        </button>
      </motion.div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Data Points', value: timelineData.length, icon: <Activity size={20} />, color: 'text-primary' },
          { label: 'Avg People', value: avgPeople, icon: <BarChart2 size={20} />, color: 'text-emerald-400' },
          { label: 'Max Queue', value: maxQueue, icon: <Clock size={20} />, color: 'text-yellow-400' },
          { label: 'Recordings', value: recordings.length, icon: <Video size={20} />, color: 'text-blue-400' },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="glass-panel p-4 rounded-xl"
          >
            <div className={`${stat.color} mb-2`}>{stat.icon}</div>
            <p className="text-2xl font-bold text-white">{stat.value}</p>
            <p className="text-xs text-gray-400 mt-1">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Timeline Chart */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-6 rounded-2xl"
      >
        <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <Activity className="text-primary w-5 h-5" />
          People Count &amp; Queue Timeline
        </h3>
        {loading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : timelineData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(val) => new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  stroke="rgba(255,255,255,0.3)"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'rgba(0,0,0,0.85)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                  labelFormatter={(val) => new Date(val).toLocaleString()}
                />
                <Legend wrapperStyle={{ color: '#9ca3af', fontSize: '12px' }} />
                <Line type="monotone" dataKey="people_count" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} name="People Count" />
                <Line type="monotone" dataKey="queue_length" stroke="#f59e0b" strokeWidth={2} dot={false} name="Queue Length" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 flex flex-col items-center justify-center text-gray-500">
            <Activity className="w-12 h-12 mb-3 opacity-20" />
            <p>No timeline data for this date</p>
          </div>
        )}
      </motion.div>

      {/* Recordings Table */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel rounded-2xl overflow-hidden"
      >
        <div className="p-5 border-b border-white/5 bg-black/20 flex items-center gap-2">
          <Video className="text-primary w-5 h-5" />
          <h3 className="text-lg font-semibold text-white">Recordings for {selectedDate}</h3>
          <span className="ml-auto text-xs text-gray-500 bg-white/5 px-2 py-1 rounded-md">{recordings.length} files</span>
        </div>

        {recordings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider p-4 font-medium">Start Time</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider p-4 font-medium">End Time</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider p-4 font-medium">Duration</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider p-4 font-medium">File Size</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider p-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {recordings.map((rec, idx) => (
                    <motion.tr
                      key={idx}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: idx * 0.03 }}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="p-4 text-white font-medium">{new Date(rec.start_time).toLocaleTimeString()}</td>
                      <td className="p-4 text-gray-300">{new Date(rec.end_time).toLocaleTimeString()}</td>
                      <td className="p-4 text-gray-300">{rec.duration_seconds}s</td>
                      <td className="p-4 text-gray-300">{(rec.file_size_bytes / 1024 / 1024).toFixed(2)} MB</td>
                      <td className="p-4">
                        <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium px-2.5 py-1 rounded-full">
                          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                          Recorded
                        </span>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-gray-500">
            <Video className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p>No recordings for this date</p>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default CalendarView;
