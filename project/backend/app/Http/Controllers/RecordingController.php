<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Recording;
use App\Models\AnalyticsTimeline;
use Carbon\Carbon;

class RecordingController extends Controller
{
    /**
     * Get recordings list for a specific date
     * GET /api/recordings?camera_id=x&date=YYYY-MM-DD
     */
    public function listRecordingsByDate(Request $request)
    {
        try {
            $cameraId = $request->query('camera_id', 'camera_1');
            $date = $request->query('date');

            if (!$date) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Date parameter required (YYYY-MM-DD format)',
                ], 400);
            }

            // Validate date format
            try {
                Carbon::createFromFormat('Y-m-d', $date);
            } catch (\Exception $e) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Invalid date format. Use YYYY-MM-DD',
                ], 400);
            }

            $recordings = Recording::getRecordingsByDate($cameraId, $date);

            return response()->json([
                'status' => 'success',
                'camera_id' => $cameraId,
                'date' => $date,
                'count' => $recordings->count(),
                'data' => $recordings->map(fn($r) => [
                    'id' => $r->_id,
                    'filename' => $r->filename,
                    'start_time' => $r->start_time->toIso8601String(),
                    'end_time' => $r->end_time->toIso8601String(),
                    'duration_seconds' => $r->duration_seconds,
                    'file_size_bytes' => $r->file_size_bytes,
                    'frame_count' => $r->frame_count,
                    'fps' => $r->fps,
                    'codec' => $r->codec,
                    'resolution' => $r->resolution,
                    'is_uploaded' => $r->is_uploaded,
                ])->values(),
            ], 200);

        } catch (\Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Stream video recording with range request support
     * GET /api/recordings/{recording_id}/stream
     */
    public function streamRecording($recordingId)
    {
        try {
            $recording = Recording::find($recordingId);

            if (!$recording) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Recording not found',
                ], 404);
            }

            // Check if file exists locally
            if (file_exists($recording->filepath)) {
                $filePath = $recording->filepath;
            } elseif ($recording->mongodb_file_id) {
                // TODO: Stream from MongoDB GridFS
                return response()->json([
                    'status' => 'error',
                    'message' => 'Recording stored in MongoDB. GridFS streaming coming soon.',
                ], 501);
            } else {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Recording file not found',
                ], 404);
            }

            // Handle range requests for seeking
            $fileSize = filesize($filePath);
            $start = 0;
            $end = $fileSize - 1;

            if (isset($_SERVER['HTTP_RANGE'])) {
                if (preg_match('/bytes=(\d+)-(\d*)/', $_SERVER['HTTP_RANGE'], $matches)) {
                    $start = intval($matches[1]);
                    $end = $matches[2] !== '' ? intval($matches[2]) : $end;
                }
            }

            $headers = [
                'Content-Type' => 'video/mp4',
                'Content-Length' => ($end - $start + 1),
                'Accept-Ranges' => 'bytes',
                'Content-Disposition' => 'inline; filename="' . $recording->filename . '"',
            ];

            if (isset($_SERVER['HTTP_RANGE'])) {
                $headers['Content-Range'] = "bytes $start-$end/$fileSize";
                $headers['HTTP/1.1 206 Partial Content'] = true;
            }

            $handle = fopen($filePath, 'r');
            fseek($handle, $start);
            $length = $end - $start + 1;

            return response()->stream(
                function () use ($handle, $length) {
                    $chunkSize = 1024 * 1024; // 1MB chunks
                    while ($length > 0 && !feof($handle)) {
                        $chunk = fread($handle, min($chunkSize, $length));
                        echo $chunk;
                        $length -= strlen($chunk);
                    }
                    fclose($handle);
                },
                isset($_SERVER['HTTP_RANGE']) ? 206 : 200,
                $headers
            );

        } catch (\Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get recording metadata by ID
     * GET /api/recordings/{recording_id}/info
     */
    public function getRecordingInfo($recordingId)
    {
        try {
            $recording = Recording::find($recordingId);

            if (!$recording) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Recording not found',
                ], 404);
            }

            return response()->json([
                'status' => 'success',
                'data' => [
                    'id' => $recording->_id,
                    'camera_id' => $recording->camera_id,
                    'filename' => $recording->filename,
                    'start_time' => $recording->start_time->toIso8601String(),
                    'end_time' => $recording->end_time->toIso8601String(),
                    'duration_seconds' => $recording->duration_seconds,
                    'file_size_bytes' => $recording->file_size_bytes,
                    'frame_count' => $recording->frame_count,
                    'fps' => $recording->fps,
                    'codec' => $recording->codec,
                    'resolution' => $recording->resolution,
                    'bitrate' => $recording->bitrate,
                    'is_uploaded' => $recording->is_uploaded,
                    'upload_status' => $recording->upload_status,
                    'created_at' => $recording->created_at->toIso8601String(),
                ],
            ], 200);

        } catch (\Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get storage statistics
     * GET /api/recordings/stats/{camera_id}
     */
    public function getStorageStats($cameraId)
    {
        try {
            $totalStorage = Recording::getTotalStorageUsed($cameraId);
            $storageLastMonth = Recording::getStorageUsedInDays($cameraId, 30);
            $recordingCount = Recording::where('camera_id', $cameraId)->count();
            $uploadedCount = Recording::where('camera_id', $cameraId)->where('is_uploaded', true)->count();

            return response()->json([
                'status' => 'success',
                'camera_id' => $cameraId,
                'stats' => [
                    'total_storage_bytes' => $totalStorage,
                    'total_storage_gb' => round($totalStorage / (1024 * 1024 * 1024), 2),
                    'storage_last_30_days_gb' => round($storageLastMonth / (1024 * 1024 * 1024), 2),
                    'total_recordings' => $recordingCount,
                    'uploaded_recordings' => $uploadedCount,
                    'pending_uploads' => $recordingCount - $uploadedCount,
                ],
            ], 200);

        } catch (\Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage(),
            ], 500);
        }
    }
}
