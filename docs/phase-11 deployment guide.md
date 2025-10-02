# Deployment Guide

Complete guide for deploying the AI Receptionist System to various environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Database Setup](#database-setup)
6. [Configuration](#configuration)
7. [SSL/TLS Setup](#ssltls-setup)
8. [Monitoring & Logging](#monitoring--logging)
9. [Scaling](#scaling)
10. [Backup & Recovery](#backup--recovery)
11. [CI/CD Pipeline](#cicd-pipeline)

---

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **MongoDB**: 7.0 or higher
- **Git**: 2.30 or higher

### Required Accounts

- **Google Cloud**: For Gemini API access
- **MongoDB Atlas**: For cloud database (optional)
- **Domain**: For production deployment (optional)

### System Requirements

**Minimum** (Development):
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB
- Network: Broadband internet

**Recommended** (Production):
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- Network: High-speed internet with low latency

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd ai-receptionist
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Step 4: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

**Required settings**:
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=ai_receptionist
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Step 5: Start MongoDB

**Option A - Docker**:
```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:7.0
```

**Option B - Local Installation**:
```bash
# Install MongoDB (Ubuntu)
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
```

### Step 6: Initialize Database

```bash
# Run migrations
python src/utilities/migrate_routing_collections.py

# Seed prompts
python src/utilities/seed_l1_prompts.py
python src/utilities/seed_l2_prompts.py

# Generate test data (optional)
python src/utilities/generate_test_data.py
```

### Step 7: Start Application

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the workflow runner
python src/workflow/workflow_runner.py
```

### Step 8: Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Open API docs
open http://localhost:8000/docs

# Open analytics dashboard
open http://localhost:8000/dashboard
```

---

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Deployment Script

```bash
# Make script executable
chmod +x scripts/deploy.sh

# Deploy to development
./scripts/deploy.sh dev --migrate --seed

# Deploy to production
./scripts/deploy.sh production --build --migrate --backup
```

**Script Options**:
- `--build`: Force rebuild Docker images
- `--migrate`: Run database migrations
- `--seed`: Seed initial data
- `--backup`: Create backup before deployment
- `--rollback`: Rollback to previous version

### Manual Docker Commands

```bash
# Build image
docker build -t ai-receptionist:latest .

# Run container
docker run -d \
  --name ai-receptionist \
  -p 8000:8000 \
  -e MONGODB_URI=mongodb://mongodb:27017 \
  -e GOOGLE_API_KEY=your_key \
  --network ai-receptionist-network \
  ai-receptionist:latest

# View logs
docker logs -f ai-receptionist

# Execute commands in container
docker exec -it ai-receptionist bash
```

### Production Profile

For production with NGINX and monitoring:

```bash
# Start with production profile
docker-compose --profile production --profile monitoring up -d

# Services included:
# - Application (4 workers)
# - MongoDB
# - Redis
# - NGINX reverse proxy
# - Prometheus
# - Grafana
```

---

## Cloud Deployment

### AWS EC2 Deployment

#### Step 1: Launch EC2 Instance

**Recommended Instance**: `t3.large` (2 vCPU, 8 GB RAM)

**AMI**: Ubuntu Server 22.04 LTS

**Security Group Rules**:
- Port 22 (SSH) - Your IP only
- Port 80 (HTTP) - 0.0.0.0/0
- Port 443 (HTTPS) - 0.0.0.0/0
- Port 8000 (App) - Optional, for testing

#### Step 2: Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
exit
```

#### Step 3: Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd ai-receptionist

# Configure environment
cp .env.example .env
nano .env  # Set your values

# Deploy
./scripts/deploy.sh production --build --migrate --seed
```

#### Step 4: Configure Domain (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
```

### Google Cloud Platform (GCP)

#### Step 1: Create Compute Engine Instance

```bash
gcloud compute instances create ai-receptionist \
  --zone=us-central1-a \
  --machine-type=e2-standard-2 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-ssd \
  --tags=http-server,https-server
```

#### Step 2: Configure Firewall

```bash
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --target-tags http-server

gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --target-tags https-server
```

#### Step 3: Deploy (Same as AWS)

Follow AWS deployment steps 2-4.

### Azure Deployment

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name ai-receptionist-rg --location eastus

# Create container
az container create \
  --resource-group ai-receptionist-rg \
  --name ai-receptionist \
  --image your-registry/ai-receptionist:latest \
  --dns-name-label ai-receptionist \
  --ports 8000 \
  --environment-variables \
    MONGODB_URI=your_mongodb_uri \
    GOOGLE_API_KEY=your_api_key
```

### Kubernetes Deployment

#### Step 1: Create Kubernetes Manifests

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-receptionist
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-receptionist
  template:
    metadata:
      labels:
        app: ai-receptionist
    spec:
      containers:
      - name: app
        image: ai-receptionist:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: ai-receptionist-secrets
              key: mongodb-uri
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-receptionist-secrets
              key: google-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-receptionist
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: ai-receptionist
```

#### Step 2: Deploy to Kubernetes

```bash
# Create secrets
kubectl create secret generic ai-receptionist-secrets \
  --from-literal=mongodb-uri='your_mongodb_uri' \
  --from-literal=google-api-key='your_api_key'

# Apply manifests
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/ai-receptionist
```

---

## Database Setup

### MongoDB Atlas (Cloud)

#### Step 1: Create Cluster

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster or paid tier
3. Choose your cloud provider and region
4. Configure cluster settings

#### Step 2: Configure Network Access

1. Go to Network Access
2. Add your application's IP address
3. For development: Add 0.0.0.0/0 (not recommended for production)

#### Step 3: Create Database User

1. Go to Database Access
2. Add new database user
3. Set username and password
4. Grant read/write access

#### Step 4: Get Connection String

1. Click "Connect" on your cluster
2. Choose "Connect your application"
3. Copy the connection string
4. Replace `<password>` with your password
5. Add to `.env`:

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

#### Step 5: Create Indexes

```bash
# Run migration script
python src/utilities/migrate_routing_collections.py
```

### Self-Hosted MongoDB

#### Using Docker

```bash
# Start MongoDB with authentication
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  -v mongodb_config:/data/configdb \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=your_secure_password \
  mongo:7.0
```

#### On Ubuntu Server

```bash
# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Secure MongoDB
sudo mongosh
> use admin
> db.createUser({
    user: "admin",
    pwd: "your_secure_password",
    roles: ["root"]
  })
> exit

# Enable authentication
sudo nano /etc/mongod.conf
# Add:
# security:
#   authorization: enabled

sudo systemctl restart mongod
```

---

## Configuration

### Environment Variables

Edit `.env` file with your configuration:

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=ai_receptionist

# LLM
GOOGLE_API_KEY=your_actual_api_key_here
MODEL_NAME=gemini-2.0-flash-exp

# Routing
CONFIDENCE_THRESHOLD_HIGH=0.75
CONFIDENCE_THRESHOLD_MEDIUM=0.4
MAX_CLARIFICATIONS=2

# Session
SESSION_TTL_MINUTES=30
MAX_CONVERSATION_HISTORY=10

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/ai_receptionist.log

# Security
PII_MASKING_ENABLED=true
API_KEY_ENABLED=false
```

### Production Settings

**For production, ensure**:

```env
# Use production database
MONGODB_URI=mongodb+srv://prod-user:password@cluster.mongodb.net/

# Secure logging
LOG_LEVEL=WARNING
PII_MASKING_ENABLED=true

# Enable authentication
API_KEY_ENABLED=true
API_KEY=generate_secure_random_key

# Enable monitoring
METRICS_ENABLED=true
SENTRY_DSN=your_sentry_dsn

# Set proper CORS
CORS_ORIGINS=https://yourdomain.com

# Disable debug features
DEBUG_MODE=false
USE_MOCK_LLM=false
SEED_TEST_DATA=false
```

---

## SSL/TLS Setup

### Using Let's Encrypt with NGINX

#### Step 1: Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

#### Step 2: Obtain Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

#### Step 3: Auto-Renewal

Certbot automatically sets up renewal. Test it:

```bash
sudo certbot renew --dry-run
```

### Manual SSL Configuration

**nginx.conf**:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Monitoring & Logging

### Application Logs

**View logs**:
```bash
# Docker
docker-compose logs -f app

# Local
tail -f logs/ai_receptionist.log
```

**Log format** (JSON):
```json
{
    "timestamp": "2025-10-01T10:00:00Z",
    "level": "INFO",
    "event": "l1_classification",
    "session_id": "sess_abc123",
    "intent": "scheduling",
    "confidence": 0.92
}
```

### Metrics Dashboard

Access built-in dashboard:
```
http://your-domain/dashboard
```

### Prometheus & Grafana

If using monitoring profile:

**Prometheus**: `http://your-domain:9090`
**Grafana**: `http://your-domain:3000` (default login: admin/admin)

### Sentry Integration

Add to `.env`:
```env
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Health Checks

**Endpoint**: `GET /health`

**Response**:
```json
{
    "status": "healthy",
    "database": "connected",
    "uptime_seconds": 3600
}
```

**Monitoring script**:
```bash
#!/bin/bash
while true; do
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "$(date): Health check failed!" >> health.log
        # Send alert
    fi
    sleep 60
done
```

---

## Scaling

### Horizontal Scaling

**Docker Compose**:
```bash
# Scale to 4 instances
docker-compose up -d --scale app=4
```

**Kubernetes**:
```bash
# Scale deployment
kubectl scale deployment ai-receptionist --replicas=4
```

### Load Balancing

**NGINX** (already configured in docker-compose):
```nginx
upstream app_servers {
    server app_1:8000;
    server app_2:8000;
    server app_3:8000;
    server app_4:8000;
}

server {
    location / {
        proxy_pass http://app_servers;
    }
}
```

### Database Scaling

**MongoDB Replica Set**:

1. Configure replica set in MongoDB Atlas
2. Update connection string:
```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?replicaSet=rs0
```

### Caching with Redis

Enable Redis in `.env`:
```env
REDIS_ENABLED=true
REDIS_HOST=redis
REDIS_PORT=6379
```

---

## Backup & Recovery

### Automated Backups

**Using deployment script**:
```bash
./scripts/deploy.sh production --backup
```

**Manual backup**:
```bash
# MongoDB
docker-compose exec mongodb mongodump \
  --db=ai_receptionist \
  --archive=/tmp/backup.gz \
  --gzip

docker-compose cp mongodb:/tmp/backup.gz ./backups/
```

### Restore from Backup

```bash
# Copy backup to container
docker-compose cp ./backups/backup.gz mongodb:/tmp/

# Restore
docker-compose exec mongodb mongorestore \
  --archive=/tmp/backup.gz \
  --gzip \
  --drop
```

### Backup Schedule

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/scripts/deploy.sh production --backup
```

---

## CI/CD Pipeline

### GitHub Actions

**.github/workflows/deploy.yml**:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest
      
      - name: Build Docker image
        run: docker build -t ai-receptionist:latest .
      
      - name: Deploy to production
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          SERVER_HOST: ${{ secrets.SERVER_HOST }}
        run: |
          echo "$SSH_PRIVATE_KEY" > key.pem
          chmod 600 key.pem
          ssh -i key.pem user@$SERVER_HOST "cd /app && git pull && ./scripts/deploy.sh production --build"
```

### GitLab CI

**.gitlab-ci.yml**:
```yaml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest

build:
  stage: build
  script:
    - docker build -t ai-receptionist:latest .
    - docker push registry/ai-receptionist:latest

deploy:
  stage: deploy
  script:
    - ssh user@server "cd /app && ./scripts/deploy.sh production"
  only:
    - main
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

---

**Last Updated**: October 2025  
**Version**: 2.0