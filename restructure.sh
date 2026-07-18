#!/bin/bash
set -e

# Initialize git if not already
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit before restructuring"
fi

# Create target directories
mkdir -p scripts docs docker deployment monitoring backend frontend

# Create backend internal structure
mkdir -p backend/app backend/api backend/core backend/config backend/database backend/models backend/schemas backend/services backend/repositories backend/dependencies backend/middleware backend/exceptions backend/security backend/camera backend/detection backend/tracking/gesture backend/face backend/fatigue backend/analytics backend/agents backend/notifications backend/websocket backend/utils backend/workers backend/tests

# Move enterprise-dashboard to frontend
echo "Moving frontend files..."
git mv enterprise-dashboard/* frontend/ 2>/dev/null || true
git mv enterprise-dashboard/.gitignore frontend/ 2>/dev/null || true
git mv enterprise-dashboard/.oxlintrc.json frontend/ 2>/dev/null || true

# Adjust frontend structure
echo "Adjusting frontend structure..."
mkdir -p frontend/src/utils frontend/src/layouts
git mv frontend/src/lib/utils.ts frontend/src/utils/ 2>/dev/null || true
rm -rf frontend/src/lib 2>/dev/null || true

git mv frontend/src/components/layout/* frontend/src/layouts/ 2>/dev/null || true
rm -rf frontend/src/components/layout 2>/dev/null || true

# Move LC-VISION--CN to backend
echo "Moving backend files..."
git mv LC-VISION--CN/main.py backend/ 2>/dev/null || true
git mv LC-VISION--CN/api/server.py backend/api/ 2>/dev/null || true
git mv LC-VISION--CN/core/config.py backend/config/ 2>/dev/null || true
git mv LC-VISION--CN/core/persistence.py backend/database/ 2>/dev/null || true
git mv LC-VISION--CN/core/pipeline.py backend/core/ 2>/dev/null || true
git mv LC-VISION--CN/core/stream_reader.py backend/camera/ 2>/dev/null || true
git mv LC-VISION--CN/db/models.py backend/models/ 2>/dev/null || true
git mv LC-VISION--CN/db/session.py backend/database/ 2>/dev/null || true
git mv LC-VISION--CN/ai/detector.py backend/detection/ 2>/dev/null || true
git mv LC-VISION--CN/ai/analytics.py backend/analytics/ 2>/dev/null || true

git mv LC-VISION--CN/modules/gesture/* backend/tracking/gesture/ 2>/dev/null || true
git mv LC-VISION--CN/yolo11n.pt backend/detection/ 2>/dev/null || true
git mv LC-VISION--CN/yolo11n_openvino_model backend/detection/ 2>/dev/null || true
git mv LC-VISION--CN/check_vid.py scripts/ 2>/dev/null || true
git mv LC-VISION--CN/docker-compose.yml ./ 2>/dev/null || true
git mv LC-VISION--CN/LICENSE backend/ 2>/dev/null || true
git mv LC-VISION--CN/README.md backend/ 2>/dev/null || true
git mv LC-VISION--CN/.gitignore backend/ 2>/dev/null || true

# Cleanup
echo "Cleaning up empty directories..."
rm -rf LC-VISION--CN/ai LC-VISION--CN/api LC-VISION--CN/core LC-VISION--CN/db LC-VISION--CN/modules/gesture LC-VISION--CN/modules LC-VISION--CN 2>/dev/null || true
rm -rf enterprise-dashboard 2>/dev/null || true

# Move LogicEye to Root README
git mv LogicEye/README.md ./ 2>/dev/null || true
rm -rf LogicEye 2>/dev/null || true

echo "Restructure move complete."
