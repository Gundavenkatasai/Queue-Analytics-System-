<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('analytics', function (Blueprint $table) {
            $table->id();
            $table->integer('people_count')->default(0);
            $table->integer('queue_length')->default(0);
            $table->integer('entry_count')->default(0);
            $table->integer('exit_count')->default(0);
            $table->timestamps();

            // Indexes for performance
            $table->index('created_at');
            $table->index(['created_at', 'people_count']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('analytics');
    }
};
