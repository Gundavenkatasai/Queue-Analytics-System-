<?php

namespace App\Http\Controllers;

use App\Models\HeatmapSnapshot;
use Illuminate\Http\Request;

class HeatmapController extends Controller
{
    public function getByDate(Request $request, $date)
    {
        $cameraId = $request->query('camera_id', 'camera_1');

        $heatmaps = HeatmapSnapshot::getHeatmapByDate($date, $cameraId);

        if ($heatmaps->isEmpty()) {
            return response()->json([
                'status' => 'no_data',
                'message' => 'No heatmap data for this date'
            ], 404);
        }

        return response()->json([
            'status' => 'success',
            'date' => $date,
            'count' => count($heatmaps),
            'data' => $heatmaps
        ], 200);
    }

    public function getByHour(Request $request, $date, $hour)
    {
        $cameraId = $request->query('camera_id', 'camera_1');

        $heatmap = HeatmapSnapshot::getHeatmapByDateAndHour($date, (int) $hour, $cameraId);

        if (!$heatmap) {
            return response()->json([
                'status' => 'no_data',
                'message' => 'No heatmap data for this hour'
            ], 404);
        }

        return response()->json([
            'status' => 'success',
            'date' => $date,
            'hour' => (int) $hour,
            'data' => $heatmap
        ], 200);
    }

    public function store(Request $request)
    {
        try {
            $validated = $request->validate([
                'camera_id' => 'required|string',
                'date' => 'required|date_format:Y-m-d',
                'hour' => 'required|integer|between:0,23',
                'heatmap_matrix' => 'required|array',
            ]);

            $snapshot = HeatmapSnapshot::create($validated);

            return response()->json([
                'status' => 'success',
                'message' => 'Heatmap snapshot stored',
                'data' => $snapshot
            ], 201);

        } catch (\Exception $e) {
            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage()
            ], 400);
        }
    }
}
