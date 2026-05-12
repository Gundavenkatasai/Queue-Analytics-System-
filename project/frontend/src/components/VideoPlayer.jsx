import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, Download, VideoOff, Calendar, Camera, Clock, FileVideo, AlertCircle, XCircle } from 'lucide-react';

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

  const fetchRecordings = useCallback(async () => {
    try {
      setLoading(true);
      setVideoError(false);
      const response = await fetch(`http://localhost:8000/api/recordings?camera_id=${cameraId}&date=${selectedDate}`);
      const data = await response.json();
      if (data.status === 'success') {
        setRecordings(data.data);
        if (data.data.length > 0) {
          setSelectedRecording(data.data[0]);
        } else {
          setSelectedRecording(null);
        }
      }
    } catch (error) {
      console.error('Error fetching recordings:', error);
    } finally {
      setLoading(false);
    }
  }, [cameraId, selectedDate]);

  useEffect(() => {
    fetchRecordings();
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

  return (
    <div className="space-y-6">
      {/* Controls Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <FileVideo className="text-primary" />
            Video Recordings Archive
          </h2>
          <p className="text-sm text-gray-400 mt-1">Review event-based alerts and continuous footage.</p>
        </div>
        
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Video Player */}
        <div className="lg:col-span-2 flex flex-col space-y-4">
          <div className="glass-panel p-2 rounded-2xl overflow-hidden relative group">
            {selectedRecording ? (
              <div className="relative aspect-video bg-black rounded-xl overflow-hidden flex items-center justify-center border border-white/10">
                <video
                  ref={videoRef}
                  src={`http://localhost:8000/api/recordings/${selectedRecording.id}/stream`}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  onEnded={() => setIsPlaying(false)}
                  onError={() => setVideoError(true)}
                  className={`w-full h-full object-contain ${videoError ? 'hidden' : 'block'}`}
                />
                
                {videoError && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 backdrop-blur-md p-6 text-center">
                    <XCircle className="w-16 h-16 text-destructive mb-4" />
                    <h3 className="text-xl font-semibold text-white mb-2">Playback Not Supported</h3>
                    <p className="text-gray-400 text-sm max-w-md mb-6">
                      This browser does not support the video codec used in this recording. Please download the file to view it locally or install FFmpeg on the server for live transcoding.
                    </p>
                    <button 
                      onClick={handleDownload}
                      className="btn-primary flex items-center gap-2 w-auto px-6"
                    >
                      <Download size={18} />
                      Download Video File
                    </button>
                  </div>
                )}
                
                {!videoError && (
                  <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    
                    {/* Progress Bar */}
                    <div 
                      className="w-full h-2 bg-white/20 rounded-full mb-4 cursor-pointer relative overflow-hidden group/progress"
                      onClick={handleSeek}
                    >
                      <div 
                        className="absolute top-0 left-0 h-full bg-primary"
                        style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                      />
                    </div>
                    
                    {/* Controls */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <button 
                          onClick={handlePlayPause}
                          className="text-white hover:text-primary transition-colors focus:outline-none"
                        >
                          {isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
                        </button>
                        <span className="text-white text-sm font-medium tracking-wide">
                          {formatTime(currentTime)} / {formatTime(duration)}
                        </span>
                      </div>
                      
                      <button 
                        onClick={handleDownload}
                        className="text-white hover:text-primary transition-colors focus:outline-none"
                        title="Download Recording"
                      >
                        <Download size={20} />
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
                      {new Date(rec.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
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
