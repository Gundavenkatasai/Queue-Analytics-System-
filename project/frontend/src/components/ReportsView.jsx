import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart2, Download, FileText, Calendar, Camera, Check,
  Users, Clock, Activity, TrendingUp, ChevronRight, Loader
} from 'lucide-react';

const reportTemplates = [
  {
    id: 'daily',
    name: 'Daily Summary',
    description: 'Occupancy, queue, and wait time for a single day',
    metrics: ['Total People', 'Max Queue', 'Avg Wait Time', 'Occupancy %'],
    color: 'from-blue-500/20 to-primary/10',
    border: 'border-primary/30',
    textColor: 'text-primary',
  },
  {
    id: 'weekly',
    name: 'Weekly Analysis',
    description: 'Weekly trends and peak hour breakdowns',
    metrics: ['Daily Averages', 'Peak Hours', 'Occupancy Trends', 'Queue Patterns'],
    color: 'from-purple-500/20 to-violet-500/10',
    border: 'border-violet-500/30',
    textColor: 'text-violet-400',
  },
  {
    id: 'monthly',
    name: 'Monthly Report',
    description: 'Comprehensive monthly statistics and trend analysis',
    metrics: ['Monthly Totals', 'Daily Averages', 'Trend Analysis', 'Peak Days'],
    color: 'from-emerald-500/20 to-teal-500/10',
    border: 'border-emerald-500/30',
    textColor: 'text-emerald-400',
  },
  {
    id: 'custom',
    name: 'Custom Report',
    description: 'Define your own date range and metrics',
    metrics: ['Any Date Range', 'Selected Metrics', 'Multi-Camera', 'Export Options'],
    color: 'from-amber-500/20 to-orange-500/10',
    border: 'border-amber-500/30',
    textColor: 'text-amber-400',
  },
];

const savedReports = [
  { name: 'surveillance_report_daily_2025-05-11.pdf', type: 'Daily', date: 'May 11, 2025', size: '1.2 MB' },
  { name: 'surveillance_report_weekly_2025-05-11.pdf', type: 'Weekly', date: 'May 11, 2025', size: '3.4 MB' },
  { name: 'surveillance_report_monthly_2025-05-11.csv', type: 'Monthly', date: 'May 11, 2025', size: '0.8 MB' },
];

const previewStats = [
  { label: 'Total People Counted', value: '2,847', icon: <Users size={18} />, trend: '+12%' },
  { label: 'Average Queue Length', value: '5.3', icon: <Activity size={18} />, trend: '-3%' },
  { label: 'Max Wait Time', value: '487s', icon: <Clock size={18} />, trend: '+8%' },
  { label: 'Average Occupancy', value: '42.5%', icon: <TrendingUp size={18} />, trend: '+2%' },
];

