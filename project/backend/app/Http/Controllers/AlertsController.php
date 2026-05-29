<?php

namespace App\Http\Controllers;

use App\Models\Alert;
use Illuminate\Http\Request;
use Log;

class AlertsController extends Controller
{
    public function index(Request $request)
    {
        try {
            $cameraId = $request->query('camera_id', 'camera_1');
            $acknowledged = $request->query('acknowledged', null);
            $limit = min($request->query('limit', 100), 500);

            $query = Alert::where('camera_id', $cameraId);

            if ($acknowledged !== null) {
                $query->where('acknowledged', $acknowledged === 'true');
            }

            $alerts = $query->orderBy('created_at', 'desc')
                ->limit($limit)
                ->get();

            return response()->json([
                'status' => 'success',
                'count' => count($alerts),
                'data' => $alerts
            ], 200);
        } catch (\Exception $e) {
            Log::error('Alerts index error: ' . $e->getMessage());

            // Return a valid JSON response even when MongoDB fails
            return response()->json([
                'status' => 'success',
                'count' => 0,
                'data' => [],
                'warning' => 'Database temporarily unavailable'
            ], 200);
        }
    }

    public function acknowledge(Request $request, $id)
    {
        try {
            $alert = Alert::find($id);

            if (!$alert) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Alert not found'
                ], 404);
            }

            $alert->update(['acknowledged' => true]);

            return response()->json([
                'status' => 'success',
                'message' => 'Alert acknowledged',
                'data' => $alert
            ], 200);
        } catch (\Exception $e) {
            Log::error('Alert acknowledge error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Failed to acknowledge alert: ' . $e->getMessage()
            ], 500);
        }
    }

    public function create(Request $request)
    {
        try {
            $data = $request->validate([
                'camera_id'  => 'required|string',
                'alert_type' => 'nullable|string',
                'type'       => 'nullable|string',
                'severity'   => 'nullable|string|in:low,medium,high,critical',
                'message'    => 'nullable|string',
                'value'      => 'nullable|numeric',
                'threshold'  => 'nullable|numeric',
            ]);

            $alert = Alert::create([
                'camera_id'    => $data['camera_id'],
                'alert_type'   => $data['alert_type'] ?? $data['type'] ?? 'unknown',
                'severity'     => $data['severity'] ?? 'medium',
                'message'      => $data['message'] ?? 'Alert triggered',
                'value'        => $data['value'] ?? null,
                'threshold'    => $data['threshold'] ?? null,
                'acknowledged' => false,
                'created_at'   => now()->toIso8601String(),
            ]);

            return response()->json(['status' => 'success', 'data' => $alert], 201);
        } catch (\Exception $e) {
            Log::error('Alert create error: ' . $e->getMessage());
            return response()->json(['status' => 'error', 'message' => $e->getMessage()], 500);
        }
    }

    public function destroy(Request $request, $id)
    {
        try {
            $alert = Alert::find($id);

            if (!$alert) {
                return response()->json([
                    'status'  => 'error',
                    'message' => 'Alert not found'
                ], 404);
            }

            $alert->delete();

            return response()->json([
                'status'  => 'success',
                'message' => 'Alert deleted'
            ], 200);
        } catch (\Exception $e) {
            Log::error('Alert destroy error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Failed to delete alert: ' . $e->getMessage()
            ], 500);
        }
    }
}
