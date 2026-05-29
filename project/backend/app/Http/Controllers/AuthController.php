<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Carbon\Carbon;
use Log;

class AuthController extends Controller
{
    /**
     * Register a new user with email + password (stores in MongoDB Atlas)
     * POST /api/auth/register
     */
    public function register(Request $request)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|email',
            'password' => 'required|string|min:6',
        ]);

        try {
            // Check if user already exists
            $existing = DB::connection('mongodb')
                ->table('users')
                ->where('email', $validated['email'])
                ->first();

            if ($existing) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'An account with this email already exists. Please sign in.',
                ], 409);
            }

            // Hash the password with bcrypt
            $hashedPassword = password_hash($validated['password'], PASSWORD_BCRYPT);

            $user = [
                'name' => $validated['name'],
                'email' => $validated['email'],
                'password' => $hashedPassword,
                'role' => 'Operator',
                'created_at' => Carbon::now()->toIso8601String(),
                'last_login' => Carbon::now()->toIso8601String(),
            ];

            $insertResult = DB::connection('mongodb')->table('users')->insert($user);

            // Fetch the newly created user to get the _id
            $newUser = DB::connection('mongodb')
                ->table('users')
                ->where('email', $validated['email'])
                ->first();

            $token = base64_encode($validated['email'] . ':' . time() . ':' . bin2hex(random_bytes(8)));

            return response()->json([
                'status' => 'success',
                'token' => $token,
                'user' => [
                    'id' => (string) ($newUser->_id ?? uniqid()),
                    'name' => $validated['name'],
                    'email' => $validated['email'],
                    'role' => 'Operator',
                ],
            ], 201);

        } catch (\Exception $e) {
            Log::error('Registration error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Registration failed. Please try again later.',
                'debug' => config('app.debug') ? $e->getMessage() : null,
            ], 500);
        }
    }

    /**
     * Email/password login — looks up MongoDB users collection, verifies bcrypt password
     * POST /api/auth/login
     */
    public function login(Request $request)
    {
        $validated = $request->validate([
            'email' => 'required|email',
            'password' => 'required|string',
        ]);

        try {
            $user = DB::connection('mongodb')
                ->table('users')
                ->where('email', $validated['email'])
                ->first();

            if (!$user) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'No account found with this email. Please sign up first.',
                ], 401);
            }

            // Verify password (bcrypt)
            $storedHash = is_array($user) ? ($user['password'] ?? '') : ($user->password ?? '');
            if (!$storedHash || !password_verify($validated['password'], $storedHash)) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Incorrect password. Please try again.',
                ], 401);
            }

            // Update last_login timestamp
            try {
                DB::connection('mongodb')
                    ->table('users')
                    ->where('email', $validated['email'])
                    ->update(['last_login' => Carbon::now()->toIso8601String()]);
            } catch (\Exception $e) {
                // Non-critical — don't fail the login
            }

            $token = base64_encode($validated['email'] . ':' . time() . ':' . bin2hex(random_bytes(8)));
            $userId = is_array($user) ? (string) ($user['_id'] ?? uniqid()) : (string) ($user->_id ?? uniqid());
            $name = is_array($user) ? ($user['name'] ?? '') : ($user->name ?? '');
            $role = is_array($user) ? ($user['role'] ?? 'Operator') : ($user->role ?? 'Operator');

            return response()->json([
                'status' => 'success',
                'token' => $token,
                'user' => [
                    'id' => $userId,
                    'name' => $name,
                    'email' => $validated['email'],
                    'role' => $role,
                ],
            ]);

        } catch (\Exception $e) {
            Log::error('Login DB error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Unable to connect to the database. Please try again.',
                'debug' => config('app.debug') ? $e->getMessage() : null,
            ], 500);
        }
    }

    /**
     * Google OAuth — upsert user in MongoDB, return user profile
     * POST /api/auth/google
     */
    public function googleLogin(Request $request)
    {
        $validated = $request->validate([
            'google_id' => 'required|string',
            'name' => 'required|string',
            'email' => 'required|email',
            'picture' => 'nullable|string',
        ]);

        try {
            // Try to upsert into MongoDB
            $existing = DB::connection('mongodb')
                ->table('users')
                ->where('google_id', $validated['google_id'])
                ->first();

            if ($existing) {
                // Update last login
                DB::connection('mongodb')
                    ->table('users')
                    ->where('google_id', $validated['google_id'])
                    ->update(['last_login' => Carbon::now()->toIso8601String()]);

                $user = array_merge((array) $existing, ['last_login' => Carbon::now()->toIso8601String()]);
            } else {
                // New Google user — also check if email exists (for merged accounts)
                $emailExists = DB::connection('mongodb')
                    ->table('users')
                    ->where('email', $validated['email'])
                    ->first();

                if ($emailExists) {
                    // Link Google ID to existing account
                    DB::connection('mongodb')
                        ->table('users')
                        ->where('email', $validated['email'])
                        ->update([
                            'google_id' => $validated['google_id'],
                            'picture' => $validated['picture'] ?? null,
                            'last_login' => Carbon::now()->toIso8601String(),
                        ]);
                    $user = (array) $emailExists;
                    $user['google_id'] = $validated['google_id'];
                } else {
                    // Brand new user
                    $user = [
                        'google_id' => $validated['google_id'],
                        'name' => $validated['name'],
                        'email' => $validated['email'],
                        'picture' => $validated['picture'] ?? null,
                        'role' => 'Operator',
                        'created_at' => Carbon::now()->toIso8601String(),
                        'last_login' => Carbon::now()->toIso8601String(),
                    ];
                    DB::connection('mongodb')->table('users')->insert($user);
                }
            }

            $userId = is_array($user) ? (string) ($user['_id'] ?? $validated['google_id']) : (string) ($user->_id ?? $validated['google_id']);
            $name = is_array($user) ? $user['name'] : $user->name;
            $email = is_array($user) ? $user['email'] : $user->email;
            $picture = is_array($user) ? ($user['picture'] ?? null) : ($user->picture ?? null);
            $role = is_array($user) ? ($user['role'] ?? 'Operator') : ($user->role ?? 'Operator');

            return response()->json([
                'status' => 'success',
                'user' => [
                    'id' => $userId,
                    'name' => $name,
                    'email' => $email,
                    'picture' => $picture,
                    'role' => $role,
                ],
            ], 200);

        } catch (\Exception $e) {
            Log::warning('MongoDB user sync failed: ' . $e->getMessage());
            // Return the profile data anyway so frontend still works
            return response()->json([
                'status' => 'success',
                'user' => [
                    'id' => $validated['google_id'],
                    'name' => $validated['name'],
                    'email' => $validated['email'],
                    'picture' => $validated['picture'] ?? null,
                    'role' => 'Operator',
                ],
            ], 200);
        }
    }
}