const ReportsView = () => {
  const [reportType, setReportType] = useState('daily');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [cameraId, setCameraId] = useState('camera_1');
  const [generating, setGenerating] = useState(false);
  const [generatedFormat, setGeneratedFormat] = useState(null);

  const generateReport = async (format) => {
    setGenerating(true);
    setGeneratedFormat(format);
    await new Promise(resolve => setTimeout(resolve, 1500));
    setGenerating(false);
    setTimeout(() => setGeneratedFormat(null), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card/40 p-4 rounded-xl border border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart2 className="text-primary" />
            Analytics &amp; Reports
          </h2>
          <p className="text-sm text-gray-400 mt-1">Generate, preview, and export surveillance analytics reports.</p>
        </div>

        <div className="flex items-center gap-2 bg-black/40 p-2 rounded-lg border border-white/10">
          <Camera className="w-4 h-4 text-gray-400" />
          <select
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            className="bg-transparent text-white border-none focus:ring-0 text-sm appearance-none outline-none cursor-pointer"
          >
            <option value="camera_1" className="bg-background">Camera 1</option>
            <option value="camera_2" className="bg-background">Camera 2</option>
            <option value="camera_3" className="bg-background">Camera 3</option>
          </select>
        </div>
      </div>

      {/* Report Template Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {reportTemplates.map((template, i) => (
          <motion.button
            key={template.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            onClick={() => setReportType(template.id)}
            className={`text-left p-5 rounded-2xl border transition-all duration-200 bg-gradient-to-br ${template.color} ${
              reportType === template.id
                ? `${template.border} shadow-lg scale-[1.02]`
                : 'border-white/5 hover:border-white/10 hover:scale-[1.01]'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className={`font-bold ${reportType === template.id ? template.textColor : 'text-white'}`}>
                {template.name}
              </h3>
              {reportType === template.id && <Check size={16} className={template.textColor} />}
            </div>
            <p className="text-xs text-gray-400 mb-4">{template.description}</p>
            <ul className="space-y-1">
              {template.metrics.map((m) => (
                <li key={m} className="flex items-center gap-1.5 text-xs text-gray-500">
                  <ChevronRight size={12} className={template.textColor} />
                  {m}
                </li>
              ))}
            </ul>
          </motion.button>
        ))}
      </div>

      {/* Custom Date Range */}
      <AnimatePresence>
        {reportType === 'custom' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="glass-panel p-5 rounded-2xl grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Start Date</label>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="input-field py-2 text-sm [color-scheme:dark]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">End Date</label>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="input-field py-2 text-sm [color-scheme:dark]"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Preview */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 glass-panel rounded-2xl overflow-hidden"
        >
          <div className="p-5 border-b border-white/5 bg-black/20 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <FileText className="text-primary w-5 h-5" />
              Report Preview
            </h3>
            <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded-md capitalize">{reportType}</span>
          </div>

          <div className="p-6 space-y-6">
            {/* Key Metrics */}
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Summary Statistics</p>
              <div className="grid grid-cols-2 gap-3">
                {previewStats.map((stat) => (
                  <div key={stat.label} className="bg-black/30 p-4 rounded-xl border border-white/5 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">{stat.icon}</div>
                    <div>
                      <p className="text-xs text-gray-500">{stat.label}</p>
                      <div className="flex items-center gap-2">
                        <p className="text-lg font-bold text-white">{stat.value}</p>
                        <span className={`text-xs font-medium ${stat.trend.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                          {stat.trend}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Peak Hours */}
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Peak Hours</p>
              <div className="space-y-2">
                {[
                  { time: '09:00 – 11:00', load: 85, label: 'Peak', color: 'bg-red-500' },
                  { time: '12:00 – 14:00', load: 62, label: 'High', color: 'bg-amber-500' },
                  { time: '15:00 – 17:00', load: 45, label: 'Medium', color: 'bg-yellow-500' },
                  { time: '17:00 – 19:00', load: 28, label: 'Low', color: 'bg-emerald-500' },
                ].map((h) => (
                  <div key={h.time} className="flex items-center gap-3">
                    <span className="text-xs text-gray-400 w-28 flex-shrink-0">{h.time}</span>
                    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${h.load}%` }}
                        transition={{ delay: 0.2, duration: 0.6 }}
                        className={`h-full ${h.color} rounded-full`}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-16">{h.load} ppl/hr</span>
                    <span className="text-xs font-medium text-gray-400 w-14">{h.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">AI Recommendations</p>
              <div className="space-y-2">
                {[
                  'Increase staff during 09:00–11:00 peak hours',
                  'Monitor queue length closely during lunch hours',
                  'Optimise checkout process during peak times',
                  'Consider dynamic resource allocation for off-peak hours',
                ].map((rec, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <Check size={14} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                    {rec}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Export & Saved Reports */}
        <div className="space-y-5">
          {/* Export */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel p-6 rounded-2xl"
          >
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <Download className="text-primary w-5 h-5" />
              Export Report
            </h3>
            <div className="space-y-3">
              <button
                onClick={() => generateReport('pdf')}
                disabled={generating}
                className="btn-primary flex items-center justify-center gap-2 py-2.5 text-sm"
              >
                {generating && generatedFormat === 'pdf' ? (
                  <><Loader size={16} className="animate-spin" /> Generating PDF…</>
                ) : generatedFormat === 'pdf' ? (
                  <><Check size={16} /> PDF Ready!</>
                ) : (
                  <><FileText size={16} /> Export as PDF</>
                )}
              </button>
              <button
                onClick={() => generateReport('csv')}
                disabled={generating}
                className="btn-secondary flex items-center justify-center gap-2 py-2.5 text-sm"
              >
                {generating && generatedFormat === 'csv' ? (
                  <><Loader size={16} className="animate-spin" /> Generating CSV…</>
                ) : generatedFormat === 'csv' ? (
                  <><Check size={16} /> CSV Ready!</>
                ) : (
                  <><Download size={16} /> Export as CSV</>
                )}
              </button>
            </div>
          </motion.div>

          {/* Saved Reports */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-panel rounded-2xl overflow-hidden"
          >
            <div className="p-4 border-b border-white/5 bg-black/20">
              <h3 className="text-base font-semibold text-white">Saved Reports</h3>
            </div>
            <div className="p-2 space-y-1">
              {savedReports.map((r, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white font-medium truncate">{r.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{r.date} · {r.size}</p>
                  </div>
                  <button className="p-1.5 text-gray-500 hover:text-primary transition-colors opacity-0 group-hover:opacity-100">
                    <Download size={14} />
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default ReportsView;
