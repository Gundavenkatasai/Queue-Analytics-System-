import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Hexagon, Camera, Calendar, RefreshCw, Activity, Target } from 'lucide-react';

const HeatmapView = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [cameraId, setCameraId] = useState('camera_1');
  const [heatmapData, setHeatmapData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [maxIntensity, setMaxIntensity] = useState(0);

  const fetchHeatmapData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/analytics/heatmap?camera_id=${cameraId}&date=${selectedDate}`
      );
      const data = await response.json();
      if (data.status === 'success' && data.data.heatmap_data) {
        setHeatmapData(data.data.heatmap_data);
        const max = Math.max(...data.data.heatmap_data.flat());
        setMaxIntensity(max > 0 ? max : 1);
      }
    } catch (error) {
      console.error('Error fetching heatmap:', error);
    } finally {
      setLoading(false);
    }
  }, [cameraId, selectedDate]);

  useEffect(() => {
    fetchHeatmapData();
  }, [fetchHeatmapData]);

  const getHeatColor = (value) => {
    if (value === 0) return 'rgba(255, 255, 255, 0.02)';
    const intensity = value / maxIntensity;
    
    // Enterprise Dark Theme Gradient (Deep Blue -> Cyan -> Yellow -> Coral)
    if (intensity < 0.2) return `rgba(14, 165, 233, ${intensity + 0.2})`; // Light Sky Blue
    if (intensity < 0.5) return `rgba(16, 185, 129, ${intensity + 0.3})`; // Emerald
    if (intensity < 0.8) return `rgba(245, 158, 11, ${intensity + 0.4})`; // Amber
    return `rgba(239, 68, 68, ${intensity + 0.2})`; // Red
  };

  const GRID_SIZE = 20;
  const gridCells = [];

  if (heatmapData.length > 0) {
    for (let i = 0; i < GRID_SIZE * GRID_SIZE; i++) {
      const value = heatmapData[i] || 0;
      gridCells.push({
        id: i,
        value,
        color: getHeatColor(value),
        row: Math.floor(i / GRID_SIZE),
        col: i % GRID_SIZE
      });
    }
  }

  const activeCells = gridCells.filter(c => c.value > 0).length;
  const totalDetections = gridCells.reduce((sum, c) => sum + c.value, 0);
  const avgIntensity = (totalDetections / (GRID_SIZE * GRID_SIZE)).toFixed(2);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Hexagon className="text-primary" />
            Spatial Heatmap Analysis
          </h2>
          <p className="text-sm text-gray-400 mt-1">Visualize high-traffic zones and dwell areas.</p>
        </div>
        
        <div className="flex items-center space-x-4 bg-black/40 p-2 rounded-lg border border-white/10">
          <div className="flex items-center space-x-2 px-2">
            <Camera className="w-4 h-4 text-gray-400" />
            <select 
              value={cameraId} 
              onChange={(e) => setCameraId(e.target.value)}
              className="bg-transparent text-white border-none focus:ring-0 text-sm appearance-none outline-none cursor-pointer"
            >
              <option value="camera_1" className="bg-background">Camera 1 (Main Entrance)</option>
              <option value="camera_2" className="bg-background">Camera 2 (Exit)</option>
            </select>
          </div>
          
          <div className="w-px h-6 bg-white/10"></div>
          
          <div className="flex items-center space-x-2 px-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <input 
              type="date" 
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="bg-transparent text-white border-none focus:ring-0 text-sm outline-none cursor-pointer [color-scheme:dark]"
            />
          </div>

          <button 
            onClick={fetchHeatmapData}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
            title="Refresh Data"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Heatmap Grid Area */}
        <div className="lg:col-span-3">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-panel p-6 rounded-2xl flex flex-col h-full"
          >
            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center space-y-4 py-20">
                <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-400">Processing spatial data...</p>
              </div>
            ) : gridCells.length > 0 ? (
              <>
                <div className="relative aspect-square w-full max-w-2xl mx-auto border border-white/10 rounded-xl overflow-hidden bg-black/50 shadow-inner">
                  {/* Overlay Grid Lines for tech aesthetic */}
                  <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10 pointer-events-none mix-blend-overlay"></div>
                  
                  <div 
                    className="absolute inset-0 grid"
                    style={{ gridTemplateColumns: `repeat(${GRID_SIZE}, minmax(0, 1fr))` }}
                  >
                    {gridCells.map(cell => (
                      <div
                        key={cell.id}
                        className="w-full h-full border border-white/[0.02] transition-colors duration-300 hover:border-white/30"
                        style={{ 
                          backgroundColor: cell.color,
                          boxShadow: cell.value > 0 ? `0 0 15px ${cell.color}` : 'none'
                        }}
                        title={`Zone (${cell.row}, ${cell.col}) | Density: ${cell.value}`}
                      />
                    ))}
                  </div>
                </div>

                {/* Legend */}
                <div className="mt-8 flex items-center justify-center space-x-6 text-sm text-gray-400 bg-black/20 p-4 rounded-xl border border-white/5 w-max mx-auto">
                  <span className="font-semibold text-gray-300 mr-2">Density:</span>
                  <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-white/5 border border-white/10" /> Minimal</div>
                  <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-sky-500/50" /> Low</div>
                  <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-emerald-500/60" /> Medium</div>
                  <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-amber-500/70" /> High</div>
                  <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-red-500/80" /> Critical</div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center py-20 text-gray-500">
                <Target className="w-16 h-16 mb-4 opacity-20" />
                <p>No spatial data available for this date</p>
              </div>
            )}
          </motion.div>
        </div>

        {/* Stats Sidebar */}
        <div className="space-y-6">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel p-6 rounded-2xl"
          >
            <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Activity className="text-primary w-5 h-5" />
              Spatial Metrics
            </h3>
            
            <div className="space-y-4">
              <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                <p className="text-gray-400 text-sm mb-1">Peak Zone Intensity</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-white">{Math.ceil(maxIntensity)}</span>
                  <span className="text-gray-500 text-sm mb-1">hits</span>
                </div>
              </div>

              <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                <p className="text-gray-400 text-sm mb-1">Active Floor Coverage</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-white">{Math.round((activeCells / (GRID_SIZE * GRID_SIZE)) * 100)}%</span>
                </div>
                <div className="w-full bg-white/5 h-1.5 rounded-full mt-3 overflow-hidden">
                  <div 
                    className="h-full bg-primary rounded-full" 
                    style={{ width: `${(activeCells / (GRID_SIZE * GRID_SIZE)) * 100}%` }}
                  />
                </div>
              </div>

              <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                <p className="text-gray-400 text-sm mb-1">Total Detections Logged</p>
                <span className="text-2xl font-bold text-white">{totalDetections.toLocaleString()}</span>
              </div>

              <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                <p className="text-gray-400 text-sm mb-1">Avg Zone Density</p>
                <span className="text-2xl font-bold text-white">{avgIntensity}</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default HeatmapView;
