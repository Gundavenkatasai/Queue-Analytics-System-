import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { 
  BarChart2, 
  Calendar, 
  Video, 
  FileText, 
  Hexagon, 
  AlertCircle, 
  Settings,
  LogOut,
  Menu,
  Bell
} from 'lucide-react';

const TabNavigation = ({ children }) => {
  const [activeTab, setActiveTab] = useState('live');
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const { user, logout } = useAuth();

  const tabs = [
    { id: 'live', label: 'Live Feed', icon: <BarChart2 size={20} /> },
    { id: 'video', label: 'Recordings', icon: <Video size={20} /> },
    { id: 'heatmap', label: 'Heatmaps', icon: <Hexagon size={20} /> },
    { id: 'alerts', label: 'Alerts', icon: <AlertCircle size={20} /> },
    { id: 'reports', label: 'Analytics', icon: <FileText size={20} /> },
    { id: 'calendar', label: 'Calendar', icon: <Calendar size={20} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground selection:bg-primary/30">
      
      {/* Sidebar */}
      <motion.aside
        initial={{ width: 260 }}
        animate={{ width: isSidebarOpen ? 260 : 80 }}
        className="relative z-20 flex flex-col bg-card border-r border-white/5 shadow-2xl transition-all duration-300"
      >
        <div className="flex items-center justify-between p-6">
          <AnimatePresence>
            {isSidebarOpen && (
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex items-center space-x-3 overflow-hidden whitespace-nowrap"
              >
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
                  <Hexagon size={20} className="text-white" />
                </div>
                <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                  Aegis AI
                </span>
              </motion.div>
            )}
          </AnimatePresence>
          <button 
            onClick={() => setSidebarOpen(!isSidebarOpen)}
            className="p-2 rounded-lg hover:bg-white/5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <Menu size={20} className="text-gray-400" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1 scrollbar-hide">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group relative ${
                  isActive 
                    ? 'bg-primary/10 text-primary' 
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
              >
                {isActive && (
                  <motion.div 
                    layoutId="activeTabIndicator"
                    className="absolute left-0 w-1 h-8 bg-primary rounded-r-full" 
                  />
                )}
                <div className="min-w-[24px] flex justify-center">
                  {tab.icon}
                </div>
                <AnimatePresence>
                  {isSidebarOpen && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      className="ml-3 font-medium whitespace-nowrap overflow-hidden"
                    >
                      {tab.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            );
          })}
        </div>

        {/* User Profile Footer */}
        <div className="p-4 border-t border-white/5">
          <div className={`flex items-center ${isSidebarOpen ? 'justify-between' : 'justify-center'}`}>
            <AnimatePresence>
              {isSidebarOpen && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center space-x-3 overflow-hidden"
                >
                  <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-white font-bold shadow-md">
                    {user?.name?.charAt(0) || 'U'}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-white truncate max-w-[120px]">
                      {user?.name || 'User'}
                    </span>
                    <span className="text-xs text-gray-500 truncate max-w-[120px]">
                      {user?.role || 'Operator'}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <button 
              onClick={logout}
              className="p-2 text-gray-400 hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-destructive/50"
              title="Logout"
            >
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </motion.aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]">
        {/* Header */}
        <header className="h-20 flex items-center justify-between px-8 bg-background/80 backdrop-blur-xl border-b border-white/5 z-10">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold tracking-tight text-white capitalize">
              {tabs.find(t => t.id === activeTab)?.label}
            </h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="relative">
              <button className="p-2.5 bg-white/5 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors relative">
                <Bell size={20} />
                <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full animate-pulse"></span>
              </button>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-8 relative z-0">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {React.cloneElement(children, { activeTab })}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default TabNavigation;
