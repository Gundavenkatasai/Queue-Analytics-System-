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

        // Check MongoDB availability using a lightweight ping
        // TEMPORARILY DISABLED: IP whitelist issue is causing 30s hangs on single-threaded dev server
        // try {
        //     if (extension_loaded('mongodb')) {
        //         DB::connection('mongodb')->command(['ping' => 1]);
        //         $this->mongodb_available = true;
        //     }
        // } catch (Exception $e) {
        //     Log::warning('MongoDB unavailable, using file storage: ' . $e->getMessage());
        // }
        $this->mongodb_available = false;
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
                'queue_detected' => 'required',
                'queue_length' => 'required|integer|min:0',
                'dwell_time_avg' => 'required|numeric|min:0',
                'dwell_time_max' => 'required|numeric|min:0',
                'peak_hours' => 'nullable|string',
                'heatmap_data' => 'nullable|string',
                'session_id' => 'nullable|string',
                'alert_status' => 'nullable|string|in:normal,high,critical'
            ]);

            $cumulative = $this->updateCumulativeCounts($validated['camera_id'], $validated['entry_count'], $validated['exit_count']);

            $analytics = [
                'camera_id' => $validated['camera_id'],
                'timestamp' => $validated['timestamp'],
                'people_count' => (int) $validated['people_count'],
                'occupancy_percentage' => (float) $validated['occupancy_percentage'],
                'entry_count' => (int) $cumulative['entry_count'],
                'exit_count' => (int) $cumulative['exit_count'],
                'queue_detected' => filter_var($validated['queue_detected'], FILTER_VALIDATE_BOOLEAN),
                'queue_length' => (int) $validated['queue_length'],
                'dwell_time_avg' => (float) $validated['dwell_time_avg'],
                'dwell_time_max' => (float) $validated['dwell_time_max'],
                'peak_hours' => $validated['peak_hours'] ? json_decode($validated['peak_hours'], true) : [],
                'heatmap' => $validated['heatmap_data'] ? json_decode($validated['heatmap_data'], true) : [],
                'session_id' => $request->input('session_id', 'default_session'),
                'alert_status' => $validated['alert_status'] ?? 'normal'
            ];

            // Store in MongoDB if available
            if ($this->mongodb_available) {
                try {
                    // Update live active stats for the dashboard
                    DB::connection('mongodb')
                        ->collection('analytics_live')
                        ->update(
                            ['camera_id' => $analytics['camera_id']],
                            $analytics,
                            ['upsert' => true]
                        );

                    // Insert into timeline (historical)
                    DB::connection('mongodb')
                        ->collection('analytics_timeline')
                        ->insert($analytics);
                } catch (Exception $e) {
                    Log::warning("MongoDB storage failed, using file only: {$e->getMessage()}");
                }
            }

            // Always store in file backup for resilience
            $this->storeToFileBackup($analytics);

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
            // How old a record can be before it's considered stale (seconds)
            $freshness_threshold = 300; // 5 minutes — covers FFmpeg transcoding delays

            $record = null;

            // Always try file storage first (most reliable for real-time)
            $record = $this->getLatestFromFile($camera_id);

            // If no file record, try MongoDB as backup
            if (!$record && $this->mongodb_available) {
                try {
                    $record = DB::connection('mongodb')
                        ->collection('analytics_live')
                        ->where('camera_id', $camera_id)
                        ->first();
                } catch (Exception $e) {
                    Log::warning("MongoDB live count fetch failed: {$e->getMessage()}");
                }
            }

            // No record at all — return empty response
            if (!$record) {
                Log::warning("No record found for camera: {$camera_id}");
                $cumulative = $this->getCumulativeCounts($camera_id);
                return response()->json([
                    'camera_id' => $camera_id,
                    'people_count' => 0,
                    'occupancy_percentage' => 0,
                    'entry_count' => (int) $cumulative['entry_count'],
                    'exit_count' => (int) $cumulative['exit_count'],
                    'queue_detected' => false,
                    'queue_length' => 0,
                    'dwell_time_avg' => 0,
                    'dwell_time_max' => 0,
                    'alert_status' => 'normal',
                    'is_live' => false,
                    'data_age_seconds' => null,
                ]);
            }

            // Support both array and object access
            $get = function ($key, $default = null) use ($record) {
                if (is_array($record))
                    return $record[$key] ?? $default;
                return $record->{$key} ?? $default;
            };

            // ── Freshness check ─────────────────────────────────────────────
            $timestamp = $get('timestamp');
            $data_age_seconds = null;
            $is_live = false;

            if ($timestamp) {
                try {
                    $recorded_at = Carbon::parse($timestamp);
                    $now = Carbon::now('UTC');
                    // Use abs() to handle minor TZ differences between PHP and Python clocks
                    $data_age_seconds = (int) abs($recorded_at->diffInSeconds($now));
                    $is_live = $data_age_seconds <= $freshness_threshold;

                    Log::info("Freshness check: timestamp={$timestamp}, age={$data_age_seconds}s, is_live={$is_live}");
                } catch (Exception $e) {
                    Log::warning("Could not parse timestamp for freshness check: {$timestamp}, error: {$e->getMessage()}");
                    // If we can't parse, treat as live (optimistic)
                    $is_live = true;
                }
            }

            // ── Return current data regardless of freshness (UI decides) ─────
            $cumulative = $this->getCumulativeCounts($camera_id);
            return response()->json([
                'camera_id' => $camera_id,
                'timestamp' => $timestamp,
                'people_count' => (int) $get('people_count', 0),
                'occupancy_percentage' => (float) $get('occupancy_percentage', 0),
                'entry_count' => (int) $cumulative['entry_count'],
                'exit_count' => (int) $cumulative['exit_count'],
                'queue_detected' => (bool) $get('queue_detected', false),
                'queue_length' => (int) $get('queue_length', 0),
                'dwell_time_avg' => (float) $get('dwell_time_avg', 0),
                'dwell_time_max' => (float) $get('dwell_time_max', 0),
                'alert_status' => $get('alert_status', 'normal'),
                'is_live' => $is_live,
                'data_age_seconds' => $data_age_seconds,
            ]);

        } catch (Exception $e) {
            Log::error("Live count error: {$e->getMessage()}");
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Search for a person by face image (calls ML service)
     */
    public function faceSearch(Request $request)
    {
        try {
            $validated = $request->validate([
                'image' => 'required|string'
            ]);

            // Call ML Service API
            $ml_service_url = 'http://localhost:8001/api/face-search';

            $response = \Http::timeout(30)->post($ml_service_url, [
                'image' => $validated['image']
            ]);

            if ($response->successful()) {
                return response()->json($response->json());
            } else {
                return response()->json([
                    'status' => 'error',
                    'message' => 'ML Service error: ' . $response->body()
                ], $response->status());
            }

        } catch (Exception $e) {
            Log::error("Face search error: {$e->getMessage()}");
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

            $records = $this->getRecordsByDate($camera_id, $date);

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'count' => count($records),
                'data' => array_values($records)
            ]);

        } catch (Exception $e) {
            Log::error("Timeline by date error: {$e->getMessage()}");
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get entry/exit analysis — MongoDB first, file fallback
     */
    public function getEntryExitAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $today = Carbon::now()->format('Y-m-d');
            if ($date === $today) {
                $cumulative = $this->getCumulativeCounts($camera_id);
                $entry_count = (int) $cumulative['entry_count'];
                $exit_count = (int) $cumulative['exit_count'];
            } else {
                $records = $this->getRecordsByDate($camera_id, $date);

                if (!empty($records)) {
                    $latest = end($records);
                    $entry_count = $latest['entry_count'] ?? 0;
                    $exit_count = $latest['exit_count'] ?? 0;
                } else {
                    $entry_count = 0;
                    $exit_count = 0;
                }
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
     * Get queue detection history — MongoDB first, file fallback
     */
    public function getQueueAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getRecordsByDate($camera_id, $date);

            $queue_instances = [];
            $max_queue_length = 0;
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
                'instances' => array_slice($queue_instances, -10)
            ]);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Get occupancy analysis — MongoDB first, file fallback
     */
    public function getOccupancyAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getRecordsByDate($camera_id, $date);

            if (empty($records)) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'date' => $date,
                    'avg_occupancy' => 0,
                    'max_occupancy' => 0,
                    'min_occupancy' => 0,
                    'max_people' => 0,
                    'timeline_data' => []
                ]);
            }

            $occupancies = array_map(function ($r) {
                return (float) ($r['occupancy_percentage'] ?? 0);
            }, $records);

            return response()->json([
                'camera_id' => $camera_id,
                'date' => $date,
                'avg_occupancy' => round(array_sum($occupancies) / count($occupancies), 2),
                'max_occupancy' => max($occupancies),
                'min_occupancy' => min($occupancies),
                'max_people' => max(array_map(function ($r) {
                    return (int) ($r['people_count'] ?? 0);
                }, $records)),
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
     * Get dwell time analysis — MongoDB first, file fallback
     */
    public function getDwellTimeAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getRecordsByDate($camera_id, $date);

            if (empty($records)) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'date' => $date,
                    'avg_dwell_time' => 0,
                    'max_dwell_time' => 0,
                    'data_points' => 0
                ]);
            }

            $dwell_times = array_map(function ($r) {
                return (float) ($r['dwell_time_avg'] ?? 0);
            }, $records);

            $max_dwell = array_map(function ($r) {
                return (float) ($r['dwell_time_max'] ?? 0);
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
     * Get peak hours analysis — MongoDB first, file fallback
     */
    public function getPeakHoursAnalysis(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getRecordsByDate($camera_id, $date);

            // Build hourly aggregation from actual timestamps
            $hourly_data = [];
            foreach ($records as $record) {
                $ts = $record['timestamp'] ?? null;
                if (!$ts)
                    continue;

                try {
                    $hour = (int) Carbon::parse($ts)->format('G'); // 0-23
                } catch (Exception $e) {
                    continue;
                }

                if (!isset($hourly_data[$hour])) {
                    $hourly_data[$hour] = ['total' => 0, 'count' => 0];
                }
                $hourly_data[$hour]['total'] += (int) ($record['people_count'] ?? 0);
                $hourly_data[$hour]['count']++;
            }

            $peak_hours = [];
            foreach ($hourly_data as $hour => $data) {
                $peak_hours[] = [
                    'hour' => $hour,
                    'avg_count' => round($data['total'] / max(1, $data['count']), 0)
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
     * Get heatmap data — MongoDB first, file fallback
     */
    public function getHeatmapByDate(Request $request)
    {
        try {
            $camera_id = $request->query('camera_id', 'camera_1');
            $date = $request->query('date', Carbon::now()->format('Y-m-d'));

            $records = $this->getRecordsByDate($camera_id, $date);

            if (empty($records)) {
                return response()->json([
                    'camera_id' => $camera_id,
                    'date' => $date,
                    'heatmap' => array_fill(0, 20, array_fill(0, 20, 0)),
                    'grid_size' => 20
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
                        if (!is_array($data[$i]))
                            continue;
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

    // =======================================================================
    // Cumulative daily count state persistence
    // =======================================================================

    private function getCumulativeCounts($camera_id)
    {
        $file = storage_path('cumulative_counts.json');
        $today = Carbon::now()->format('Y-m-d');
        
        $data = [];
        if (file_exists($file)) {
            $content = @file_get_contents($file);
            $data = json_decode($content, true) ?? [];
        }
        
        if (!isset($data[$camera_id]) || !is_array($data[$camera_id]) || ($data[$camera_id]['date'] ?? '') !== $today) {
            $data[$camera_id] = [
                'date' => $today,
                'entry_count' => 0,
                'exit_count' => 0
            ];
            file_put_contents($file, json_encode($data, JSON_PRETTY_PRINT), LOCK_EX);
        }
        
        return $data[$camera_id];
    }
    
    private function updateCumulativeCounts($camera_id, $entry_count, $exit_count)
    {
        $file = storage_path('cumulative_counts.json');
        $today = Carbon::now()->format('Y-m-d');
        
        $data = [];
        if (file_exists($file)) {
            $content = @file_get_contents($file);
            $data = json_decode($content, true) ?? [];
        }
        
        if (!isset($data[$camera_id]) || !is_array($data[$camera_id]) || ($data[$camera_id]['date'] ?? '') !== $today) {
            $data[$camera_id] = [
                'date' => $today,
                'entry_count' => 0,
                'exit_count' => 0
            ];
        }
        
        $data[$camera_id]['entry_count'] = (int)$entry_count;
        $data[$camera_id]['exit_count'] = (int)$exit_count;
        
        file_put_contents($file, json_encode($data, JSON_PRETTY_PRINT), LOCK_EX);
        return $data[$camera_id];
    }

    // =======================================================================
    // Core helper — queries MongoDB first, falls back to file
    // =======================================================================

    /**
     * Get records by date — tries MongoDB first, then file backup
     */
    protected function getRecordsByDate($camera_id, $date)
    {
        $start = Carbon::createFromFormat('Y-m-d', $date)->startOfDay();
        $end = Carbon::createFromFormat('Y-m-d', $date)->endOfDay();

        // Try MongoDB first
        if ($this->mongodb_available) {
            try {
                $dbRecords = DB::connection('mongodb')
                    ->collection('analytics_timeline')
                    ->where('camera_id', $camera_id)
                    ->where('timestamp', '>=', $start->toIso8601String())
                    ->where('timestamp', '<=', $end->toIso8601String())
                    ->orderBy('timestamp', 1)
                    ->get();

                if ($dbRecords && count($dbRecords) > 0) {
                    return $dbRecords->toArray();
                }
            } catch (Exception $e) {
                Log::warning("MongoDB query failed for {$camera_id}/{$date}: {$e->getMessage()}");
            }
        }

        // Fallback to file storage
        return $this->getFromFileByDate($camera_id, $date);
    }

    // =======================================================================
    // File-based backup helpers
    // =======================================================================

    protected function storeToFileBackup($analytics)
    {
        try {
            $camera_id = $analytics['camera_id'] ?? 'camera_1';
            $date = Carbon::now()->format('Y-m-d');

            // 1. Write the latest record for real-time live polling (extremely fast, tiny file)
            $latest_file = storage_path("latest_{$camera_id}.json");
            file_put_contents($latest_file, json_encode($analytics, JSON_PRETTY_PRINT), LOCK_EX);

            // 2. Append to daily timeline file (fast, partitioned by day)
            $timeline_file = storage_path("timeline_{$camera_id}_{$date}.json");
            $data = [];
            if (file_exists($timeline_file)) {
                $content = @file_get_contents($timeline_file);
                if ($content) {
                    $data = json_decode($content, true) ?? [];
                }
            }

            $data[] = $analytics;

            // Keep only last 1000 records per daily file to avoid unbounded growth
            if (count($data) > 1000) {
                $data = array_slice($data, -1000);
            }

            file_put_contents($timeline_file, json_encode($data, JSON_PRETTY_PRINT), LOCK_EX);

        } catch (Exception $e) {
            Log::error("File backup error: {$e->getMessage()}");
        }
    }

    protected function getLatestFromFile($camera_id)
    {
        try {
            $latest_file = storage_path("latest_{$camera_id}.json");
            if (file_exists($latest_file)) {
                $content = @file_get_contents($latest_file);
                if ($content) {
                    $decoded = json_decode($content, true);
                    if ($decoded) {
                        return $decoded;
                    }
                }
            }

            // Fallback: search backwards in the legacy storage file if it exists
            return $this->getLatestFromBigFile($camera_id);
        } catch (Exception $e) {
            Log::error("Get latest from file error: {$e->getMessage()}");
            return null;
        }
    }

    protected function getLatestFromBigFile($camera_id)
    {
        try {
            if (!file_exists($this->storage_file)) {
                return null;
            }

            $content = @file_get_contents($this->storage_file);
            if (!$content) {
                return null;
            }

            $data = json_decode($content, true);
            if (!is_array($data) || empty($data)) {
                return null;
            }

            for ($i = count($data) - 1; $i >= 0; $i--) {
                $record = $data[$i];
                if (($record['camera_id'] ?? null) === $camera_id) {
                    return $record;
                }
            }
            return null;
        } catch (Exception $e) {
            Log::error("Get latest from big file error: {$e->getMessage()}");
            return null;
        }
    }

    protected function getFromFileByDate($camera_id, $date)
    {
        try {
            $timeline_file = storage_path("timeline_{$camera_id}_{$date}.json");
            if (file_exists($timeline_file)) {
                $content = @file_get_contents($timeline_file);
                if ($content) {
                    $decoded = json_decode($content, true);
                    if (is_array($decoded)) {
                        return $decoded;
                    }
                }
            }

            // Fallback: read from legacy big file
            return $this->getFromBigFileByDate($camera_id, $date);
        } catch (Exception $e) {
            Log::error("Get from file by date error: {$e->getMessage()}");
            return [];
        }
    }

    protected function getFromBigFileByDate($camera_id, $date)
    {
        try {
            if (!file_exists($this->storage_file)) {
                return [];
            }

            $content = @file_get_contents($this->storage_file);
            if (!$content) {
                return [];
            }

            $data = json_decode($content, true) ?? [];

            $start = Carbon::createFromFormat('Y-m-d', $date)->startOfDay()->toIso8601String();
            $end = Carbon::createFromFormat('Y-m-d', $date)->endOfDay()->toIso8601String();

            $filtered = array_filter($data, function ($record) use ($camera_id, $start, $end) {
                $ts = $record['timestamp'] ?? null;
                return ($record['camera_id'] ?? null) === $camera_id && $ts >= $start && $ts <= $end;
            });

            return array_values($filtered);
        } catch (Exception $e) {
            Log::error("Get from big file by date error: {$e->getMessage()}");
            return [];
        }
    }
}
