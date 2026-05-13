import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings, Camera, Target, AlertTriangle, Video, Database,
  Globe, Info, Save, RefreshCw, Check, Shield, Cpu
} from 'lucide-react';

const SectionCard = ({ icon, title, children, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="glass-panel p-6 rounded-2xl"
  >
    <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
      <span className="p-2 rounded-lg bg-primary/10 text-primary">{icon}</span>
      {title}
    </h3>
    {children}
  </motion.div>
);

const FieldGroup = ({ label, hint, children }) => (
  <div>
    <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">{label}</label>
    {children}
    {hint && <p className="text-xs text-gray-600 mt-1">{hint}</p>}
  </div>
);

const SettingsView = () => {
  const [settings, setSettings] = useState({
    cameraId: 'camera_1',
    cameraName: 'Main Entrance',
    resolution: '640x480',
    fps: 10,
    confidence: 0.45,
    maxPeople: 50,
    maxQueue: 10,
    maxWaitTime: 300,
    recordingEnabled: true,
    recordingDuration: 60,
    mongodbEnabled: true,
    retentionDays: 30,
    apiUrl: 'http://localhost:8000/api',
    sendInterval: 1,
    theme: 'dark',
  });
  const [saved, setSaved] = useState(false);

  const update = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    console.log('Saving settings:', settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleReset = () => window.location.reload();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="text-primary" />
            System Settings
          </h2>
          <p className="text-sm text-gray-400 mt-1">Configure camera, detection, recording, and integration options.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 text-sm transition-all"
          >
            <RefreshCw size={16} />
            Reset
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white text-sm font-medium transition-all active:scale-[0.98]"
          >
            <Save size={16} />
            Save Changes
          </button>
        </div>
      </div>

      {/* Save success toast */}
      <AnimatePresence>
        {saved && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-5 py-3 rounded-xl flex items-center gap-2 font-medium"
          >
            <Check size={18} />
            Settings saved successfully
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Camera Settings */}
        <SectionCard icon={<Camera size={18} />} title="Camera Settings" delay={0.05}>
          <div className="space-y-4">
            <FieldGroup label="Camera ID">
              <input
                type="text"
                value={settings.cameraId}
                disabled
                className="input-field opacity-50 cursor-not-allowed"
              />
            </FieldGroup>
            <FieldGroup label="Camera Name">
              <input
                type="text"
                value={settings.cameraName}
                onChange={(e) => update('cameraName', e.target.value)}
                className="input-field"
              />
            </FieldGroup>
            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label="Resolution">
                <select
                  value={settings.resolution}
                  onChange={(e) => update('resolution', e.target.value)}
                  className="input-field"
                >
                  <option value="320x240" className="bg-background">320×240 (Low)</option>
                  <option value="640x480" className="bg-background">640×480 (Medium)</option>
                  <option value="1280x720" className="bg-background">1280×720 (High)</option>
                  <option value="1920x1080" className="bg-background">1920×1080 (Full HD)</option>
                </select>
              </FieldGroup>
              <FieldGroup label="Frame Rate" hint="5 – 30 FPS">
                <input
                  type="number"
                  value={settings.fps}
                  onChange={(e) => update('fps', parseInt(e.target.value))}
                  min="5" max="30"
                  className="input-field"
                />
              </FieldGroup>
            </div>
          </div>
        </SectionCard>

        {/* Detection Settings */}
        <SectionCard icon={<Target size={18} />} title="Detection Settings" delay={0.1}>
          <div className="space-y-4">
            <FieldGroup label="YOLO Confidence Threshold" hint={`Current: ${settings.confidence}`}>
              <input
                type="range"
                min="0.1" max="0.9" step="0.01"
                value={settings.confidence}
                onChange={(e) => update('confidence', parseFloat(e.target.value))}
                className="w-full accent-primary"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.10 (Sensitive)</span>
                <span className="text-white font-medium">{settings.confidence}</span>
                <span>0.90 (Strict)</span>
              </div>
            </FieldGroup>
          </div>
        </SectionCard>

        {/* Alert Thresholds */}
        <SectionCard icon={<AlertTriangle size={18} />} title="Alert Thresholds" delay={0.15}>
          <div className="space-y-4">
            <FieldGroup label="Max Occupancy (people)">
              <div className="relative">
                <input
                  type="number"
                  value={settings.maxPeople}
                  onChange={(e) => update('maxPeople', parseInt(e.target.value))}
                  className="input-field pr-16"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-xs">people</span>
              </div>
            </FieldGroup>
            <FieldGroup label="Max Queue Length">
              <div className="relative">
                <input
                  type="number"
                  value={settings.maxQueue}
                  onChange={(e) => update('maxQueue', parseInt(e.target.value))}
                  className="input-field pr-16"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-xs">people</span>
              </div>
            </FieldGroup>
            <FieldGroup label="Max Wait Time">
              <div className="relative">
                <input
                  type="number"
                  value={settings.maxWaitTime}
                  onChange={(e) => update('maxWaitTime', parseInt(e.target.value))}
                  className="input-field pr-16"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-xs">seconds</span>
              </div>
            </FieldGroup>
          </div>
        </SectionCard>

        {/* Recording Settings */}
        <SectionCard icon={<Video size={18} />} title="Recording Settings" delay={0.2}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-black/20 rounded-xl border border-white/5">
              <div>
                <p className="text-sm font-medium text-white">Enable Recording</p>
                <p className="text-xs text-gray-500">Save video clips on event trigger</p>
              </div>
              <button
                onClick={() => update('recordingEnabled', !settings.recordingEnabled)}
                className={`w-11 h-6 rounded-full relative transition-all duration-200 ${settings.recordingEnabled ? 'bg-primary' : 'bg-white/10'}`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200 ${settings.recordingEnabled ? 'left-5' : 'left-0.5'}`} />
              </button>
            </div>
            <FieldGroup label="Clip Duration (seconds)" hint="60 seconds recommended">
              <input
                type="number"
                value={settings.recordingDuration}
                onChange={(e) => update('recordingDuration', parseInt(e.target.value))}
                disabled={!settings.recordingEnabled}
                className={`input-field ${!settings.recordingEnabled ? 'opacity-40 cursor-not-allowed' : ''}`}
              />
            </FieldGroup>
          </div>
        </SectionCard>

        {/* Database Settings */}
        <SectionCard icon={<Database size={18} />} title="Database Settings" delay={0.25}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-black/20 rounded-xl border border-white/5">
              <div>
                <p className="text-sm font-medium text-white">Enable MongoDB</p>
                <p className="text-xs text-gray-500">Store analytics in cloud database</p>
              </div>
              <button
                onClick={() => update('mongodbEnabled', !settings.mongodbEnabled)}
                className={`w-11 h-6 rounded-full relative transition-all duration-200 ${settings.mongodbEnabled ? 'bg-primary' : 'bg-white/10'}`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200 ${settings.mongodbEnabled ? 'left-5' : 'left-0.5'}`} />
              </button>
            </div>
            <FieldGroup label="Data Retention (days)">
              <input
                type="number"
                value={settings.retentionDays}
                onChange={(e) => update('retentionDays', parseInt(e.target.value))}
                disabled={!settings.mongodbEnabled}
                className={`input-field ${!settings.mongodbEnabled ? 'opacity-40 cursor-not-allowed' : ''}`}
              />
            </FieldGroup>
          </div>
        </SectionCard>

        {/* API Settings */}
        <SectionCard icon={<Globe size={18} />} title="API & Integration" delay={0.3}>
          <div className="space-y-4">
            <FieldGroup label="Backend API URL">
              <input
                type="text"
                value={settings.apiUrl}
                onChange={(e) => update('apiUrl', e.target.value)}
                className="input-field font-mono text-sm"
              />
            </FieldGroup>
            <FieldGroup label="Send Interval (seconds)" hint="1 – 10 seconds">
              <input
                type="number"
                value={settings.sendInterval}
                onChange={(e) => update('sendInterval', parseInt(e.target.value))}
                min="1" max="10"
                className="input-field"
              />
            </FieldGroup>
          </div>
        </SectionCard>
      </div>

      {/* System Info */}
      <SectionCard icon={<Info size={18} />} title="System Information" delay={0.35}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'System Version', value: '2.0.0', icon: <Cpu size={16} />, color: 'text-primary' },
            { label: 'ML Engine', value: 'YOLOv8m', icon: <Target size={16} />, color: 'text-yellow-400' },
            { label: 'API Status', value: '✓ Connected', icon: <Shield size={16} />, color: 'text-emerald-400' },
            { label: 'DB Status', value: '✓ Connected', icon: <Database size={16} />, color: 'text-emerald-400' },
          ].map((item) => (
            <div key={item.label} className="bg-black/20 p-4 rounded-xl border border-white/5">
              <div className={`flex items-center gap-2 mb-2 ${item.color}`}>
                {item.icon}
                <span className="text-xs text-gray-400">{item.label}</span>
              </div>
              <p className={`font-bold ${item.color}`}>{item.value}</p>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
};

export default SettingsView;
