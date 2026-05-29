#!/bin/bash
# Final Project Structure Verification Script

echo "=========================================="
echo "Queue Analytics System - File Verification"
echo "=========================================="
echo ""

# Arrays to store results
declare -a FOUND_FILES
declare -a MISSING_FILES

# Expected files
EXPECTED_FILES=(
    "ARCHITECTURE.md"
    "FOLDER_STRUCTURE.md"
    "README.md"
    "QUICK_REFERENCE.md"
    "COMPLETE_DOCUMENTATION.md"
    "TESTING.md"
    "PROJECT_SUMMARY.md"
    "INDEX.md"
    "DELIVERY_CHECKLIST.md"
    "setup.sh"
    "setup.bat"
    
    "ml-service/main.py"
    "ml-service/detector.py"
    "ml-service/tracker.py"
    "ml-service/queue_analyzer.py"
    "ml-service/api_client.py"
    "ml-service/config.py"
    "ml-service/requirements.txt"
    
    "backend/composer.json"
    "backend/.env.example"
    "backend/app/Models/Analytics.php"
    "backend/app/Http/Controllers/AnalyticsController.php"
    "backend/app/Http/Requests/StoreAnalyticsRequest.php"
    "backend/database/migrations/2024_01_01_000000_create_analytics_table.php"
    "backend/routes/api.php"
    
    "frontend/package.json"
    "frontend/.env"
    "frontend/public/index.html"
    "frontend/src/index.js"
    "frontend/src/index.css"
    "frontend/src/App.jsx"
    "frontend/src/App.css"
    "frontend/src/components/Dashboard.jsx"
    "frontend/src/components/Dashboard.css"
    "frontend/src/components/StatsCard.jsx"
    "frontend/src/components/StatsCard.css"
    "frontend/src/components/ChartComponent.jsx"
    "frontend/src/components/ChartComponent.css"
    "frontend/src/services/api.js"
    "frontend/src/utils/helpers.js"
)

# Check each file
FOUND=0
MISSING=0

for file in "${EXPECTED_FILES[@]}"; do
    if [ -f "$file" ]; then
        FOUND=$((FOUND + 1))
        FOUND_FILES+=("$file")
        echo "✓ $file"
    else
        MISSING=$((MISSING + 1))
        MISSING_FILES+=("$file")
        echo "✗ $file (MISSING)"
    fi
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Found: $FOUND files"
echo "Missing: $MISSING files"
echo ""

if [ $MISSING -eq 0 ]; then
    echo "✅ ALL FILES PRESENT - PROJECT IS COMPLETE!"
else
    echo "⚠️  Missing files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
fi

echo ""
echo "=========================================="
echo "File Statistics"
echo "=========================================="
echo ""

# Count by category
echo "Documentation Files:"
find . -maxdepth 1 -name "*.md" | wc -l
echo ""

echo "Python Files:"
find ml-service -name "*.py" 2>/dev/null | wc -l
echo ""

echo "Laravel Files:"
find backend -name "*.php" 2>/dev/null | wc -l
echo ""

echo "React Files:"
find frontend/src -name "*.jsx" -o -name "*.js" 2>/dev/null | wc -l
echo ""

echo "Total Project Files:"
find . -type f ! -path './.git/*' ! -path './node_modules/*' ! -path './.venv/*' 2>/dev/null | wc -l
echo ""

echo "=========================================="
echo "✅ VERIFICATION COMPLETE"
echo "=========================================="
