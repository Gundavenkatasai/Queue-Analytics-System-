<?php

namespace App\Http\Controllers;

use App\Models\Recording;
use Illuminate\Http\Request;
use Storage;
use Carbon\Carbon;

class RecordingsController extends Controller
{
    public function index(Request $request)
    {
        $cameraId = $request->query('camera_id', 'camera_1');
        $date     = $request->query('date'); // optional YYYY-MM-DD
        $limit    = min($request->query('limit', 50), 200);

        try {
            $query = Recording::where('camera_id', $cameraId);

            if ($date) {
                $start = \Carbon\Carbon::createFromFormat('Y-m-d', $date)->startOfDay();
                $end   = \Carbon\Carbon::createFromFormat('Y-m-d', $date)->endOfDay();
                $query->whereBetween('start_time', [$start, $end]);
            }

            $recordings = $query->orderBy('start_time', 'desc')->limit($limit)->get();
        } catch (\Exception $e) {
            // ── Fallback: read from ML-service local JSON file ──────────────
            $jsonPath   = base_path('../ml-service/storage/analytics_recordings.json');
            $recordings = [];

            if (file_exists($jsonPath)) {
                $all = json_decode(file_get_contents($jsonPath), true) ?? [];

                foreach ($all as $r) {
                    if (($r['camera_id'] ?? '') !== $cameraId) continue;

                    if ($date) {
                        $recDate = substr($r['start_time'] ?? '', 0, 10);
                        if ($recDate !== $date) continue;
                    }

                    $recordings[] = [
                        'id'               => md5($r['filename']),
                        'filename'         => $r['filename'],
                        'camera_id'        => $r['camera_id'],
                        'start_time'       => $r['start_time'],
                        'end_time'         => $r['end_time'],
                        'duration_seconds' => (int) ($r['duration'] ?? 0),
                        'file_size_bytes'  => (int) ($r['file_size'] ?? 0),
                        'frame_count'      => (int) ($r['frames'] ?? 0),
                        'filepath'         => base_path('../ml-service/storage/videos/' . $r['filename']),
                    ];
                }

                // newest first, trim to limit
                $recordings = array_reverse(array_slice($recordings, -$limit));
            } else {
                // in-memory cache last resort
                $all = \Cache::get('in_memory_recordings', []);
                $recordings = array_filter($all, fn($r) => $r['camera_id'] === $cameraId);
                $recordings = array_slice(array_values($recordings), -$limit);
            }
        }

        return response()->json([
            'status' => 'success',
            'count'  => count($recordings),
            'data'   => $recordings
        ], 200);
    }

    public function show(Request $request, $id)
    {
        $recording = Recording::find($id);

        if (!$recording) {
            return response()->json([
                'status' => 'error',
                'message' => 'Recording not found'
            ], 404);
        }

        return response()->json([
            'status' => 'success',
            'data' => $recording
        ], 200);
    }

    public function store(Request $request)
    {
        try {
            $validated = $request->validate([
                'camera_id' => 'required|string',
                'filename' => 'required|string',
                'filepath' => 'required|string',
                'duration_seconds' => 'required|integer|min:0',
                'people_count' => 'required|integer|min:0',
                'file_size_bytes' => 'required|integer|min:0',
                'frame_count' => 'required|integer|min:0',
                'fps' => 'nullable|integer|min:1',
            ]);

            $recording = Recording::create($validated);

            return response()->json([
                'status' => 'success',
                'message' => 'Recording metadata stored',
                'data' => $recording
            ], 201);

        } catch (\Exception $e) {
            // Check if it's a validation error or MongoDB error
            if ($e instanceof \Illuminate\Validation\ValidationException) {
                return response()->json([
                    'status' => 'error',
                    'message' => $e->getMessage()
                ], 400);
            }

            // MongoDB not available, use Cache
            $validated['id'] = uniqid();
            $validated['created_at'] = now()->toIso8601String();
            $inMemory = \Cache::get('in_memory_recordings', []);
            $inMemory[] = $validated;
            if (count($inMemory) > 50) array_shift($inMemory);
            \Cache::put('in_memory_recordings', $inMemory);

            return response()->json([
                'status' => 'success',
                'message' => 'Recording metadata stored (cached)',
                'data' => $validated
            ], 201);
        }
    }

    public function destroy(Request $request, $id)
    {
        $recording = Recording::find($id);

        if (!$recording) {
            return response()->json([
                'status' => 'error',
                'message' => 'Recording not found'
            ], 404);
        }

        // Delete physical file if exists
        if (file_exists($recording->filepath)) {
            unlink($recording->filepath);
        }

        $recording->delete();

        return response()->json([
            'status' => 'success',
            'message' => 'Recording deleted'
        ], 200);
    }

