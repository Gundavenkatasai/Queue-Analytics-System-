<?php

namespace App\Http\Controllers;

class HealthController extends Controller
{
    public function health()
    {
        return response()->json([
            'status' => 'ok',
            'timestamp' => now()->toIso8601String(),
            'version' => '1.0.0'
        ], 200);
    }
}
