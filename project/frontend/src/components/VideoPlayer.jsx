import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, Download, Video, VideoOff, Calendar, Camera, Clock, FileVideo, AlertCircle, XCircle, Circle } from 'lucide-react';

const VideoPlayer = () => {
  const [recordings, setRecordings] = useState([]);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [cameraId, setCameraId] = useState('camera_1');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const videoRef = useRef(null);

  const fetchRecordings = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) {
        setLoading(true);
      }
      setVideoError(false);
      const response = await fetch(`http://localhost:8000/api/recordings?camera_id=${cameraId}&date=${selectedDate}`);
      const data = await response.json();
      if (data.status === 'success') {
        // Filter out corrupted/empty recordings (< 1 KB are invalid video files)
        const allRecordings = Array.isArray(data.data) ? data.data : [];
        const nextRecordings = allRecordings.filter(r => (r.file_size_bytes || 0) >= 1024);
        setRecordings(nextRecordings);

        setSelectedRecording((current) => {
          if (!nextRecordings.length) {
            return null;
          }

          if (current) {
            const stillExists = nextRecordings.find((item) => item.id === current.id);
            if (stillExists) {
              if (
                stillExists.id === current.id &&
                stillExists.duration_seconds === current.duration_seconds &&
                stillExists.file_size_bytes === current.file_size_bytes &&
                stillExists.filename === current.filename
              ) {
                return current;
              }
              return stillExists;
            }
          }

          return nextRecordings[0];
        });
      }
    } catch (error) {
      console.error('Error fetching recordings:', error);
    } finally {
      if (!isSilent) {
        setLoading(false);
      }
    }
  }, [cameraId, selectedDate]);

  useEffect(() => {
    fetchRecordings(false);
  }, [fetchRecordings]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchRecordings(true);
    }, 10000);

    return () => clearInterval(interval);
  }, [fetchRecordings]);

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(e => {
            console.error("Play failed", e);
            setVideoError(true);
        });
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleRetry = () => {
    setVideoError(false);
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => setVideoError(true));
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    if (videoRef.current) {
      videoRef.current.currentTime = percent * duration;
    }
  };

  const handleDownload = async () => {
    if (!selectedRecording) return;
    try {
      const response = await fetch(`http://localhost:8000/api/recordings/${selectedRecording.id}/stream`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = selectedRecording.filename || 'recording.mp4';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading recording:', error);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  /**
   * Parse a recording's display time.
   * Priority: start_time field → filename timestamp → created_at → 'Unknown'
   */
  const formatRecordingDate = (rec, format = 'time') => {
    // Try start_time field first
    let dt = null;
    if (rec.start_time) {
      dt = new Date(rec.start_time);
    }
    // Fallback: parse from filename e.g. event_camera_1_20260516_213416.mp4
    if ((!dt || isNaN(dt)) && rec.filename) {
      const m = rec.filename.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
      if (m) {
        dt = new Date(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`);
      }
    }
    // Fallback: created_at
    if ((!dt || isNaN(dt)) && rec.created_at) {
      dt = new Date(rec.created_at);
    }
    if (!dt || isNaN(dt)) return 'Unknown';
    if (format === 'date') return dt.toLocaleDateString();
    return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const triggerManualRecording = async () => {
    try {
      // We send a custom alert to trigger recording
      await fetch('http://localhost:8000/api/alerts/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: cameraId,
          type: 'manual_trigger',
          severity: 'high',
          message: 'Manual recording triggered from dashboard'
        })
      });
      alert('Recording triggered! It will appear here in about 70 seconds.');
    } catch (error) {
      console.error('Error triggering recording:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Video className="text-primary" />
            Event Recording Archive
          </h2>
          <p className="text-sm text-gray-400 mt-1">Review historical surveillance footage and events.</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-4">
          <button 
            onClick={triggerManualRecording}
            className="flex items-center gap-2 px-4 py-2 bg-primary/20 hover:bg-primary/30 text-primary border border-primary/30 rounded-lg transition-all text-sm font-medium"
          >
            <Circle className="w-3 h-3 fill-primary animate-pulse" />
            Record Now
          </button>

          <div className="flex items-center space-x-4 bg-black/40 p-2 rounded-lg border border-white/10">
          <div className="flex items-center space-x-2 px-2">
            <Camera className="w-4 h-4 text-gray-400" />
            <select 
              value={cameraId} 
              onChange={(e) => setCameraId(e.target.value)}
              className="bg-transparent text-white border-none focus:ring-0 text-sm appearance-none outline-none cursor-pointer"
            >
              <option value="camera_1" className="bg-background text-white">Camera 1 (Main)</option>
              <option value="camera_2" className="bg-background text-white">Camera 2 (Exit)</option>
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
        </div>
      </div>
    </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Video Player */}
        <div className="lg:col-span-2 flex flex-col space-y-4">
          <div className="glass-panel p-2 rounded-2xl overflow-hidden relative group">
            {selectedRecording ? (
              <div className="relative aspect-video bg-black rounded-xl overflow-hidden flex items-center justify-center border border-white/10">
                <video
                  key={selectedRecording.id}
                  ref={videoRef}
                  controls
                  autoPlay
                  muted
                  playsInline
                  preload="auto"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  onEnded={() => setIsPlaying(false)}
                  onError={() => setVideoError(true)}
                  className={`w-full h-full object-contain ${videoError ? 'hidden' : 'block'}`}
                >
                  <source src={`http://localhost:8000/api/recordings/${selectedRecording.id}/stream`} type="video/mp4" />
                  Your browser does not support the HTML5 video tag.
                </video>
                
                {videoError && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 backdrop-blur-md p-6 text-center">
                    <XCircle className="w-16 h-16 text-destructive mb-4" />
                    <h3 className="text-xl font-semibold text-white mb-2">Playback Failed</h3>
                    <p className="text-gray-400 text-sm max-w-md mb-6">
                      The video could not be decoded by your browser. This usually happens with freshly-recorded files that are still being transcoded to H.264. Try clicking Retry in a few seconds, or download the file to view it locally.
                    </p>
                    <div className="flex gap-3">
                      <button 
                        onClick={handleRetry}
                        className="btn-primary flex items-center gap-2 px-6"
                      >
                        ↺ Retry
                      </button>
                      <button 
                        onClick={handleDownload}
                        className="flex items-center gap-2 px-6 py-2 border border-white/20 rounded-lg text-white hover:bg-white/10 transition-all"
                      >
                        <Download size={18} />
                        Download
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="aspect-video bg-black/40 rounded-xl flex flex-col items-center justify-center border border-dashed border-white/20 text-gray-500">
                <VideoOff className="w-16 h-16 mb-4 opacity-50" />
                <p className="font-medium text-lg">No Video Selected</p>
                <p className="text-sm opacity-70">Please select a recording from the list</p>
              </div>
            )}
          </div>
          
          {selectedRecording && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-panel p-4 rounded-xl flex justify-between items-center"
            >
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2">
                  <AlertCircle size={16} className="text-primary" />
                  Event Recording Metadata
                </h3>
                <p className="text-gray-400 text-sm mt-1">{selectedRecording.filename}</p>
              </div>
              <div className="text-right">
                <p className="text-white font-bold text-lg">{selectedRecording.duration_seconds}s</p>
                <p className="text-gray-500 text-xs">{(selectedRecording.file_size_bytes / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            </motion.div>
          )}
        </div>

        {/* Playlist */}
        <div className="glass-panel rounded-2xl flex flex-col overflow-hidden max-h-[calc(100vh-200px)] lg:max-h-[600px]">
          <div className="p-4 border-b border-white/5 bg-black/20">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Clock size={18} className="text-gray-400" />
              Timeline ({recordings.length})
            </h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-hide">
            {loading ? (
              <div className="flex justify-center p-8">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : recordings.length > 0 ? (
              recordings.map((rec, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setVideoError(false);
                    setSelectedRecording(rec);
                    setIsPlaying(true);
                  }}
                  className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 text-left ${
                    selectedRecording?.id === rec.id 
                      ? 'bg-primary/20 border border-primary/30 shadow-lg shadow-primary/10' 
                      : 'hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 mr-4 ${
                    selectedRecording?.id === rec.id ? 'bg-primary text-white' : 'bg-black/50 text-gray-400'
                  }`}>
                    <Play size={20} fill={selectedRecording?.id === rec.id ? "currentColor" : "none"} />
                  </div>
                  
                  <div className="flex-1 overflow-hidden">
                    <h4 className={`font-semibold truncate ${selectedRecording?.id === rec.id ? 'text-white' : 'text-gray-300'}`}>
                      {formatRecordingDate(rec, 'time')}
                    </h4>
                    <div className="flex items-center text-xs text-gray-500 mt-1 gap-2">
                      <span className="bg-black/50 px-2 py-0.5 rounded text-gray-400">{rec.duration_seconds}s</span>
                      <span>{(rec.file_size_bytes / 1024 / 1024).toFixed(1)} MB</span>
                    </div>
                  </div>
                </button>
              ))
            ) : (
              <div className="text-center p-8 text-gray-500">
                <Calendar size={32} className="mx-auto mb-3 opacity-30" />
                <p>No events recorded on this date.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
