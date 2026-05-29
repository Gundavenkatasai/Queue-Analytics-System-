<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class Cors
{
    /**
     * Handle an incoming request.
     * Allows the React frontend (localhost:3000) to call the Laravel API (localhost:8000).
     */
    public function handle(Request $request, Closure $next)
    {
        // Handle OPTIONS preflight request immediately (browsers send this before POST/PUT)
        if ($request->isMethod('OPTIONS')) {
            return response('', 200)
                ->header('Access-Control-Allow-Origin', '*')
                ->header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
                ->header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
                ->header('Access-Control-Max-Age', '86400');
        }

        $response = $next($request);

        // StreamedResponse doesn't expose ->header(), so set headers via header bag.
        $response->headers->set('Access-Control-Allow-Origin', '*');
        $response->headers->set('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
        $response->headers->set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept');

        return $response;
    }
}
