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
      
      // Handle the response structure from AnalyticsTimelineController
      const actualHeatmap = data.heatmap || (data.data && data.data.heatmap);
      
      if (actualHeatmap && Array.isArray(actualHeatmap)) {
        setHeatmapData(actualHeatmap);
        // Flatten 2D array safely to find max
        let max = 0;
        for (let r = 0; r < actualHeatmap.length; r++) {
          if (Array.isArray(actualHeatmap[r])) {
            for (let c = 0; c < actualHeatmap[r].length; c++) {
              if (actualHeatmap[r][c] > max) max = actualHeatmap[r][c];
            }
          }
        }
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

  // Color function with HIGH VISIBILITY for dark backgrounds
  const getHeatColor = (value) => {
    if (value === 0) return 'rgba(30, 41, 59, 0.8)'; // Slate-800 — visible dark tile
    const intensity = value / maxIntensity;
    
    // Solid, bright colors that pop on dark backgrounds
    if (intensity < 0.2) return `rgba(56, 189, 248, ${0.4 + intensity * 2})`; // Sky-400
    if (intensity < 0.4) return `rgba(34, 211, 238, ${0.5 + intensity})`; // Cyan-400
    if (intensity < 0.6) return `rgba(52, 211, 153, ${0.6 + intensity * 0.5})`; // Emerald-400
    if (intensity < 0.8) return `rgba(251, 191, 36, ${0.7 + intensity * 0.3})`; // Amber-400
    return `rgba(248, 113, 113, ${0.8 + intensity * 0.2})`; // Red-400
  };

  const GRID_SIZE = 20;
  const gridCells = [];

  if (heatmapData.length > 0 && Array.isArray(heatmapData[0])) {
    for (let row = 0; row < GRID_SIZE; row++) {
      for (let col = 0; col < GRID_SIZE; col++) {
        const value = (heatmapData[row] && heatmapData[row][col]) ? heatmapData[row][col] : 0;
        gridCells.push({
          id: row * GRID_SIZE + col,
          value,
          color: getHeatColor(value),
          row,
          col
        });
      }
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
                <div className="relative aspect-square w-full max-w-2xl mx-auto rounded-xl overflow-hidden shadow-inner" style={{ backgroundColor: '#0f172a' }}>
                  {/* Grid */}
                  <div 
                    className="absolute inset-0 grid gap-[1px]"
                    style={{ 
                      gridTemplateColumns: `repeat(${GRID_SIZE}, minmax(0, 1fr))`,
                      backgroundColor: 'rgba(51, 65, 85, 0.3)'
                    }}
                  >
                    {gridCells.map(cell => (
                      <div
                        key={cell.id}
                        className="w-full h-full transition-all duration-300 hover:scale-110 hover:z-10 cursor-crosshair relative group"
                        style={{ 
                          backgroundColor: cell.color,
                          boxShadow: cell.value > 0 ? `inset 0 0 8px ${cell.color}, 0 0 12px ${cell.color}` : 'none'
                        }}
                        title={`Zone (${cell.row}, ${cell.col}) | Density: ${cell.value}`}
                      >
                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-20 pointer-events-none">
                          <div className="bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap border border-white/10">
                            ({cell.row},{cell.col}): {cell.value}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Axis Labels */}
                  <div className="absolute -bottom-6 left-0 right-0 flex justify-between px-1">
                    <span className="text-[10px] text-gray-500">0</span>
                    <span className="text-[10px] text-gray-500">← X Axis →</span>
                    <span className="text-[10px] text-gray-500">{GRID_SIZE}</span>
                  </div>
                </div>

                {/* Legend */}
                <div className="mt-10 flex flex-wrap items-center justify-center gap-4 text-sm text-gray-300 bg-slate-900/60 p-4 rounded-xl border border-white/10 w-max mx-auto">
                  <span className="font-semibold text-gray-200 mr-1">Density:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded" style={{ backgroundColor: 'rgba(30, 41, 59, 0.8)', border: '1px solid rgba(148,163,184,0.3)' }} />
                    <span className="text-gray-400">None</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded" style={{ backgroundColor: 'rgba(56, 189, 248, 0.6)' }} />
                    <span className="text-gray-400">Low</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded" style={{ backgroundColor: 'rgba(52, 211, 153, 0.7)' }} />
                    <span className="text-gray-400">Medium</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded" style={{ backgroundColor: 'rgba(251, 191, 36, 0.85)' }} />
                    <span className="text-gray-400">High</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded" style={{ backgroundColor: 'rgba(248, 113, 113, 0.9)' }} />
                    <span className="text-gray-400">Critical</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center py-20 text-gray-500">
                <Target className="w-16 h-16 mb-4 opacity-20" />
                <p className="text-gray-400">No spatial data available for this date.</p>
                <p className="text-sm text-gray-600 mt-2">Run the ML service to generate heatmap data.</p>
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
              <div className="bg-black/30 p-4 rounded-xl border border-white/10">
                <p className="text-gray-400 text-sm mb-1">Peak Zone Intensity</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-white">{Math.ceil(maxIntensity)}</span>
                  <span className="text-gray-500 text-sm mb-1">hits</span>
                </div>
              </div>

              <div className="bg-black/30 p-4 rounded-xl border border-white/10">
                <p className="text-gray-400 text-sm mb-1">Active Floor Coverage</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-white">{Math.round((activeCells / (GRID_SIZE * GRID_SIZE)) * 100)}%</span>
                </div>
                <div className="w-full bg-white/10 h-2 rounded-full mt-3 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-sky-400 to-emerald-400 rounded-full transition-all duration-500" 
                    style={{ width: `${(activeCells / (GRID_SIZE * GRID_SIZE)) * 100}%` }}
                  />
                </div>
              </div>

              <div className="bg-black/30 p-4 rounded-xl border border-white/10">
                <p className="text-gray-400 text-sm mb-1">Total Detections Logged</p>
                <span className="text-2xl font-bold text-white">{totalDetections.toLocaleString()}</span>
              </div>

              <div className="bg-black/30 p-4 rounded-xl border border-white/10">
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
