<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Carbon\Carbon;
use DB;
use Log;
use Exception;

class AnalyticsTimelineController extends Controller
{
    protected $storage_file;
    protected $recordings_file;
    protected $mongodb_available = false;

    public function __construct()
    {
        $this->storage_file = storage_path('analytics_timeline.json');
        $this->recordings_file = storage_path('analytics_recordings.json');

        // Check MongoDB availability
        try {
            if (extension_loaded('mongodb')) {
                DB::connection('mongodb')->getSchemaBuilder()->getColumns('test');
                $this->mongodb_available = true;
            }
        } catch (Exception $e) {
            Log::warning('MongoDB unavailable, using file storage');
        }
    }

    /**
     * Store real-time analytics (from ML service)
     * Called at 15 FPS with detection results
     */
    public function storeTimeline(Request $request)
    {
        try {
            set_time_limit(300);

            $validated = $request->validate([
                'camera_id' => 'required|string',
                'timestamp' => 'required|string',
                'people_count' => 'required|integer|min:0',
                'occupancy_percentage' => 'required|numeric|min:0|max:100',
                'entry_count' => 'required|integer|min:0',
                'exit_count' => 'required|integer|min:0',
                'queue_detected' => 'required|boolean',
                'queue_length' => 'required|integer|min:0',
                'dwell_time_avg' => 'required|numeric|min:0',
                'dwell_time_max' => 'required|numeric|min:0',
                'peak_hours' => 'nullable|string',
                'heatmap_data' => 'nullable|string',
                'alert_status' => 'nullable|string|in:normal,high,critical'
            ]);

            $analytics = [
                'camera_id' => $validated['camera_id'],
                'timestamp' => $validated['timestamp'],
                'people_count' => $validated['people_count'],
                'occupancy_percentage' => $validated['occupancy_percentage'],
                'entry_count' => $validated['entry_count'],
                'exit_count' => $validated['exit_count'],
                'queue_detected' => $validated['queue_detected'],
                'queue_length' => $validated['queue_length'],
                'dwell_time_avg' => $validated['dwell_time_avg'],
                'dwell_time_max' => $validated['dwell_time_max'],
                'peak_hours' => $validated['peak_hours'] ? json_decode($validated['peak_hours'], true) : [],
                'heatmap' => $validated['heatmap_data'] ? json_decode($validated['heatmap_data'], true) : [],
                'alert_status' => $validated['alert_status'] ?? 'normal'
            ];

            // Try MongoDB first
            if ($this->mongodb_available) {
                try {
                    DB::connection('mongodb')
                        ->collection('analytics_timeline')
                        ->insert($analytics);

                    Log::info("Analytics stored in MongoDB: {$analytics['camera_id']}");
                } catch (Exception $e) {
                    Log::warning("MongoDB insert failed: {$e->getMessage()}");
                    $this->storeToFileBackup($analytics);
                }
            } else {
                $this->storeToFileBackup($analytics);
            }

            return response()->json([
                'success' => true,
                'message' => 'Analytics stored',
                'data' => $analytics
            ], 201);

        } catch (Exception $e) {
            Log::error("Analytics storage error: {$e->getMessage()}");
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get real-time person count (latest)
     */
    public function getLiveCount(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');

            if ($this->mongodb_available) {
                $record = DB::connection('mongodb')
                    ->collection('analytics_timeline')
                    ->where('camera_id', $camera_id)
                    ->orderBy('timestamp', -1)
                    ->first();
            } else {
                $record = $this->getLatestFromFile($camera_id);
            }

            if (!$record) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'people_count' => 0,
                    'occupancy_percentage' => 0,
                    'queue_detected' => false,
                    'alert_status' => 'normal'
                ]);
            }

