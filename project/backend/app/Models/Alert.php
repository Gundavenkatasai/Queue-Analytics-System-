<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class Alert extends Model
{
    protected $collection = 'alerts';

    protected $fillable = [
        'camera_id',
        'alert_type',
        'severity',
        'message',
        'people_count',
        'queue_length',
        'occupancy_percentage',
        'value',
        'threshold',
        'acknowledged',
    ];

    protected $casts = [
        'acknowledged' => 'boolean',
        'people_count' => 'integer',
        'queue_length' => 'integer',
        'occupancy_percentage' => 'float',
    ];

    public static function getUnacknowledgedAlerts($cameraId = 'camera_1')
    {
        return self::where('camera_id', $cameraId)
            ->where('acknowledged', false)
            ->orderBy('created_at', 'desc')
            ->get();
    }

    public static function getAllAlerts($cameraId = 'camera_1', $limit = 100)
    {
        return self::where('camera_id', $cameraId)
            ->orderBy('created_at', 'desc')
            ->limit($limit)
            ->get();
    }
}
