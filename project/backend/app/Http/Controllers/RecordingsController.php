<?php

namespace App\Http\Controllers;

require_once app_path('Support/MongoBson/ObjectId.php');

use App\Models\Recording;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Carbon\Carbon;
use Exception;

class RecordingsController extends Controller
{
    public function index(Request $request)
    {
        $cameraId = $request->query('camera_id', 'camera_1');
        $date = $request->query('date'); // optional YYYY-MM-DD
        $limit = min($request->query('limit', 50), 200);

        try {
            $query = Recording::where('camera_id', $cameraId);

            if ($date) {
                $start = Carbon::createFromFormat('Y-m-d', $date)->startOfDay();
                $end = Carbon::createFromFormat('Y-m-d', $date)->endOfDay();
                $query->whereBetween('start_time', [$start, $end]);
            }

            $recordings = $query->orderBy('start_time', 'desc')->limit($limit)->get();

            if ($recordings->isEmpty()) {
                $recordings = collect($this->loadFallbackRecordings($cameraId, $date, $limit));
            }
        } catch (Exception $e) {
            Log::error("Recordings index error: " . $e->getMessage());
            $recordings = collect($this->loadFallbackRecordings($cameraId, $date, $limit));
        }

        return response()->json([
            'status' => 'success',
            'count' => count($recordings),
            'data' => $recordings
        ], 200);
    }

