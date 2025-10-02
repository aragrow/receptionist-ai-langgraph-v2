#!/bin/bash
# ==================== setup_workflow_migration.sh ====================
# Setup script for migrating to 3-tier workflow routing
# Run this script to set up all necessary components

set -e  # Exit on error

echo "================================================================================"
echo "WORKFLOW MIGRATION SETUP"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Backup existing files
echo "Step 1: Backing up existing workflow files..."
if [ -f "src/workflow/ai_receptionist_workflow.py" ]; then
    #cp src/workflow/ai_receptionist_workflow.py src/workflow/ai_receptionist_workflow.py.backup
    print_status "Backed up ai_receptionist_workflow.py"
else
    print_warning "No existing workflow file found"
fi

if [ -f "src/workflow/workflow_runner.py" ]; then
    #cp src/workflow/workflow_runner.py src/workflow/workflow_runner.py.backup
    print_status "Backed up workflow_runner.py"
else
    print_warning "No existing runner file found"
fi
echo ""

# Step 2: Run database migration
echo "Step 2: Running database migration..."
if python src/utilities/migrate_routing_collections.py; then
    print_status "Database migration completed"
else
    print_error "Database migration failed"
    exit 1
fi
echo ""

# Step 3: Seed L1 prompts
echo "Step 3: Seeding L1 prompts..."
if python src/utilities/seed_l1_prompts.py; then
    print_status "L1 prompts seeded"
else
    print_error "L1 prompt seeding failed"
    exit 1
fi
echo ""

# Step 4: Seed L2 prompts
echo "Step 4: Seeding L2 prompts..."
if python src/utilities/seed_l2_prompts.py; then
    print_status "L2 prompts seeded"
else
    print_error "L2 prompt seeding failed"
    exit 1
fi
echo ""

# Step 5: Verify migration
echo "Step 5: Verifying migration..."
if python verify_workflow_migration.py; then
    print_status "Migration verification passed"
else
    print_error "Migration verification failed"
    echo ""
    echo "Please review the errors above and fix any issues."
    exit 1
fi
echo ""

# Summary
echo "================================================================================"
echo "SETUP COMPLETE"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Test the workflow:"
echo "     python src/workflow/workflow_runner.py \"555-123-4567\" \"I need help\""
echo ""
echo "  2. Start the API server:"
echo "     uvicorn main:app --reload"
echo ""
echo "  3. Test via API:"
echo "     curl -X POST http://localhost:8000/process-call \\"
echo "       -H \"Content-Type: application/json\" \\"
echo "       -d '{\"caller_phone\":\"555-123-4567\",\"speech_text\":\"test\",\"call_sid\":\"test\"}'"
echo ""
echo "  4. Monitor logs:"
echo "     tail -f logs/ai_receptionist.log"
echo ""