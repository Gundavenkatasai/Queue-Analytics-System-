<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;
use Carbon\Carbon;

class AnalyticsTimeline extends Model
{
    protected $collection = 'analytics_timeline';

    protected $fillable = [
        'camera_id',
        'frame_id',
        'people_count',
        'queue_length',
        'entry_count',
        'exit_count',
        'average_wait_time',
        'max_wait_time',
        'occupancy_percentage',
        'heatmap_data',
        'detected_boxes',
        'confidence_score',
        'timestamp',
        'frame_timestamp',
    ];

    protected $casts = [
        'people_count' => 'integer',
        'queue_length' => 'integer',
        'entry_count' => 'integer',
        'exit_count' => 'integer',
        'average_wait_time' => 'float',
        'max_wait_time' => 'float',
        'occupancy_percentage' => 'float',
        'heatmap_data' => 'array',
        'detected_boxes' => 'array',
        'confidence_score' => 'float',
        'timestamp' => 'datetime',
        'frame_timestamp' => 'datetime',
    ];

    /**
     * Get all analytics for a specific date
     */
    public static function getTimelineByDate($cameraId, $date)
    {
        $startOfDay = Carbon::createFromFormat('Y-m-d', $date)->startOfDay();
        $endOfDay = Carbon::createFromFormat('Y-m-d', $date)->endOfDay();

        return self::where('camera_id', $cameraId)
            ->whereBetween('timestamp', [$startOfDay, $endOfDay])
            ->orderBy('timestamp', 'asc')
            ->get();
    }

    /**
     * Get analytics for a time range
     */
    public static function getTimelineByRange($cameraId, $startTime, $endTime)
    {
        return self::where('camera_id', $cameraId)
            ->whereBetween('timestamp', [$startTime, $endTime])
            ->orderBy('timestamp', 'asc')
            ->get();
    }

    /**
     * Get latest N records for a camera
     */
    public static function getLatest($cameraId, $limit = 100)
    {
        return self::where('camera_id', $cameraId)
            ->orderBy('timestamp', 'desc')
            ->limit($limit)
            ->get()
            ->reverse()
            ->values();
    }

    /**
     * Get hourly aggregates for a date
     */
    public static function getHourlyAggregates($cameraId, $date)
    {
        $data = self::getTimelineByDate($cameraId, $date);

        $hourly = [];
        foreach ($data as $record) {
            $hour = $record->timestamp->format('H:00');
            if (!isset($hourly[$hour])) {
                $hourly[$hour] = [
                    'hour' => $hour,
                    'people_count_avg' => 0,
                    'queue_length_avg' => 0,
                    'occupancy_avg' => 0,
                    'entries_total' => 0,
                    'exits_total' => 0,
                    'max_people' => 0,
                    'count' => 0,
                ];
            }

            $hourly[$hour]['people_count_avg'] += $record->people_count;
            $hourly[$hour]['queue_length_avg'] += $record->queue_length;
            $hourly[$hour]['occupancy_avg'] += $record->occupancy_percentage;
            $hourly[$hour]['entries_total'] += $record->entry_count;
            $hourly[$hour]['exits_total'] += $record->exit_count;
            $hourly[$hour]['max_people'] = max($hourly[$hour]['max_people'], $record->people_count);
            $hourly[$hour]['count']++;
        }

        // Calculate averages
        foreach ($hourly as &$hour) {
            if ($hour['count'] > 0) {
                $hour['people_count_avg'] = round($hour['people_count_avg'] / $hour['count'], 2);
                $hour['queue_length_avg'] = round($hour['queue_length_avg'] / $hour['count'], 2);
                $hour['occupancy_avg'] = round($hour['occupancy_avg'] / $hour['count'], 2);
            }
            unset($hour['count']);
        }

        return $hourly;
    }

    /**
     * Get daily summary for a date
     */
    public static function getDailySummary($cameraId, $date)
    {
        $data = self::getTimelineByDate($cameraId, $date);

        if ($data->isEmpty()) {
            return null;
        }

        $summary = [
            'date' => $date,
            'camera_id' => $cameraId,
            'data_points' => $data->count(),
            'people_count_avg' => round($data->avg('people_count'), 2),
            'people_count_max' => $data->max('people_count'),
            'people_count_min' => $data->min('people_count'),
            'queue_length_avg' => round($data->avg('queue_length'), 2),
            'queue_length_max' => $data->max('queue_length'),
            'queue_length_min' => $data->min('queue_length'),
            'total_entries' => $data->sum('entry_count'),
            'total_exits' => $data->sum('exit_count'),
            'occupancy_avg' => round($data->avg('occupancy_percentage'), 2),
            'occupancy_max' => $data->max('occupancy_percentage'),
            'first_record_time' => $data->first()->timestamp,
            'last_record_time' => $data->last()->timestamp,
        ];

        return $summary;
    }

    /**
     * Get heatmap aggregates for a date
     */
    public static function getHeatmapByDate($cameraId, $date)
    {
        $data = self::getTimelineByDate($cameraId, $date);

        if ($data->isEmpty()) {
            return null;
        }

        // Initialize 20x20 grid
        $grid = [];
        for ($i = 0; $i < 20; $i++) {
            for ($j = 0; $j < 20; $j++) {
                $grid[$i][$j] = 0;
            }
        }

        // Aggregate heatmap data
        foreach ($data as $record) {
            if ($record->heatmap_data && is_array($record->heatmap_data)) {
                foreach ($record->heatmap_data as $cell => $count) {
                    if (isset($grid[$cell['x']][$cell['y']])) {
                        $grid[$cell['x']][$cell['y']] += $count;
                    }
                }
            }
        }

        return [
            'date' => $date,
            'camera_id' => $cameraId,
            'grid' => $grid,
            'grid_size' => 20,
            'data_points' => $data->count(),
        ];
    }

    /**
     * Clean up old data (retention policy: 30 days)
     */
    public static function cleanupOldData($daysToKeep = 30)
    {
        $cutoffDate = Carbon::now()->subDays($daysToKeep);
        return self::where('timestamp', '<', $cutoffDate)->delete();
    }
}