    public function show(Request $request, $id)
    {
        try {
            $recording = null;
            try {
                $recording = Recording::find($id);
            } catch (Exception $dbEx) {
                Log::warning("MongoDB recording find failed: " . $dbEx->getMessage());
            }

            if (!$recording) {
                // Check cache
                $inMemory = Cache::get('in_memory_recordings', []);
                $recording = collect($inMemory)->firstWhere('id', $id);

                if (!$recording) {
                    $recording = $this->findFallbackRecording($id);
                }
            }

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
        } catch (Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => 'Database error: ' . $e->getMessage()
            ], 500);
        }
    }

    public function store(Request $request)
    {
        try {
            $validated = $request->validate([
                'camera_id' => 'required|string',
                'filename' => 'required|string',
                'filepath' => 'required|string',
                'cloud_url' => 'nullable|string',
                'duration_seconds' => 'required|integer|min:0',
                'people_count' => 'required|integer|min:0',
                'file_size_bytes' => 'required|integer|min:0',
                'frame_count' => 'required|integer|min:0',
                'fps' => 'nullable|integer|min:1',
                'start_time' => 'nullable|string',
                'end_time' => 'nullable|string',
            ]);

            $recording = Recording::create($validated);

            return response()->json([
                'status' => 'success',
                'message' => 'Recording metadata stored',
                'data' => $recording
            ], 201);

        } catch (Exception $e) {
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
            // Ensure start_time is always populated so the frontend can format dates
            if (empty($validated['start_time'])) {
                $validated['start_time'] = now()->toIso8601String();
            }
            if (empty($validated['end_time'])) {
                $validated['end_time'] = now()->addSeconds($validated['duration_seconds'] ?? 60)->toIso8601String();
            }
            $inMemory = Cache::get('in_memory_recordings', []);
            $inMemory[] = $validated;
            if (count($inMemory) > 50)
                array_shift($inMemory);
            Cache::put('in_memory_recordings', $inMemory);

            return response()->json([
                'status' => 'success',
                'message' => 'Recording metadata stored (cached)',
                'data' => $validated
            ], 201);
        }
    }

    public function destroy(Request $request, $id)
    {
        try {
            $recording = Recording::find($id);

            if (!$recording) {
                // Check if it's in cache
                $inMemory = Cache::get('in_memory_recordings', []);
                $updated = array_filter($inMemory, fn($r) => ($r['id'] ?? '') !== $id);
                if (count($inMemory) !== count($updated)) {
                    Cache::put('in_memory_recordings', array_values($updated));
                    return response()->json(['status' => 'success', 'message' => 'Recording removed from cache'], 200);
                }

                $fallbackRecord = $this->findFallbackRecording($id);
                if ($fallbackRecord) {
                    return response()->json(['status' => 'error', 'message' => 'Fallback recordings are read-only'], 403);
                }

                return response()->json([
                    'status' => 'error',
                    'message' => 'Recording not found'
                ], 404);
            }

            // Delete physical file if exists
            if (isset($recording->filepath) && file_exists($recording->filepath)) {
                @unlink($recording->filepath);
            }

            $recording->delete();

            return response()->json([
                'status' => 'success',
                'message' => 'Recording deleted'
            ], 200);
        } catch (Exception $e) {
            return response()->json(['status' => 'error', 'message' => $e->getMessage()], 500);
        }
    }

    public function stream(Request $request, $id)
    {
        try {
            $recording = null;
            try {
                $recording = Recording::find($id);
            } catch (Exception $dbEx) {
                Log::warning("MongoDB recording find failed: " . $dbEx->getMessage());
            }

            if (!$recording) {
                // Check cache first
                $inMemory = Cache::get('in_memory_recordings', []);
                $recording = collect($inMemory)->firstWhere('id', $id);

                if (!$recording) {
                    $recording = $this->findFallbackRecording($id);
                }
            }

            if (!$recording) {
                return response()->json(['error' => 'Recording not found'], 404);
            }

            $cloudUrl = is_array($recording) ? ($recording['cloud_url'] ?? null) : ($recording->cloud_url ?? null);

            if ($cloudUrl && strpos($cloudUrl, 'gridfs://') === 0) {
                $fileId = substr($cloudUrl, 9);
                return $this->streamFromGridFS($fileId);
            }

            $filepath = is_array($recording) ? ($recording['filepath'] ?? null) : ($recording->filepath ?? null);
            $filename = is_array($recording) ? ($recording['filename'] ?? null) : ($recording->filename ?? null);

            if (!$filepath && !empty($filename)) {
                $filepath = $this->resolveFallbackVideoPath($filename);
            }
            if (!$filepath || !file_exists($filepath)) {
                return response()->json(['error' => 'File not found'], 404);
            }

            // Reject files that are too small to be valid video (corrupted/empty recordings)
            $minValidBytes = 1024; // 1 KB
            if (filesize($filepath) < $minValidBytes) {
                Log::warning("Skipping corrupt/empty recording file: {$filepath} (" . filesize($filepath) . " bytes)");
                return response()->json(['error' => 'Recording file is corrupted or empty'], 422);
            }

            // Stream raw or non-H264 videos on-the-fly using FFmpeg transcode if available.
            // This is a bulletproof backup that guarantees modern browser compatibility.
            $ffmpeg = $this->findFfmpeg();
            $filenameLower = strtolower($filename ?? '');
            $isRawOrAvi = (strpos($filenameLower, '_raw') !== false) || (substr($filenameLower, -4) === '.avi');

            if ($ffmpeg && ($isRawOrAvi || $this->isMp4vVideo($filepath, $ffmpeg))) {
                Log::info("Streaming video via FFmpeg dynamic transcode: " . $filepath);
                return $this->streamWithFfmpeg($filepath, $ffmpeg);
            }

            // Stream local file directly with full byte-range support
            return $this->streamVideoFile($filepath);

        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    public function streamByFilename(Request $request, $filename)
    {
        try {
            $decodedFilename = urldecode($filename);

            $recording = null;
            try {
                $recording = Recording::where('filename', $decodedFilename)
                    ->orderBy('start_time', 'desc')
                    ->first();
            } catch (Exception $dbEx) {
                Log::warning("MongoDB recording filename find failed: " . $dbEx->getMessage());
            }

            $filepath = $recording ? ($recording->filepath ?? null) : null;
            if (!$filepath) {
                $filepath = $this->resolveFallbackVideoPath($decodedFilename);
            }

            if (!$filepath || !file_exists($filepath)) {
                return response()->json(['error' => 'File not found'], 404);
            }

            $minValidBytes = 1024;
            if (filesize($filepath) < $minValidBytes) {
                return response()->json(['error' => 'Recording file is corrupted or empty'], 422);
            }

            $ffmpeg = $this->findFfmpeg();
            $filenameLower = strtolower($decodedFilename);
            $isRawOrAvi = (strpos($filenameLower, '_raw') !== false) || (substr($filenameLower, -4) === '.avi');

            if ($ffmpeg && ($isRawOrAvi || $this->isMp4vVideo($filepath, $ffmpeg))) {
                return $this->streamWithFfmpeg($filepath, $ffmpeg);
            }

            return $this->streamVideoFile($filepath);
        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    private function loadFallbackRecordings(?string $cameraId = null, ?string $date = null, int $limit = 50): array
    {
        $records = [];

        foreach ($this->fallbackRecordingFiles() as $filePath) {
            if (!file_exists($filePath)) {
                continue;
            }

            $content = file_get_contents($filePath);
            $items = json_decode($content, true);
            if (!is_array($items)) {
                continue;
            }

            foreach ($items as $item) {
                $normalized = $this->normalizeFallbackRecording($item);
                if ($cameraId !== null && ($normalized['camera_id'] ?? '') !== $cameraId) {
                    continue;
                }

                if ($date) {
                    $recordedAt = Carbon::parse($normalized['start_time'] ?? $normalized['created_at'] ?? null);
                    $start = Carbon::createFromFormat('Y-m-d', $date)->startOfDay();
                    $end = Carbon::createFromFormat('Y-m-d', $date)->endOfDay();
                    if (!$recordedAt->betweenIncluded($start, $end)) {
                        continue;
                    }
                }

                $records[$normalized['id']] = $normalized;
            }
        }

        usort($records, function ($left, $right) {
            return strcmp($right['start_time'] ?? '', $left['start_time'] ?? '');
        });

        return array_slice(array_values($records), 0, $limit);
    }

    private function findFallbackRecording(string $id): ?array
    {
        foreach ($this->loadFallbackRecordings(null, null, 500) as $recording) {
            if (($recording['id'] ?? '') === $id) {
                return $recording;
            }
        }

        return null;
    }

    private function resolveFallbackVideoPath(string $filename): string
    {
        $projectRoot = dirname(base_path());
        return $projectRoot . DIRECTORY_SEPARATOR . 'ml-service' . DIRECTORY_SEPARATOR . 'storage' . DIRECTORY_SEPARATOR . 'videos' . DIRECTORY_SEPARATOR . $filename;
    }

    private function fallbackRecordingFiles(): array
    {
        $projectRoot = dirname(base_path());

        return [
            $projectRoot . DIRECTORY_SEPARATOR . 'ml-service' . DIRECTORY_SEPARATOR . 'storage' . DIRECTORY_SEPARATOR . 'analytics_recordings.json',
            storage_path('analytics_recordings.json'),
        ];
    }

    private function normalizeFallbackRecording(array $record): array
    {
        $filename = $record['filename'] ?? ('recording_' . uniqid() . '.mp4');
        $startTime = $record['start_time'] ?? $record['created_at'] ?? $record['stored_at'] ?? now()->toIso8601String();
        $endTime = $record['end_time'] ?? $startTime;
        $durationSeconds = (int) round((float) ($record['duration_seconds'] ?? $record['duration'] ?? 0));
        $fileSizeBytes = (int) ($record['file_size_bytes'] ?? $record['file_size'] ?? 0);

        return [
            'id' => $record['id'] ?? $filename,
            'camera_id' => $record['camera_id'] ?? 'camera_1',
            'filename' => $filename,
            'filepath' => $record['filepath'] ?? $this->resolveFallbackVideoPath($filename),
            'cloud_url' => $record['cloud_url'] ?? null,
            'duration_seconds' => $durationSeconds,
            'people_count' => (int) ($record['people_count'] ?? 0),
            'file_size_bytes' => $fileSizeBytes,
            'frame_count' => (int) ($record['frame_count'] ?? 0),
            'fps' => (int) ($record['fps'] ?? 15),
            'start_time' => $startTime,
            'end_time' => $endTime,
            'created_at' => $record['created_at'] ?? $record['stored_at'] ?? $startTime,
        ];
    }

    /**
     * Stream from MongoDB GridFS
     */
    private function streamFromGridFS($fileId)
    {
        try {
            $db = DB::connection('mongodb')->getMongoDB();
            $bucket = $db->selectGridFSBucket();
            $stream = $bucket->openDownloadStream(new \MongoDB\BSON\ObjectId($fileId));
            $metadata = $bucket->getFileDocumentForStream($stream);

            return response()->stream(
                function () use ($stream) {
                    while (!feof($stream)) {
                        echo fread($stream, 1024 * 64);
                        flush();
                    }
                    fclose($stream);
                },
                200,
                [
                    'Content-Type' => 'video/mp4',
                    'Content-Length' => $metadata->length,
                    'Accept-Ranges' => 'bytes',
                    'Access-Control-Allow-Origin' => '*',
                    'Access-Control-Allow-Headers' => '*',
                    'Cross-Origin-Resource-Policy' => 'cross-origin',
                ]
            );
        } catch (Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * Find FFmpeg executable on common Windows/Linux install paths.
     */
    private function findFfmpeg(): ?string
    {
        $projectRoot = dirname(base_path());
        $localFfmpeg = $projectRoot . DIRECTORY_SEPARATOR . 'ml-service' . DIRECTORY_SEPARATOR . 'ffmpeg.exe';
        if (file_exists($localFfmpeg)) {
            return $localFfmpeg;
        }

        if (PHP_OS_FAMILY === 'Windows') {
            $out = [];
            $code = -1;
            @exec('where ffmpeg 2>&1', $out, $code);
            if ($code === 0 && !empty($out[0])) {
                return trim($out[0]);
            }
        }

        $candidates = [
            'ffmpeg',
            'C:\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe',
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
        ];

        foreach ($candidates as $cmd) {
            $out = [];
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

        // On Windows, popen() requires the entire command to be wrapped in an extra
        // set of double-quotes ONLY when the command itself contains quoted tokens
        // AND we use cmd.exe implicitly. The safest approach for Windows is to use
        // the absolute path without extra outer wrapping, since PHP's popen() on
        // Windows calls cmd.exe /c internally.
        //
        // Correct Windows format: "C:\path\to ffmpeg.exe" -y -i "input" ... pipe:1
        // WRONG format (breaks popen): ""C:\path\ffmpeg.exe" -y -i "input" pipe:1"
        //
        // We build a cmd.exe-compatible command string for Windows.
        if (PHP_OS_FAMILY === 'Windows') {
            // Use double-quoted ffmpeg path (handles spaces), and use Windows NUL for stderr
            $quotedFfmpeg = '"' . str_replace('/', '\\', $ffmpeg) . '"';
            $quotedInput = '"' . str_replace('/', '\\', $filepath) . '"';
            $cmd = $quotedFfmpeg
                . ' -y -i ' . $quotedInput
                . ' -c:v libx264 -preset ultrafast -tune zerolatency -crf 23'
                . ' -movflags frag_keyframe+empty_moov+default_base_moof'
                . ' -f mp4 pipe:1'
                . ' 2>NUL';
        } else {
            $cmd = '"' . $ffmpeg . '"'
                . ' -y -i ' . escapeshellarg($filepath)
                . ' -c:v libx264 -preset ultrafast -tune zerolatency -crf 23'
                . ' -movflags frag_keyframe+empty_moov+default_base_moof'
                . ' -f mp4 pipe:1'
                . ' 2>/dev/null';
        }

        Log::info("[FFmpeg Stream] Running: {$cmd}");

        return response()->stream(
            function () use ($cmd) {
                $handle = popen($cmd, 'rb');
                if (!$handle) {
                    Log::error("[FFmpeg Stream] popen() returned false. Command was: {$cmd}");
                    return;
                }
                while (!feof($handle)) {
                    $chunk = fread($handle, 1024 * 64); // 64 KB chunks
                    if ($chunk === false)
                        break;
                    echo $chunk;
                    if (ob_get_level()) {
                        ob_flush();
                    }
                    flush();
                }
                pclose($handle);
            },
            200,
            [
                'Content-Type' => 'video/mp4',
                'Cache-Control' => 'no-cache, no-store',
                'X-Accel-Buffering' => 'no',
                'Access-Control-Allow-Origin' => '*',
                'Access-Control-Allow-Headers' => '*',
                'Cross-Origin-Resource-Policy' => 'cross-origin',
            ]
        );
    }

    /**
     * Probe video with FFmpeg to detect if it is NOT H.264
     */
    private function isMp4vVideo(string $filepath, string $ffmpeg): bool
    {
        try {
            // Build the probe command correctly for each OS.
            // On Windows, exec() also uses cmd.exe, so the quoting rules differ.
            if (PHP_OS_FAMILY === 'Windows') {
                $quotedFfmpeg = '"' . str_replace('/', '\\', $ffmpeg) . '"';
                $quotedInput = '"' . str_replace('/', '\\', $filepath) . '"';
                $cmd = $quotedFfmpeg . ' -i ' . $quotedInput . ' 2>&1';
            } else {
                $cmd = '"' . $ffmpeg . '" -i ' . escapeshellarg($filepath) . ' 2>&1';
            }
            $output = [];
            @exec($cmd, $output);
            $fullOutput = implode("\n", $output);

            // If it contains "Video: h264", it is natively supported by all modern browsers
            if (strpos($fullOutput, 'Video: h264') !== false) {
                return false; // Already H.264 — serve directly with range support
            }
            return true; // Not H.264 (e.g. mp4v, mpeg4, or other codecs) — must transcode
        } catch (\Exception $e) {
            return false; // On error, assume it's fine to stream directly
        }
    }

    /**
     * Stream a video file with proper HTTP Range support (for already-H264 files).
     * The browser <video> element requires Range requests (206 Partial Content)
     * to seek, buffer, and play the video correctly.
     */
    private function streamVideoFile(string $filepath)
    {
        $fileSize = filesize($filepath);
        $start = 0;
        $end = $fileSize - 1;
        $status = 200;

        // Detect correct MIME type
        $ext = strtolower(pathinfo($filepath, PATHINFO_EXTENSION));
        if ($ext === 'webm') {
            $mimeType = 'video/webm';
        } elseif ($ext === 'avi') {
            $mimeType = 'video/x-msvideo';
        } else {
            $mimeType = 'video/mp4';
        }

        $headers = [
            'Content-Type' => $mimeType,
            'Accept-Ranges' => 'bytes',
            'Content-Disposition' => 'inline; filename="' . basename($filepath) . '"',
            'Cache-Control' => 'no-cache, no-store',
            'Access-Control-Allow-Origin' => '*',
            'Access-Control-Allow-Headers' => '*',
            'Cross-Origin-Resource-Policy' => 'cross-origin',
        ];

        // Handle browser Range request (seek / progressive download)
        $rangeHeader = request()->header('Range');
        if ($rangeHeader && preg_match('/bytes=(\d+)-(\d*)/', $rangeHeader, $m)) {
            $start = (int) $m[1];
            $end = $m[2] !== '' ? (int) $m[2] : $end;
            $end = min($end, $fileSize - 1);
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
                $chunk = 1024 * 256; // 256 KB chunks
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
