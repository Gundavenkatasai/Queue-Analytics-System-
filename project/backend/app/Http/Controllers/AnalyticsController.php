<?php

namespace App\Http\Controllers;

use App\Models\Analytics;
use App\Models\Alert;
use Illuminate\Http\Request;

class AnalyticsController extends Controller
{
    // Removed static $inMemoryData in favor of Laravel Cache

    public function store(Request $request)
    {
        try {
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

            $data = array_merge($validated, [
                'id' => uniqid(),
                'timestamp' => now()->toIso8601String(),
                'created_at' => now()->toIso8601String(),
            ]);

            // Try to save to database, but if it fails, keep in memory
            try {
                $analytics = Analytics::create($data);
            } catch (\Exception $dbError) {
                // MongoDB not available, use Cache for storage
                $inMemoryData = \Cache::get('in_memory_analytics', []);
                $inMemoryData[] = $data;
                // Keep only last 100 records in memory
                if (count($inMemoryData) > 100) {
                    array_shift($inMemoryData);
                }
                \Cache::put('in_memory_analytics', $inMemoryData);
                $analytics = (object)$data;
            }

            // Generate alerts if thresholds exceeded
            $this->checkAndCreateAlerts($validated);

            return response()->json([
                'status' => 'success',
                'message' => 'Analytics recorded',
                'data' => $analytics
            ], 201);

        } catch (\Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage()
            ], 400);
        }
    }

    public function getLatestStats(Request $request)
    {
        $cameraId = $request->query('camera_id', 'camera_1');
        
        try {
            $stats = Analytics::getLatestStats($cameraId);
        } catch (\Exception $e) {
            // MongoDB not available, return from Cache
            $stats = null;
            $inMemoryData = \Cache::get('in_memory_analytics', []);
            foreach (array_reverse($inMemoryData) as $record) {
                if ($record['camera_id'] === $cameraId) {
                    $stats = $record;
                    break;
                }
            }
        }

        if (!$stats) {
            // Return empty stats if no data yet
            return response()->json([
                'status' => 'success',
                'data' => [
                    'camera_id' => $cameraId,
                    'people_count' => 0,
                    'queue_length' => 0,
                    'average_wait_time' => 0,
                    'max_wait_time' => 0,
                    'occupancy_percentage' => 0,
                    'entry_count' => 0,
                    'exit_count' => 0,
                    'timestamp' => now()->toIso8601String(),
                ]
            ], 200);
        }

        return response()->json([
            'status' => 'success',
            'data' => $stats
        ], 200);
    }

    public function getHistory(Request $request)
    {
        $cameraId = $request->query('camera_id', 'camera_1');
        $limit = min($request->query('limit', 100), 500);

        try {
            $history = Analytics::getHistoricalData($cameraId, $limit);
        } catch (\Exception $e) {
            // MongoDB not available, return from Cache
            $inMemoryData = \Cache::get('in_memory_analytics', []);
            $history = array_filter($inMemoryData, function($record) use ($cameraId) {
                return $record['camera_id'] === $cameraId;
            });
            $history = array_slice(array_values($history), -$limit);
        }

        return response()->json([
            'status' => 'success',
            'count' => count($history),
            'data' => $history
        ], 200);
    }

    public function getTrends(Request $request)
    {
        $cameraId = $request->query('camera_id', 'camera_1');
        $hours = $request->query('hours', 24);

        try {
            $trends = Analytics::getTrendData($cameraId, $hours);
        } catch (\Exception $e) {
            // MongoDB not available, return from Cache
            $inMemoryData = \Cache::get('in_memory_analytics', []);
            $trends = array_filter($inMemoryData, function($record) use ($cameraId) {
                return $record['camera_id'] === $cameraId;
            });
            $trends = array_slice(array_values($trends), -50);
        }

        return response()->json([
            'status' => 'success',
            'count' => count($trends),
            'data' => $trends
        ], 200);
    }

    private function checkAndCreateAlerts($analytics)
    {
        $cameraId = $analytics['camera_id'];
        $queueLength = $analytics['queue_length'];
        $occupancyPercentage = $analytics['occupancy_percentage'];

        // Check queue overload
        if ($queueLength > 15) {
            try {
                Alert::create([
                    'camera_id' => $cameraId,
                    'alert_type' => 'queue_overload',
                    'severity' => $queueLength > 20 ? 'high' : 'medium',
                    'message' => "Queue length is high: {$queueLength} people",
                    'people_count' => $analytics['people_count'],
                    'queue_length' => $queueLength,
                    'occupancy_percentage' => $occupancyPercentage,
                    'acknowledged' => false,
                ]);
            } catch (\Exception $e) {
                // Ignore if database unavailable
            }
        }

        // Check overcrowding
        if ($occupancyPercentage > 80) {
            try {
                Alert::create([
                    'camera_id' => $cameraId,
                    'alert_type' => 'overcrowding',
                    'severity' => $occupancyPercentage > 95 ? 'high' : 'medium',
                    'message' => "Area is overcrowded: {$occupancyPercentage}% occupancy",
                    'people_count' => $analytics['people_count'],
                    'queue_length' => $queueLength,
                    'occupancy_percentage' => $occupancyPercentage,
                    'acknowledged' => false,
                ]);
            } catch (\Exception $e) {
                // Ignore if database unavailable
            }
        }
    }
}