            return response()->json([
                'camera_id' => $camera_id,
                'timestamp' => $record['timestamp'] ?? $record->timestamp ?? null,
                'people_count' => $record['people_count'] ?? 0,
                'occupancy_percentage' => $record['occupancy_percentage'] ?? 0,
                'entry_count' => $record['entry_count'] ?? 0,
                'exit_count' => $record['exit_count'] ?? 0,
                'queue_detected' => $record['queue_detected'] ?? false,
                'queue_length' => $record['queue_length'] ?? 0,
                'alert_status' => $record['alert_status'] ?? 'normal'
            ]);

        } catch (Exception $e) {
            Log::error("Live count error: {$e->getMessage()}");
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get timeline data for specific date
     */
    public function getTimelineByDate(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $start = Carbon::createFromFormat('Y-m-d', $date)->startOfDay();
            $end = Carbon::createFromFormat('Y-m-d', $date)->endOfDay();

            if ($this->mongodb_available) {
                $records = DB::connection('mongodb')
                    ->collection('analytics_timeline')
                    ->where('camera_id', $camera_id)
                    ->whereBetween('timestamp', [$start->toIso8601String(), $end->toIso8601String()])
                    ->orderBy('timestamp', 1)
                    ->get();
            } else {
                $records = $this->getFromFileByDate($camera_id, $date);
            }

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'count' => count($records),
                'data' => $records
            ]);

        } catch (Exception $e) {
            Log::error("Timeline by date error: {$e->getMessage()}");
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get entry/exit analysis
     */
    public function getEntryExitAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getFromFileByDate($camera_id, $date);

            if (!empty($records)) {
                $latest = end($records);
                $entry_count = $latest['entry_count'] ?? 0;
                $exit_count = $latest['exit_count'] ?? 0;
            } else {
                $entry_count = 0;
                $exit_count = 0;
            }

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'entry_count' => $entry_count,
                'exit_count' => $exit_count,
                'net_flow' => $entry_count - $exit_count,
                'type' => $entry_count > $exit_count ? 'influx' : ($exit_count > $entry_count ? 'outflow' : 'balanced')
            ]);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get queue detection history
     */
    public function getQueueAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getFromFileByDate($camera_id, $date);

            $queue_instances = [];
            $max_queue_length = 0;
            $total_queue_time = 0;
            $queue_detected_times = 0;

            foreach ($records as $record) {
                if ($record['queue_detected'] ?? false) {
                    $queue_detected_times++;
                    $queue_length = $record['queue_length'] ?? 0;
                    $max_queue_length = max($max_queue_length, $queue_length);

                    $queue_instances[] = [
                        'timestamp' => $record['timestamp'],
                        'queue_length' => $queue_length
                    ];
                }
            }

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'queue_detected_count' => $queue_detected_times,
                'max_queue_length' => $max_queue_length,
                'queue_percentage' => count($records) > 0 ? ($queue_detected_times / count($records)) * 100 : 0,
                'instances' => array_slice($queue_instances, -10)  // Last 10 instances
            ]);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get occupancy analysis
     */
    public function getOccupancyAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getFromFileByDate($camera_id, $date);

            if (empty($records)) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'date' => $date,
                    'avg_occupancy' => 0,
                    'max_occupancy' => 0,
                    'min_occupancy' => 0
                ]);
            }

            $occupancies = array_map(function ($r) {
                return $r['occupancy_percentage'] ?? 0;
            }, $records);

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'avg_occupancy' => round(array_sum($occupancies) / count($occupancies), 2),
                'max_occupancy' => max($occupancies),
                'min_occupancy' => min($occupancies),
                'max_people' => max(array_map(function ($r) {
                    return $r['people_count'] ?? 0; }, $records)),
                'timeline_data' => array_map(function ($r) {
                    return [
                        'timestamp' => $r['timestamp'],
                        'occupancy' => $r['occupancy_percentage'],
                        'people_count' => $r['people_count']
                    ];
                }, $records)
            ]);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get dwell time analysis
     */
    public function getDwellTimeAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getFromFileByDate($camera_id, $date);

            if (empty($records)) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'date' => $date,
                    'avg_dwell_time' => 0,
                    'max_dwell_time' => 0
                ]);
            }

            $dwell_times = array_map(function ($r) {
                return $r['dwell_time_avg'] ?? 0;
            }, $records);

            $max_dwell = array_map(function ($r) {
                return $r['dwell_time_max'] ?? 0;
            }, $records);

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'avg_dwell_time' => round(array_sum($dwell_times) / max(1, count($dwell_times)), 2),
                'max_dwell_time' => max($max_dwell),
                'data_points' => count($records)
            ]);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get peak hours analysis
     */
    public function getPeakHoursAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getFromFileByDate($camera_id, $date);

            $hourly_data = [];
            foreach ($records as $record) {
                if (!isset($record['peak_hours']) || empty($record['peak_hours'])) {
                    continue;
                }

                foreach ($record['peak_hours'] as $peak) {
                    $hour = $peak[0];
                    $count = $peak[1];

                    if (!isset($hourly_data[$hour])) {
                        $hourly_data[$hour] = [];
                    }
                    $hourly_data[$hour][] = $count;
                }
            }

            $peak_hours = [];
            foreach ($hourly_data as $hour => $counts) {
                $peak_hours[] = [
                    'hour' => $hour,
                    'avg_count' => round(array_sum($counts) / count($counts), 0)
                ];
            }

            usort($peak_hours, function ($a, $b) {
                return $b['avg_count'] <=> $a['avg_count'];
            });

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'peak_hours' => array_slice($peak_hours, 0, 5)
            ]);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get heatmap data
     */
    public function getHeatmapByDate(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getFromFileByDate($camera_id, $date);

            if (empty($records)) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'date' => $date,
                    'heatmap' => array_fill(0, 20, array_fill(0, 20, 0))
                ]);
            }

            $heatmap = array_fill(0, 20, array_fill(0, 20, 0));

            foreach ($records as $record) {
                if (!isset($record['heatmap']))
                    continue;

                $data = $record['heatmap'];
                if (is_string($data)) {
                    $data = json_decode($data, true);
                }

                if (is_array($data) && count($data) === 20) {
                    for ($i = 0; $i < 20; $i++) {
                        for ($j = 0; $j < 20; $j++) {
                            $heatmap[$i][$j] += $data[$i][$j] ?? 0;
                        }
                    }
                }
            }

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'heatmap' => $heatmap,
                'grid_size' => 20
            ]);

        } catch (Exception $e) {
            Log::error("Heatmap error: {$e->getMessage()}");
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    // Helper methods

    protected function storeToFileBackup($analytics)
    {
        try {
            $data = [];
            if (file_exists($this->storage_file)) {
                $content = file_get_contents($this->storage_file);
                $data = json_decode($content, true) ?? [];
            }

            $data[] = $analytics;

            // Keep only last 1000 records per camera
            $data = array_slice($data, -1000);

            file_put_contents($this->storage_file, json_encode($data, JSON_PRETTY_PRINT));
        } catch (Exception $e) {
            Log::error("File backup error: {$e->getMessage()}");
        }
    }

    protected function getLatestFromFile($camera_id)
    {
        try {
            if (!file_exists($this->storage_file)) {
                return null;
            }

            $content = file_get_contents($this->storage_file);
            $data = json_decode($content, true) ?? [];

            $filtered = array_filter($data, function ($record) use ($camera_id) {
                return ($record['camera_id'] ?? null) === $camera_id;
            });

            if (empty($filtered)) {
                return null;
            }

            return end($filtered);
        } catch (Exception $e) {
            Log::error("Get latest from file error: {$e->getMessage()}");
            return null;
        }
    }

    protected function getFromFileByDate($camera_id, $date)
    {
        try {
            if (!file_exists($this->storage_file)) {
                return [];
            }

            $content = file_get_contents($this->storage_file);
            $data = json_decode($content, true) ?? [];

            $start = Carbon::createFromFormat('Y-m-d', $date)->startOfDay()->toIso8601String();
            $end = Carbon::createFromFormat('Y-m-d', $date)->endOfDay()->toIso8601String();

            $filtered = array_filter($data, function ($record) use ($camera_id, $start, $end) {
                $ts = $record['timestamp'] ?? null;
                return ($record['camera_id'] ?? null) === $camera_id && $ts >= $start && $ts <= $end;
            });

            return array_values($filtered);
        } catch (Exception $e) {
            Log::error("Get from file by date error: {$e->getMessage()}");
            return [];
        }
    }
}
