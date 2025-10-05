#!/bin/bash

# ============================================================================
# AI Receptionist System - Deployment Script
# ============================================================================
# This script automates the deployment process for the AI Receptionist System
# 
# Usage:
#   ./scripts/deploy.sh [environment] [options]
#
# Environments:
#   dev         - Development environment
#   staging     - Staging environment  
#   production  - Production environment
#
# Options:
#   --build     - Force rebuild of Docker images
#   --migrate   - Run database migrations
#   --seed      - Seed initial data
#   --backup    - Create backup before deployment
#   --rollback  - Rollback to previous version
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV="${1:-dev}"
BUILD_FLAG=""
MIGRATE_FLAG=false
SEED_FLAG=false
BACKUP_FLAG=false
ROLLBACK_FLAG=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Parse Arguments
# ============================================================================

shift || true  # Skip environment argument
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --migrate)
            MIGRATE_FLAG=true
            shift
            ;;
        --seed)
            SEED_FLAG=true
            shift
            ;;
        --backup)
            BACKUP_FLAG=true
            shift
            ;;
        --rollback)
            ROLLBACK_FLAG=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# Validate Environment
# ============================================================================

log_info "Deploying to ${ENV} environment..."

if [[ ! "$ENV" =~ ^(dev|staging|production)$ ]]; then
    log_error "Invalid environment: ${ENV}"
    log_info "Valid environments: dev, staging, production"
    exit 1
fi

# Load environment-specific configuration
ENV_FILE="${PROJECT_DIR}/.env.${ENV}"
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Environment file not found: ${ENV_FILE}"
    exit 1
fi

# ============================================================================
# Pre-deployment Checks
# ============================================================================

log_info "Running pre-deployment checks..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Check if .env file exists
if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
    log_warning ".env file not found. Creating from .env.example..."
    if [[ -f "${PROJECT_DIR}/.env.example" ]]; then
        cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
        log_info "Please edit .env file with your configuration and run again."
        exit 1
    else
        log_error ".env.example not found"
        exit 1
    fi
fi

# Validate required environment variables
source "${PROJECT_DIR}/.env"
required_vars=("MONGODB_URI" "GOOGLE_API_KEY")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "Required environment variable not set: ${var}"
        exit 1
    fi
done

log_success "Pre-deployment checks passed"

# ============================================================================
# Backup (if requested)
# ============================================================================

if [[ "$BACKUP_FLAG" == true ]]; then
    log_info "Creating backup..."
    
    BACKUP_DIR="${PROJECT_DIR}/backups"
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).gz"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup MongoDB
    docker-compose exec -T mongodb mongodump \
        --db="${MONGODB_DB_NAME}" \
        --archive="/tmp/${BACKUP_FILE}" \
        --gzip
    
    docker-compose cp mongodb:/tmp/"${BACKUP_FILE}" "${BACKUP_DIR}/${BACKUP_FILE}"
    
    log_success "Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"
fi

# ============================================================================
# Rollback (if requested)
# ============================================================================

if [[ "$ROLLBACK_FLAG" == true ]]; then
    log_warning "Rolling back to previous version..."
    
    # Stop current containers
    docker-compose down
    
    # Restore from latest backup
    LATEST_BACKUP=$(ls -t "${PROJECT_DIR}/backups/"backup_*.gz | head -1)
    
    if [[ -z "$LATEST_BACKUP" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    log_info "Restoring from: ${LATEST_BACKUP}"
    
    docker-compose up -d mongodb
    sleep 10
    
    docker-compose exec -T mongodb mongorestore \
        --archive=/tmp/backup.gz \
        --gzip \
        --drop
    
    log_success "Rollback completed"
    exit 0
fi

# ============================================================================
# Build & Deploy
# ============================================================================

cd "$PROJECT_DIR"

log_info "Stopping existing containers..."
docker-compose down

log_info "Pulling latest images..."
docker-compose pull

if [[ -n "$BUILD_FLAG" ]]; then
    log_info "Building Docker images..."
    docker-compose build --no-cache
fi

log_info "Starting services..."
if [[ "$ENV" == "production" ]]; then
    docker-compose --profile production up -d
else
    docker-compose up -d
fi

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

# Check MongoDB health
RETRIES=30
until docker-compose exec -T mongodb mongosh --eval "db.runCommand('ping').ok" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    log_info "Waiting for MongoDB... ($RETRIES retries left)"
    sleep 2
    ((RETRIES--))
done

if [ $RETRIES -eq 0 ]; then
    log_error "MongoDB failed to start"
    exit 1
fi

log_success "MongoDB is healthy"

# Check application health
RETRIES=30
until curl -f http://localhost:${PORT:-8000}/health > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    log_info "Waiting for application... ($RETRIES retries left)"
    sleep 2
    ((RETRIES--))
done

if [ $RETRIES -eq 0 ]; then
    log_error "Application failed to start"
    docker-compose logs app
    exit 1
fi

log_success "Application is healthy"

# ============================================================================
# Database Migrations
# ============================================================================

if [[ "$MIGRATE_FLAG" == true ]]; then
    log_info "Running database migrations..."
    
    docker-compose exec -T app python src/utilities/migrate_routing_collections.py
    
    log_success "Database migrations completed"
fi

# ============================================================================
# Seed Data
# ============================================================================

if [[ "$SEED_FLAG" == true ]]; then
    log_info "Seeding database..."
    
    # Seed L1 prompts
    docker-compose exec -T app python src/utilities/seed_l1_prompts.py
    
    # Seed L2 prompts
    docker-compose exec -T app python src/utilities/seed_l2_prompts.py
    
    # Seed L3 prompts (if exists)
    if docker-compose exec -T app test -f src/utilities/seed_l3_prompts.py; then
        docker-compose exec -T app python src/utilities/seed_l3_prompts.py
    fi
    
    # Seed test data (dev only)
    if [[ "$ENV" == "dev" ]]; then
        docker-compose exec -T app python src/utilities/generate_test_data.py
    fi
    
    log_success "Database seeding completed"
fi

# ============================================================================
# Post-deployment Verification
# ============================================================================

log_info "Running post-deployment verification..."

# Test API endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT:-8000}/health)
if [[ "$HTTP_CODE" != "200" ]]; then
    log_error "Health check failed with HTTP ${HTTP_CODE}"
    exit 1
fi

log_success "Health check passed"

# ============================================================================
# Display Status
# ============================================================================

echo ""
log_success "============================================"
log_success "  Deployment Completed Successfully!"
log_success "============================================"
echo ""
log_info "Environment: ${ENV}"
log_info "Application URL: http://localhost:${PORT:-8000}"
log_info "API Docs: http://localhost:${PORT:-8000}/docs"
log_info "Analytics Dashboard: http://localhost:${PORT:-8000}/dashboard"
echo ""
log_info "Container Status:"
docker-compose ps
echo ""

# ============================================================================
# Monitoring Commands
# ============================================================================

echo ""
log_info "Useful Commands:"
echo "  View logs:          docker-compose logs -f app"
echo "  Stop services:      docker-compose down"
echo "  Restart app:        docker-compose restart app"
echo "  Run migrations:     docker-compose exec app python src/utilities/migrate_routing_collections.py"
echo "  Access MongoDB:     docker-compose exec mongodb mongosh"
echo "  View metrics:       curl http://localhost:${PORT:-8000}/analytics/dashboard"
echo ""

log_success "Deployment script completed!"