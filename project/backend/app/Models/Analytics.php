<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class Analytics extends Model
{
    protected $collection = 'analytics';

    protected $fillable = [
        'camera_id',
        'people_count',
        'queue_length',
        'entry_count',
        'exit_count',
        'average_wait_time',
        'max_wait_time',
        'occupancy_percentage',
        'heatmap_data',
        'frame_count',
        'timestamp',
    ];

    protected $casts = [
        'timestamp' => 'datetime',
        'heatmap_data' => 'array',
        'people_count' => 'integer',
        'queue_length' => 'integer',
        'entry_count' => 'integer',
        'exit_count' => 'integer',
        'average_wait_time' => 'float',
        'occupancy_percentage' => 'float',
        'frame_count' => 'integer',
    ];

    public static function getLatestStats($cameraId = 'camera_1')
    {
        return self::where('camera_id', $cameraId)
            ->latest('timestamp')
            ->first();
    }

    public static function getHistoricalData($cameraId = 'camera_1', $limit = 100)
    {
        return self::where('camera_id', $cameraId)
            ->orderBy('timestamp', 'desc')
            ->limit($limit)
            ->get()
            ->reverse();
    }

    public static function getTrendData($cameraId = 'camera_1', $hours = 24)
    {
        return self::where('camera_id', $cameraId)
            ->where('timestamp', '>=', now()->subHours($hours))
            ->orderBy('timestamp', 'asc')
            ->get();
    }
}
