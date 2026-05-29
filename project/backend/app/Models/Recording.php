<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class Recording extends Model
{
    protected $collection = 'recordings';

    protected $fillable = [
        'camera_id',
        'filename',
        'filepath',
        'cloud_url',
        'duration_seconds',
        'people_count',
        'file_size_bytes',
        'frame_count',
        'fps',
        'start_time',
        'end_time',
    ];

    protected $casts = [
        'duration_seconds' => 'integer',
        'people_count' => 'integer',
        'file_size_bytes' => 'integer',
        'frame_count' => 'integer',
        'fps' => 'integer',
        'start_time' => 'datetime',
        'end_time' => 'datetime',
    ];

    public static function getRecordingsByCamera($cameraId = 'camera_1', $limit = 50)
    {
        return self::where('camera_id', $cameraId)
            ->orderBy('created_at', 'desc')
            ->limit($limit)
            ->get();
    }

    public static function getTotalStorageUsed($cameraId = 'camera_1')
    {
        return self::where('camera_id', $cameraId)
            ->sum('file_size_bytes');
    }
}
