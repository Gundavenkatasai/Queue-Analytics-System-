<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

// Mock in-memory storage
$analytics_data = [];
$alerts_data = [];

Route::post('/analytics', function (Request $request) use (&$analytics_data) {
    $validated = $request->validate([
        'camera_id' => 'required|string',
        'people_count' => 'required|integer|min:0',
        'queue_length' => 'required|integer|min:0',
        'entry_count' => 'required|integer|min:0',
        'exit_count' => 'required|integer|min:0',
        'average_wait_time' => 'required|numeric|min:0',
        'max_wait_time' => 'nullable|numeric|min:0',
        'occupancy_percentage' => 'required|numeric|between:0,100',
        'heatmap_data' => 'nullable|array',
        'frame_count' => 'required|integer|min:0',
    ]);

    $record = array_merge($validated, [
        'id' => uniqid(),
        'timestamp' => now()->toIso8601String(),
        'created_at' => now()->toIso8601String(),
    ]);

    $analytics_data[] = $record;
    if (count($analytics_data) > 500) {
        array_shift($analytics_data);
    }

    return response()->json([
        'status' => 'success',
        'message' => 'Analytics recorded',
        'data' => $record
    ], 201);
});

Route::get('/stats', function (Request $request) use ($analytics_data) {
    $cameraId = $request->query('camera_id', 'camera_1');

    // Get latest stat for camera
    $latest = null;
    foreach (array_reverse($analytics_data) as $record) {
        if ($record['camera_id'] === $cameraId) {
            $latest = $record;
            break;
        }
    }

    if ($latest) {
        return response()->json([
            'status' => 'success',
            'data' => $latest
        ], 200);
    }

    // Return mock data
    return response()->json([
        'status' => 'success',
        'data' => [
            'camera_id' => $cameraId,
            'people_count' => rand(0, 20),
            'queue_length' => rand(0, 10),
            'average_wait_time' => rand(0, 30),
            'max_wait_time' => rand(0, 60),
            'occupancy_percentage' => rand(0, 100),
            'entry_count' => rand(0, 100),
            'exit_count' => rand(0, 100),
            'timestamp' => now()->toIso8601String(),
        ]
    ], 200);
});

Route::get('/history', function (Request $request) use ($analytics_data) {
    $cameraId = $request->query('camera_id', 'camera_1');
    $limit = min($request->query('limit', 100), 500);

    $history = array_filter($analytics_data, function ($record) use ($cameraId) {
        return $record['camera_id'] === $cameraId;
    });

    return response()->json([
        'status' => 'success',
        'count' => count($history),
        'data' => array_slice(array_values($history), -$limit)
    ], 200);
});

Route::get('/trends', function (Request $request) use ($analytics_data) {
    $cameraId = $request->query('camera_id', 'camera_1');
    $hours = $request->query('hours', 24);

    $trends = array_filter($analytics_data, function ($record) use ($cameraId) {
        return $record['camera_id'] === $cameraId;
    });

    return response()->json([
        'status' => 'success',
        'count' => count($trends),
        'data' => array_slice(array_values($trends), -50)
    ], 200);
});

Route::get('/health', function () {
    return response()->json([
        'status' => 'ok',
        'message' => 'API is running',
        'timestamp' => now()->toIso8601String()
    ], 200);
});