    public function stream(Request $request, $id)
    {
        $filepath = null;

        try {
            $recording = Recording::find($id);
            if ($recording) {
                $filepath = $recording->filepath;
            }
        } catch (\Exception $e) {
            // fall through to JSON lookup
        }

        // JSON file fallback lookup by md5 id
        if (!$filepath) {
            $jsonPath = base_path('../ml-service/storage/analytics_recordings.json');
            if (file_exists($jsonPath)) {
                $all = json_decode(file_get_contents($jsonPath), true) ?? [];
                foreach ($all as $r) {
                    if (md5($r['filename']) === $id) {
                        $filepath = base_path('../ml-service/storage/videos/' . $r['filename']);
                        break;
                    }
                }
            }
        }

        // In-memory cache fallback
        if (!$filepath) {
            $allRecordings = \Cache::get('in_memory_recordings', []);
            foreach ($allRecordings as $r) {
                if (($r['_id'] ?? $r['id'] ?? '') == $id) {
                    $filepath = $r['filepath'] ?? null;
                    break;
                }
            }
        }

        if (!$filepath || !file_exists($filepath)) {
            return response()->json([
                'status'  => 'error',
                'message' => 'Recording not found'
            ], 404);
        }

        // Try FFmpeg transcoding first — handles mp4v files that browsers can't play
        $ffmpeg = $this->findFfmpeg();
        if ($ffmpeg) {
            return $this->streamWithFfmpeg($filepath, $ffmpeg);
        }

        // FFmpeg not available → serve file directly with range-request support
        return $this->streamVideoFile($filepath);
    }

    /**
     * Find FFmpeg executable on common Windows/Linux install paths.
     */
    private function findFfmpeg(): ?string
    {
        $candidates = [
            'ffmpeg',
            'C:\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe',
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
        ];

        foreach ($candidates as $cmd) {
            $out  = [];
            $code = -1;
            // Use full shell quoting on Windows paths that contain spaces
            @exec('"' . $cmd . '" -version 2>&1', $out, $code);
            if ($code === 0) {
                return $cmd;
            }
        }

        return null;
    }

    /**
     * Stream a video through FFmpeg → H.264 fragmented MP4.
     * Fragmented MP4 (frag_keyframe+empty_moov) does NOT need a Content-Length,
     * which makes it perfect for pipe-based streaming to the browser.
     */
    private function streamWithFfmpeg(string $filepath, string $ffmpeg)
    {
        $devNull = PHP_OS_FAMILY === 'Windows' ? 'NUL' : '/dev/null';

        // Build the command.  We quote the ffmpeg path because it may contain spaces.
        $cmd = '"' . $ffmpeg . '"'
             . ' -y -i ' . escapeshellarg($filepath)
             . ' -c:v libx264 -preset ultrafast -tune zerolatency -crf 23'
             . ' -movflags frag_keyframe+empty_moov+default_base_moof'
             . ' -f mp4 pipe:1'
             . ' 2>' . $devNull;

        return response()->stream(
            function () use ($cmd) {
                $handle = popen($cmd, 'rb');
                if (!$handle) {
                    return;
                }
                while (!feof($handle)) {
                    echo fread($handle, 1024 * 64); // 64 KB chunks
                    if (ob_get_level()) {
                        ob_flush();
                    }
                    flush();
                }
                pclose($handle);
            },
            200,
            [
                'Content-Type'      => 'video/mp4',
                'Cache-Control'     => 'no-cache, no-store',
                'X-Accel-Buffering' => 'no',  // disable nginx buffering if behind proxy
            ]
        );
    }

    /**
     * Stream a video file with proper HTTP Range support (for already-H264 files).
     * The browser <video> element requires Range requests (206 Partial Content)
     * to seek, buffer, and play the video correctly.
     */
    private function streamVideoFile(string $filepath)
    {
        $fileSize = filesize($filepath);
        $start    = 0;
        $end      = $fileSize - 1;
        $status   = 200;

        $headers = [
            'Content-Type'        => 'video/mp4',
            'Accept-Ranges'       => 'bytes',
            'Content-Disposition' => 'inline; filename="' . basename($filepath) . '"',
            'Cache-Control'       => 'no-cache, no-store',
        ];

        // Handle browser Range request (seek / progressive download)
        $rangeHeader = request()->header('Range');
        if ($rangeHeader && preg_match('/bytes=(\d+)-(\d*)/', $rangeHeader, $m)) {
            $start  = (int) $m[1];
            $end    = $m[2] !== '' ? (int) $m[2] : $end;
            $end    = min($end, $fileSize - 1);
            $status = 206;
            $headers['Content-Range'] = "bytes {$start}-{$end}/{$fileSize}";
        }

        $length = $end - $start + 1;
        $headers['Content-Length'] = $length;

        $handle = fopen($filepath, 'rb');
        fseek($handle, $start);

        return response()->stream(
            function () use ($handle, $length) {
                $remaining = $length;
                $chunk     = 1024 * 256; // 256 KB chunks
                while ($remaining > 0 && !feof($handle)) {
                    $read = fread($handle, min($chunk, $remaining));
                    echo $read;
                    $remaining -= strlen($read);
                    flush();
                }
                fclose($handle);
            },
            $status,
            $headers
        );
    }
}

