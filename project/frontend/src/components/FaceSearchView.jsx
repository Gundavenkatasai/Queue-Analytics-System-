import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Upload, User, Clock, CheckCircle, AlertCircle, Image as ImageIcon, Film, MapPin } from 'lucide-react';

const FaceSearchView = () => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [personMatches, setPersonMatches] = useState([]);
  const [error, setError] = useState(null);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSearch = async () => {
    if (!imagePreview) return;

    setIsSearching(true);
    setError(null);
    setResults([]);
    setPersonMatches([]);

    try {
      const response = await fetch('http://localhost:8000/api/analytics/face-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image: imagePreview }),
      });

      const data = await response.json();
      if (data.status === 'success') {
        setResults(data.recording_matches || data.results || []);
        setPersonMatches(data.person_matches || []);
      } else {
        setError(data.message || 'Search failed');
      }
    } catch (err) {
      setError('Connection to backend failed');
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-card/40 p-8 rounded-2xl border border-white/5">
        <div className="absolute top-0 right-0 -mt-20 -mr-20 w-64 h-64 bg-primary/10 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="relative z-10">
          <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
            <User className="text-primary" size={32} />
            AI Face Search Intelligence
          </h1>
          <p className="text-gray-400 max-w-2xl">
            Upload a person's photo to identify them and find all their appearances across your surveillance recordings using advanced biometric embeddings.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Panel */}
        <div className="lg:col-span-1 space-y-6">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel p-6 rounded-2xl"
          >
            <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Upload className="text-primary" size={20} />
              Identify Target
            </h3>

            <div className="space-y-6">
              <div 
                className={`relative aspect-square rounded-xl border-2 border-dashed transition-all cursor-pointer overflow-hidden flex flex-col items-center justify-center
                  ${imagePreview ? 'border-primary/50' : 'border-white/10 hover:border-white/20 bg-white/5'}`}
                onClick={() => document.getElementById('face-upload').click()}
              >
                {imagePreview ? (
                  <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                ) : (
                  <>
                    <ImageIcon className="w-12 h-12 text-gray-500 mb-2" />
                    <p className="text-sm text-gray-400">Click to upload photo</p>
                  </>
                )}
                <input 
                  id="face-upload"
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  onChange={handleImageChange}
                />
              </div>

              <button
                onClick={handleSearch}
                disabled={!imagePreview || isSearching}
                className={`w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all
                  ${!imagePreview || isSearching 
                    ? 'bg-white/5 text-gray-500 cursor-not-allowed' 
                    : 'bg-primary hover:bg-primary/80 text-white shadow-lg shadow-primary/20'}`}
              >
                {isSearching ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Search size={20} />
                )}
                {isSearching ? 'Searching...' : 'Search Across Records'}
              </button>
            </div>
          </motion.div>

          {error && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-red-500/10 border border-red-500/20 p-4 rounded-xl flex items-center gap-3 text-red-400"
            >
              <AlertCircle size={20} />
              <p className="text-sm">{error}</p>
            </motion.div>
          )}
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {isSearching ? (
              <motion.div 
                key="searching"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center text-center space-y-4"
              >
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-primary/20 rounded-full animate-ping absolute inset-0" />
                  <div className="w-20 h-20 border-4 border-primary border-t-transparent rounded-full animate-spin relative z-10" />
                </div>
                <h3 className="text-xl font-bold text-white">Scanning Database...</h3>
                <p className="text-gray-400">Analyzing biometric patterns and comparing with stored identities.</p>
              </motion.div>
            ) : results.length > 0 ? (
              <motion.div 
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-4"
              >
                <div className="flex justify-between items-center px-2">
                  <h3 className="text-lg font-semibold text-white">
                    Found {results.length} Matching Videos
                  </h3>
                </div>

                {personMatches.length > 0 && (
                  <div className="glass-panel p-4 rounded-2xl border border-white/5">
                    <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                      <User size={16} className="text-primary" />
                      Matching Face Profiles
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {personMatches.map((person) => (
                        <div key={person.person_id} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300">
                          {person.person_id?.slice(0, 8)} · {Math.round((person.confidence || 0) * 100)}%
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {results.map((result, idx) => (
                    <motion.div
                      key={result.recording_id || result.filename || idx}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className="glass-panel p-4 rounded-2xl border border-white/5 hover:border-primary/30 transition-colors group"
                    >
                      <div className="flex flex-col gap-3">
                        <div className="aspect-video rounded-lg overflow-hidden bg-black/40 border border-white/10 shrink-0">
                          {result.stream_url ? (
                            <video className="w-full h-full object-cover" controls preload="metadata" src={result.stream_url} />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-500">
                              <Film size={32} />
                            </div>
                          )}
                        </div>

                        <div className="space-y-2">
                          <div className="flex justify-between items-start gap-3">
                            <div>
                              <span className="block text-xs font-mono text-gray-500 uppercase">
                                {result.filename || 'Recording'}
                              </span>
                              <span className="block text-[11px] text-gray-500 mt-1">
                                {result.camera_id || 'camera_1'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 bg-emerald-500/10 text-emerald-400 text-[10px] px-2 py-0.5 rounded-full border border-emerald-500/20 whitespace-nowrap">
                              <CheckCircle size={10} />
                              {Math.round((result.confidence || 0) * 100)}% Match
                            </div>
                          </div>

                          <div className="space-y-1">
                            <div className="flex items-center gap-2 text-sm text-gray-300">
                              <Clock size={14} className="text-gray-500" />
                              <span>Matched at: {Math.floor(result.matched_at_seconds || 0)}s</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-gray-300">
                              <MapPin size={14} className="text-gray-500" />
                              <span>Video contains the person</span>
                            </div>
                          </div>

                          <div className="w-full mt-2 py-1.5 bg-white/5 text-gray-300 text-xs rounded-lg text-center">
                            Playing inline in this card
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="glass-panel p-20 rounded-2xl flex flex-col items-center justify-center text-center text-gray-500"
              >
                <Search size={48} className="mb-4 opacity-20" />
                <h3 className="text-lg font-medium text-gray-400">No matches found</h3>
                <p className="max-w-xs text-sm">Upload a photo and start a search to see results here.</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default FaceSearchView;
