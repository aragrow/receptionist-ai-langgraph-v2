#!/bin/bash
# Quick Workflow Status Check
# Run this to get immediate answers about your workflow state

echo "=========================================="
echo "QUICK WORKFLOW STATUS CHECK"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check 1: Does workflow file exist?
echo "1. Checking workflow file..."
if [ -f "src/workflow/ai_receptionist_workflow.py" ]; then
    echo -e "${GREEN}✓${NC} Workflow file exists"
else
    echo -e "${RED}✗${NC} Workflow file NOT FOUND!"
    exit 1
fi
echo ""

# Check 2: What does workflow import?
echo "2. Checking workflow imports..."
echo "----------------------------------------"

# Old node imports
OLD_IMPORTS=0
if grep -q "from src.nodes.identity_checker" src/workflow/ai_receptionist_workflow.py; then
    echo -e "${RED}✗${NC} Found: identity_checker import (OLD)"
    ((OLD_IMPORTS++))
else
    echo -e "${GREEN}✓${NC} No identity_checker import"
fi

if grep -q "from src.nodes.intent_analyzer" src/workflow/ai_receptionist_workflow.py; then
    echo -e "${RED}✗${NC} Found: intent_analyzer import (OLD)"
    ((OLD_IMPORTS++))
else
    echo -e "${GREEN}✓${NC} No intent_analyzer import"
fi

if grep -q "from src.nodes.response_generator" src/workflow/ai_receptionist_workflow.py; then
    echo -e "${RED}✗${NC} Found: response_generator import (OLD)"
    ((OLD_IMPORTS++))
else
    echo -e "${GREEN}✓${NC} No response_generator import"
fi

echo ""

# New agent imports
NEW_IMPORTS=0
if grep -q "from src.agents.receptionist_l1" src/workflow/ai_receptionist_workflow.py; then
    echo -e "${GREEN}✓${NC} Found: ReceptionistL1 import (NEW)"
    ((NEW_IMPORTS++))
else
    echo -e "${YELLOW}?${NC} No ReceptionistL1 import"
fi

if grep -q "from src.agents.l2_agent_factory" src/workflow/ai_receptionist_workflow.py; then
    echo -e "${GREEN}✓${NC} Found: L2AgentFactory import (NEW)"
    ((NEW_IMPORTS++))
else
    echo -e "${YELLOW}?${NC} No L2AgentFactory import"
fi

if grep -q "from src.agents.l3_agent_factory" src/workflow/ai_receptionist_workflow.py; then
    echo -e "${GREEN}✓${NC} Found: L3AgentFactory import (NEW)"
    ((NEW_IMPORTS++))
else
    echo -e "${YELLOW}?${NC} No L3AgentFactory import"
fi

echo ""

# Check 3: What classes are instantiated?
echo "3. Checking class usage in workflow..."
echo "----------------------------------------"

# Old nodes - Fixed: properly handle grep output
OLD_USAGE=0
if grep -qE "IdentityChecker\(\)|IntentAnalyzer\(\)|ResponseGenerator\(\)" src/workflow/ai_receptionist_workflow.py 2>/dev/null; then
    OLD_USAGE=$(grep -oE "IdentityChecker\(\)|IntentAnalyzer\(\)|ResponseGenerator\(\)" src/workflow/ai_receptionist_workflow.py 2>/dev/null | wc -l)
    OLD_USAGE=$(echo $OLD_USAGE | tr -d ' ')  # Remove any whitespace
fi

if [ "$OLD_USAGE" -gt 0 ] 2>/dev/null; then
    echo -e "${RED}✗${NC} Found $OLD_USAGE old node instantiation(s)"
else
    echo -e "${GREEN}✓${NC} No old node instantiations"
fi

# New agents - Fixed: properly handle grep output
NEW_USAGE=0
if grep -qE "ReceptionistL1\(\)|L2AgentFactory\(\)|L3AgentFactory\(\)" src/workflow/ai_receptionist_workflow.py 2>/dev/null; then
    NEW_USAGE=$(grep -oE "ReceptionistL1\(\)|L2AgentFactory\(\)|L3AgentFactory\(\)" src/workflow/ai_receptionist_workflow.py 2>/dev/null | wc -l)
    NEW_USAGE=$(echo $NEW_USAGE | tr -d ' ')  # Remove any whitespace
fi

if [ "$NEW_USAGE" -gt 0 ] 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Found $NEW_USAGE new agent instantiation(s)"
else
    echo -e "${YELLOW}?${NC} No new agent instantiations found"
fi

echo ""

# Check 4: Do old node files exist?
echo "4. Checking if old node files exist..."
echo "----------------------------------------"

OLD_FILES=0
if [ -f "src/nodes/identity_checker.py" ]; then
    echo -e "${YELLOW}!${NC} identity_checker.py exists"
    ((OLD_FILES++))
else
    echo -e "${GREEN}✓${NC} identity_checker.py removed"
fi

if [ -f "src/nodes/intent_analyzer.py" ]; then
    echo -e "${YELLOW}!${NC} intent_analyzer.py exists"
    ((OLD_FILES++))
else
    echo -e "${GREEN}✓${NC} intent_analyzer.py removed"
fi

if [ -f "src/nodes/response_generator.py" ]; then
    echo -e "${YELLOW}!${NC} response_generator.py exists"
    ((OLD_FILES++))
else
    echo -e "${GREEN}✓${NC} response_generator.py removed"
fi

echo ""

# Check 5: Do new agent files exist?
echo "5. Checking if new agent files exist..."
echo "----------------------------------------"

