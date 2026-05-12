<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class HeatmapSnapshot extends Model
{
    protected $collection = 'heatmap_snapshots';

    protected $fillable = [
        'camera_id',
        'date',
        'hour',
        'heatmap_matrix',
    ];

    protected $casts = [
        'hour' => 'integer',
        'heatmap_matrix' => 'array',
    ];

    public static function getHeatmapByDate($date, $cameraId = 'camera_1')
    {
        return self::where('camera_id', $cameraId)
            ->where('date', $date)
            ->orderBy('hour', 'asc')
            ->get();
    }

    public static function getHeatmapByDateAndHour($date, $hour, $cameraId = 'camera_1')
    {
        return self::where('camera_id', $cameraId)
            ->where('date', $date)
            ->where('hour', $hour)
            ->first();
    }
}
