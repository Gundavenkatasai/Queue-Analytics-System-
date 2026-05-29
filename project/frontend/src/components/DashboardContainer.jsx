/**
 * DashboardContainer - Routes between different dashboard views based on active tab
 */

import React from 'react';
import Dashboard from './Dashboard';
import CalendarView from './CalendarView';
import VideoPlayer from './VideoPlayer';
import ReportsView from './ReportsView';
import HeatmapView from './HeatmapView';
import AlertsView from './AlertsView';
import SettingsView from './SettingsView';
import FaceSearchView from './FaceSearchView';

const DashboardContainer = ({ activeTab }) => {
    const renderView = () => {
        switch (activeTab) {
            case 'live':
                return <Dashboard />;
            case 'calendar':
                return <CalendarView />;
            case 'video':
                return <VideoPlayer />;
            case 'reports':
                return <ReportsView />;
            case 'heatmap':
                return <HeatmapView />;
            case 'alerts':
                return <AlertsView />;
            case 'settings':
                return <SettingsView />;
            case 'search':
                return <FaceSearchView />;
            default:
                return <Dashboard />;
        }
    };

    return (
        <div style={{ width: '100%', height: '100%' }}>
            {renderView()}
        </div>
    );
};

export default DashboardContainer;