AGENT_COUNT=0

if [ -f "src/agents/receptionist_l1.py" ]; then
    echo -e "${GREEN}✓${NC} receptionist_l1.py exists"
    ((AGENT_COUNT++))
else
    echo -e "${RED}✗${NC} receptionist_l1.py missing"
fi

if [ -f "src/agents/receptionist_l2_base.py" ]; then
    echo -e "${GREEN}✓${NC} receptionist_l2_base.py exists"
    ((AGENT_COUNT++))
else
    echo -e "${RED}✗${NC} receptionist_l2_base.py missing"
fi

if [ -f "src/agents/l3_base_agent.py" ]; then
    echo -e "${GREEN}✓${NC} l3_base_agent.py exists"
    ((AGENT_COUNT++))
else
    echo -e "${RED}✗${NC} l3_base_agent.py missing"
fi

if [ -f "src/agents/l2_agent_factory.py" ]; then
    echo -e "${GREEN}✓${NC} l2_agent_factory.py exists"
    ((AGENT_COUNT++))
else
    echo -e "${RED}✗${NC} l2_agent_factory.py missing"
fi

if [ -f "src/agents/l3_agent_factory.py" ]; then
    echo -e "${GREEN}✓${NC} l3_agent_factory.py exists"
    ((AGENT_COUNT++))
else
    echo -e "${RED}✗${NC} l3_agent_factory.py missing"
fi

echo ""
echo "Agent system files: $AGENT_COUNT/5"

echo ""

# Check 6: Test files
echo "6. Checking test files..."
echo "----------------------------------------"

if [ -f "tests/test_nodes.py" ]; then
    if grep -q "from src.nodes" tests/test_nodes.py; then
        echo -e "${YELLOW}!${NC} test_nodes.py uses old node imports"
    else
        echo -e "${GREEN}✓${NC} test_nodes.py doesn't import old nodes"
    fi
else
    echo -e "${YELLOW}?${NC} test_nodes.py not found"
fi

if [ -f "tests/test_agents.py" ]; then
    echo -e "${GREEN}✓${NC} test_agents.py exists (new tests)"
else
    echo -e "${YELLOW}?${NC} test_agents.py not found"
fi

echo ""

# Check 7: Search for any remaining old imports
echo "7. Scanning for old node imports in src/..."
echo "----------------------------------------"

OLD_REFS=$(find src -name "*.py" ! -path "src/nodes/*" -exec grep -l "from src.nodes.identity_checker\|from src.nodes.intent_analyzer\|from src.nodes.response_generator" {} \; 2>/dev/null)

if [ -z "$OLD_REFS" ]; then
    echo -e "${GREEN}✓${NC} No old node imports found outside src/nodes/"
else
    echo -e "${RED}✗${NC} Found old node imports in:"
    echo "$OLD_REFS" | while read -r file; do
        echo "   - $file"
    done
fi

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""

# Determine overall status - with proper integer checks
if [ "$OLD_IMPORTS" -eq 0 ] 2>/dev/null && [ "$NEW_IMPORTS" -gt 0 ] 2>/dev/null && [ "$OLD_USAGE" -eq 0 ] 2>/dev/null; then
    echo -e "${GREEN}STATUS: ✓ WORKFLOW MIGRATED${NC}"
    echo ""
    echo "Your workflow is using the new agent system!"
    echo ""
    if [ "$OLD_FILES" -gt 0 ] 2>/dev/null; then
        echo -e "${YELLOW}ACTION NEEDED:${NC}"
        echo "- Old node files can be safely deleted"
        echo "- Update test files to use new agents"
        echo ""
        echo "Run these commands to clean up:"
        echo "  rm src/nodes/identity_checker.py"
        echo "  rm src/nodes/intent_analyzer.py"
        echo "  rm src/nodes/response_generator.py"
    else
        echo -e "${GREEN}✓ Clean state - no old files to remove${NC}"
    fi
elif [ "$OLD_IMPORTS" -gt 0 ] 2>/dev/null || [ "$OLD_USAGE" -gt 0 ] 2>/dev/null; then
    echo -e "${RED}STATUS: ✗ WORKFLOW NOT MIGRATED${NC}"
    echo ""
    echo "Your workflow is still using old nodes!"
    echo ""
    echo -e "${YELLOW}ACTION NEEDED:${NC}"
    echo "1. Update src/workflow/ai_receptionist_workflow.py"
    echo "2. Replace old node imports with agent imports"
    echo "3. Update workflow graph to use 3-tier routing"
    echo ""
    echo "See Phase 3.2 documentation for migration steps."
elif [ "$AGENT_COUNT" -lt 5 ] 2>/dev/null; then
    echo -e "${YELLOW}STATUS: ? INCOMPLETE SETUP${NC}"
    echo ""
    echo "Agent system is not fully installed!"
    echo ""
    echo -e "${YELLOW}ACTION NEEDED:${NC}"
    echo "- Complete agent system setup (missing $((5-AGENT_COUNT))/5 files)"
    echo "- Follow Phases 2-4 implementation guide"
else
    echo -e "${YELLOW}STATUS: ? UNCERTAIN${NC}"
    echo ""
    echo "Cannot determine workflow state."
    echo "Review the checks above and investigate."
fi

echo ""
echo "=========================================="
echo ""
echo "For detailed analysis, run:"
echo "  python verify_workflow.py"
echo ""
echo "For migration steps, see:"
echo "  docs/workflow_migration_guide.md"
echo ""