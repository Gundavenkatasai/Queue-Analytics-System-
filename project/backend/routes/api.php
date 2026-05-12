<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AnalyticsController;
use App\Http\Controllers\AnalyticsTimelineController;
use App\Http\Controllers\RecordingsController;
use App\Http\Controllers\AlertsController;
use App\Http\Controllers\HeatmapController;
use App\Http\Controllers\HealthController;

Route::get('/health', [HealthController::class, 'health']);

Route::middleware('api')->group(function () {
    // Real-time Analytics Timeline (from ML Service)
    Route::post('/analytics/timeline', [AnalyticsTimelineController::class, 'storeTimeline']);
    Route::get('/analytics/live', [AnalyticsTimelineController::class, 'getLiveCount']);
    Route::get('/analytics/timeline', [AnalyticsTimelineController::class, 'getTimelineByDate']);

    // Analytics Features (6 core features)
    Route::get('/analytics/entry-exit', [AnalyticsTimelineController::class, 'getEntryExitAnalysis']);
    Route::get('/analytics/queue', [AnalyticsTimelineController::class, 'getQueueAnalysis']);
    Route::get('/analytics/occupancy', [AnalyticsTimelineController::class, 'getOccupancyAnalysis']);
    Route::get('/analytics/dwell-time', [AnalyticsTimelineController::class, 'getDwellTimeAnalysis']);
    Route::get('/analytics/peak-hours', [AnalyticsTimelineController::class, 'getPeakHoursAnalysis']);
    Route::get('/analytics/heatmap', [AnalyticsTimelineController::class, 'getHeatmapByDate']);

    // Legacy Analytics endpoints (backward compatibility)
    Route::post('/analytics', [AnalyticsController::class, 'store']);
    Route::get('/stats', [AnalyticsController::class, 'getLatestStats']);
    Route::get('/history', [AnalyticsController::class, 'getHistory']);
    Route::get('/trends', [AnalyticsController::class, 'getTrends']);

    // Recordings endpoints
    Route::post('/recordings', [RecordingsController::class, 'store']);
    Route::get('/recordings', [RecordingsController::class, 'index']);
    Route::get('/recordings/{id}', [RecordingsController::class, 'show']);
    Route::get('/recordings/{id}/stream', [RecordingsController::class, 'stream']);
    Route::delete('/recordings/{id}', [RecordingsController::class, 'destroy']);

    // Alerts endpoints
    Route::get('/alerts', [AlertsController::class, 'index']);
    Route::post('/alerts/create', [AlertsController::class, 'create']);
    Route::put('/alerts/{id}/acknowledge', [AlertsController::class, 'acknowledge']);
    Route::delete('/alerts/{id}', [AlertsController::class, 'destroy']);

    // Heatmap endpoints
    Route::post('/heatmap', [HeatmapController::class, 'store']);
    Route::get('/heatmap/{date}', [HeatmapController::class, 'getByDate']);
    Route::get('/heatmap/{date}/hour/{hour}', [HeatmapController::class, 'getByHour']);
});
