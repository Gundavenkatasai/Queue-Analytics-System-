import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { Toaster } from 'react-hot-toast';

import Login from './pages/Login';
import Signup from './pages/Signup';
import TabNavigation from './components/TabNavigation';
import DashboardContainer from './components/DashboardContainer';

import './App.css';

const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" />;
  }
  return children;
};

function App() {
  return (
    <div className="App bg-background text-foreground min-h-screen font-sans">
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        
        {/* Protected Dashboard Route */}
        <Route 
          path="/*" 
          element={
            <ProtectedRoute>
              <TabNavigation>
                <DashboardContainer />
              </TabNavigation>
            </ProtectedRoute>
          } 
        />
      </Routes>
    </div>
  );
}

export default App;
