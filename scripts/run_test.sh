#!/bin/bash
# Test runner script for 3-tier routing system
# Usage: ./run_tests.sh [OPTIONS]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print section header
print_header() {
    echo ""
    echo "======================================================================"
    print_message "$BLUE" "$1"
    echo "======================================================================"
    echo ""
}

# Default options
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_E2E=false
RUN_PERFORMANCE=false
RUN_ALL=false
COVERAGE=true
VERBOSE=false
PARALLEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --e2e)
            RUN_E2E=true
            shift
            ;;
        --performance)
            RUN_PERFORMANCE=true
            shift
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-n)
            PARALLEL=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit              Run unit tests only"
            echo "  --integration       Run integration tests only"
            echo "  --e2e               Run end-to-end tests only"
            echo "  --performance       Run performance tests only"
            echo "  --all               Run all tests (default)"
            echo "  --no-coverage       Skip coverage reporting"
            echo "  --verbose, -v       Verbose output"
            echo "  --parallel, -n      Run tests in parallel"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh --unit              # Run only unit tests"
            echo "  ./run_tests.sh --integration -v    # Run integration tests with verbose output"
            echo "  ./run_tests.sh --all --parallel    # Run all tests in parallel"
            exit 0
            ;;
        *)
            print_message "$RED" "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# If no specific test type selected, run all
if [ "$RUN_UNIT" = false ] && [ "$RUN_INTEGRATION" = false ] && \
   [ "$RUN_E2E" = false ] && [ "$RUN_PERFORMANCE" = false ]; then
    RUN_ALL=true
fi

# Build pytest command
PYTEST_CMD="pytest"
PYTEST_ARGS=""

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -vv"
else
    PYTEST_ARGS="$PYTEST_ARGS -v"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -n auto"
fi

# Add coverage
if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=html --cov-report=term-missing"
fi

# Run tests
print_header "Running Tests for 3-Tier Agent Routing System"

if [ "$RUN_ALL" = true ]; then
    print_message "$GREEN" "Running all tests..."
    $PYTEST_CMD tests/ $PYTEST_ARGS
    
elif [ "$RUN_UNIT" = true ]; then
    print_header "Unit Tests"
    print_message "$GREEN" "Running unit tests..."
    
    print_message "$YELLOW" "→ L1 Agent Tests"
    $PYTEST_CMD tests/test_agents/test_l1_agent.py $PYTEST_ARGS
    
    print_message "$YELLOW" "→ L2 Agent Tests"
    $PYTEST_CMD tests/test_agents/test_l2_agents.py $PYTEST_ARGS
    
    print_message "$YELLOW" "→ L3 Agent Tests"
    $PYTEST_CMD tests/test_agents/test_l3_agents.py $PYTEST_ARGS
    
elif [ "$RUN_INTEGRATION" = true ]; then
    print_header "Integration Tests"
    print_message "$GREEN" "Running integration tests..."
    $PYTEST_CMD tests/test_integration/ $PYTEST_ARGS
    
elif [ "$RUN_E2E" = true ]; then
    print_header "End-to-End Scenario Tests"
    print_message "$GREEN" "Running E2E tests..."
    $PYTEST_CMD tests/test_e2e_scenarios.py $PYTEST_ARGS
    
elif [ "$RUN_PERFORMANCE" = true ]; then
    print_header "Performance Tests"
    print_message "$YELLOW" "⚠️  Performance tests may take several minutes..."
    $PYTEST_CMD tests/test_performance.py $PYTEST_ARGS -m "not slow"
fi

# Check exit code
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_header "✅ All Tests Passed!"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        print_message "$GREEN" "📊 Coverage report generated: htmlcov/index.html"
        echo ""
        print_message "$BLUE" "Open coverage report:"
        echo "    open htmlcov/index.html        # macOS"
        echo "    xdg-open htmlcov/index.html    # Linux"
        echo "    start htmlcov/index.html       # Windows"
    fi
else
    print_header "❌ Tests Failed"
    print_message "$RED" "Some tests failed. Please review the output above."
    exit $TEST_EXIT_CODE
fi

echo ""
print_message "$BLUE" "Test run completed at $(date)"
echo ""