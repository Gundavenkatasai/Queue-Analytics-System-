<?php

namespace App\Http\Controllers;

use App\Models\Alert;
use Illuminate\Http\Request;

class AlertsController extends Controller
{
    public function index(Request $request)
    {
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
    }

    public function acknowledge(Request $request, $id)
    {
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
    }

    public function destroy(Request $request, $id)
    {
        $alert = Alert::find($id);

        if (!$alert) {
            return response()->json([
                'status' => 'error',
                'message' => 'Alert not found'
            ], 404);
        }

        $alert->delete();

        return response()->json([
            'status' => 'success',
            'message' => 'Alert deleted'
        ], 200);
    }
}
