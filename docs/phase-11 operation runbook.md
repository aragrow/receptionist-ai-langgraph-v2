# Operations Runbook

Complete operational guide for the AI Receptionist System on-call team.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Alert Response](#alert-response)
3. [Common Incidents](#common-incidents)
4. [Escalation Procedures](#escalation-procedures)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Emergency Contacts](#emergency-contacts)
7. [Post-Incident Review](#post-incident-review)

---

## System Overview

### Architecture Summary

```
User → NGINX → Application (4 workers) → MongoDB
                    ↓
              Redis Cache
```

### Critical Components

| Component | Purpose | Health Check | Recovery Time |
|-----------|---------|--------------|---------------|
| Application | Process calls | `/health` | 2 minutes |
| MongoDB | Data persistence | `mongosh ping` | 5 minutes |
| Redis | Session cache | `redis-cli ping` | 1 minute |
| NGINX | Load balancer | Port 80/443 | 1 minute |

### Service Dependencies

- **Google Gemini API**: LLM processing (external)
- **MongoDB Atlas**: Database (if using cloud)
- **DNS**: Domain resolution
- **SSL Certificates**: Let's Encrypt

### Key Metrics

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Response Time | <3s | 3-5s | >5s |
| Error Rate | <1% | 1-5% | >5% |
| CPU Usage | <50% | 50-80% | >80% |
| Memory Usage | <60% | 60-85% | >85% |
| Disk Usage | <70% | 70-90% | >90% |

---

## Alert Response

### Alert Priority Levels

**P0 - Critical (Response: Immediate)**
- System completely down
- Data loss occurring
- Security breach
- >50% error rate

**P1 - High (Response: 15 minutes)**
- Partial outage
- 10-50% error rate
- Database connection issues
- Performance degradation >5s

**P2 - Medium (Response: 1 hour)**
- 5-10% error rate
- Non-critical service degradation
- Disk space warning
- Certificate expiring soon

**P3 - Low (Response: Next business day)**
- Minor performance issues
- Logging issues
- Non-urgent warnings

### Alert Response Workflow

```
1. Acknowledge alert (within 5 minutes)
2. Assess severity
3. Check system health
4. Review recent changes
5. Implement fix or escalate
6. Verify resolution
7. Document incident
```

---

## Common Incidents

### Incident: Application Down

**Alert**: `Health check failed - no response from /health endpoint`

**Severity**: P0 - Critical

**Symptoms**:
- Users cannot access system
- 502/503 errors from NGINX
- No logs being generated

**Triage Steps**:

1. **Check if application is running**:
```bash
docker-compose ps app
# or
systemctl status ai-receptionist
```

2. **Check application logs**:
```bash
docker-compose logs --tail=100 app
```

3. **Check resource usage**:
```bash
docker stats
# Look for OOM (Out of Memory) kills
```

**Resolution**:

**If application crashed**:
```bash
# Restart application
docker-compose restart app

# Wait for health check
sleep 30
curl http://localhost:8000/health
```

**If OOM killed**:
```bash
# Increase memory limit in docker-compose.yml
resources:
  limits:
    memory: 4G  # Increase from 2G

# Restart with new limits
docker-compose up -d app
```

**If port conflict**:
```bash
# Find process using port
lsof -i :8000

# Kill conflicting process
kill -9 <PID>

# Restart application
docker-compose up -d app
```

**Verification**:
```bash
# Health check
curl http://localhost:8000/health

# Test call processing
curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{
    "caller_phone": "+14155551234",
    "speech_text": "test",
    "call_sid": "test-001"
  }'
```

**Post-Incident**:
- Review logs for root cause
- Update monitoring if needed
- Document in incident log

---

### Incident: Database Connection Lost

**Alert**: `MongoDB connection failed - unable to connect`

**Severity**: P0 - Critical

**Symptoms**:
- Application returning 503 errors
- Logs showing `ServerSelectionTimeoutError`
- Users cannot complete actions

**Triage Steps**:

1. **Check MongoDB status**:
```bash
docker-compose ps mongodb
# or
systemctl status mongod
```

2. **Check MongoDB logs**:
```bash
docker-compose logs --tail=100 mongodb
```

3. **Test connection**:
```bash
mongosh "mongodb://localhost:27017"
```

**Resolution**:

**If MongoDB stopped**:
```bash
# Start MongoDB
docker-compose up -d mongodb

# Wait for startup
sleep 10

# Verify
mongosh --eval "db.serverStatus()"
```

**If authentication failed**:
```bash
# Check credentials in .env
cat .env | grep MONGODB

# Test connection with credentials
mongosh "mongodb://username:password@localhost:27017/admin"

# If password wrong, reset in MongoDB
mongosh
> use admin
> db.changeUserPassword("username", "new_password")
```

**If disk full**:
```bash
# Check disk space
df -h

# Clean up old data
docker system prune -a

# Or increase disk size (cloud provider)
```

**If network issue**:
```bash
# Check connectivity
ping mongodb-host

# Check firewall rules
sudo iptables -L

# Check MongoDB is listening
netstat -tulpn | grep 27017
```

**Verification**:
```bash
# Test connection
mongosh --eval "db.runCommand('ping')"

# Restart application
docker-compose restart app

# Test end-to-end
curl http://localhost:8000/health
```

---

### Incident: High Error Rate

**Alert**: `Error rate above threshold - 10% errors in last 5 minutes`

**Severity**: P1 - High

**Symptoms**:
- Increased 500 errors
- Dashboard showing red metrics
- User complaints

**Triage Steps**:

1. **Check error distribution**:
```bash
curl http://localhost:8000/analytics/dashboard | jq '.l3_actions.failure_reasons'
```

2. **Check recent errors**:
```bash
grep "ERROR" logs/ai_receptionist.log | tail -50
```

3. **Check external dependencies**:
```bash
# Test Google Gemini API
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"test"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$GOOGLE_API_KEY"
```

**Resolution**:

**If LLM API issues**:
```bash
# Check API quota
# Go to Google Cloud Console > APIs & Services > Quotas

# Switch to backup model temporarily
# In .env:
MODEL_NAME=gemini-1.5-flash

# Restart
docker-compose restart app
```

**If database timeout**:
```bash
# Check slow queries
mongosh
> use ai_receptionist
> db.setProfilingLevel(2)
> db.system.profile.find({millis: {$gt: 100}}).sort({millis: -1}).limit(10)

# Add missing indexes if found
python src/utilities/migrate_routing_collections.py
```

**If memory pressure**:
```bash
# Check memory
docker stats

# Restart to clear memory
docker-compose restart app

# If persistent, scale up
docker-compose up -d --scale app=6
```

**Verification**:
```bash
# Monitor error rate for 5 minutes
watch -n 10 'curl -s http://localhost:8000/analytics/dashboard | jq ".l3_actions.success_rate"'
```

---

### Incident: Slow Response Times

**Alert**: `Average response time above 5 seconds`

**Severity**: P1 - High

**Symptoms**:
- Users experiencing delays
- Requests timing out
- Queue building up

**Triage Steps**:

1. **Check current load**:
```bash
docker stats
curl http://localhost:8000/analytics/dashboard | jq '.routing_performance'
```

2. **Check for slow queries**:
```bash
mongosh
> use ai_receptionist
> db.currentOp({"secs_running": {$gt: 1}})
```

3. **Check LLM response times**:
```bash
grep "processing_time_ms" logs/ai_receptionist.log | tail -20
```

**Resolution**:

**If high CPU usage**:
```bash
# Scale up workers
docker-compose up -d --scale app=8

# Or add rate limiting
# In .env:
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_IP=50
```

**If slow LLM responses**:
```bash
# Use faster model
# In .env:
MODEL_NAME=gemini-2.0-flash-exp

# Reduce conversation history
MAX_CONVERSATION_HISTORY=5

# Restart
docker-compose restart app
```

**If database slow**:
```bash
# Check indexes
mongosh
> use ai_receptionist
> db.sessions.getIndexes()

# Optimize queries
# Add compound indexes for common queries
```

**If memory swapping**:
```bash
# Check swap usage
free -h

# Increase memory limits
# In docker-compose.yml:
resources:
  limits:
    memory: 4G
```

**Verification**:
```bash
# Test response time
time curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{"caller_phone":"+14155551234","speech_text":"test","call_sid":"test"}'

# Should be <3 seconds
```

---

### Incident: SSL Certificate Expired

**Alert**: `SSL certificate expires in 7 days`

**Severity**: P2 - Medium (P0 if already expired)

**Symptoms**:
- HTTPS not working
- Browser warnings
- Certificate errors in logs

**Resolution**:

```bash
# Check expiration
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -text -noout | grep "Not After"

# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run

# Reload NGINX
docker-compose exec nginx nginx -s reload

# Verify
curl -vI https://yourdomain.com 2>&1 | grep "expire"
```

**Prevention**:
```bash
# Set up auto-renewal (should be automatic with Certbot)
sudo systemctl status certbot.timer

# Or add to cron
0 0 * * 0 certbot renew --quiet && docker-compose exec nginx nginx -s reload
```

---

### Incident: Disk Space Full

**Alert**: `Disk usage above 90%`

**Severity**: P1 - High

**Symptoms**:
- Application errors
- Cannot write logs
- Database operations failing

**Triage Steps**:

1. **Check disk usage**:
```bash
df -h
du -sh /* | sort -hr | head -10
```

2. **Find large files**:
```bash
find / -type f -size +1G 2>/dev/null
```

**Resolution**:

```bash
# Clean Docker resources
docker system prune -a --volumes
docker image prune -a

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Clean old backups
find backups/ -name "*.gz" -mtime +90 -delete

# Clean MongoDB oplog (if too large)
mongosh
> use local
> db.oplog.rs.stats()
# If too large, increase oplog size

# Expand disk (cloud provider)
# AWS: Modify EBS volume
# GCP: Resize persistent disk
# Azure: Expand managed disk
```

**Verification**:
```bash
df -h
# Should show <70% usage
```

---

## Escalation Procedures

### When to Escalate

Escalate if:
- Cannot resolve within SLA time
- Root cause unknown
- Requires code changes
- Security incident suspected
- Data loss occurred

### Escalation Contacts

**Level 1 - On-Call Engineer**
- Response: Immediate
- Handles: Common incidents, restarts, config changes

**Level 2 - Senior Engineer**
- Response: 30 minutes
- Handles: Complex issues, code bugs, architecture problems
- Contact: [senior-eng-email]
- Phone: [phone-number]

**Level 3 - Engineering Lead**
- Response: 1 hour
- Handles: Critical decisions, major incidents, data loss
- Contact: [lead-email]
- Phone: [phone-number]

**Level 4 - CTO / VP Engineering**
- Response: As needed
- Handles: Business impact, customer escalations, PR issues
- Contact: [cto-email]
- Phone: [phone-number]

### Escalation Template

```
Subject: [P0/P1/P2] - [Brief Description]

Incident ID: INC-20251001-001
Severity: P0 - Critical
Started: 2025-10-01 10:30 UTC
Duration: 45 minutes
Status: Escalating to Level 2

Impact:
- 100% of users unable to access system
- Estimated 500 users affected
- Revenue impact: $X/hour

What We Know:
- Application not responding to health checks
- All restart attempts failed
- No recent deployments

What We've Tried:
- Restarted application (3x)
- Checked logs (no errors)
- Verified database connectivity
- Checked resource usage

Need Help With:
- Root cause analysis
- Alternative recovery options
- Decision on failover to backup

Current Actions:
- Monitoring logs
- Collecting diagnostic data
```

---

## Maintenance Procedures

### Scheduled Maintenance

**Recommended Window**: Sunday 2:00-4:00 AM (lowest traffic)

**Pre-Maintenance Checklist**:
- [ ] Notify users 48 hours in advance
- [ ] Create full backup
- [ ] Test in staging environment
- [ ] Prepare rollback plan
- [ ] Verify team availability
- [ ] Update status page

**During Maintenance**:
- [ ] Update status page to "maintenance"
- [ ] Create pre-maintenance backup
- [ ] Execute changes
- [ ] Run smoke tests
- [ ] Monitor for 30 minutes
- [ ] Update status page to "operational"

**Post-Maintenance**:
- [ ] Verify all services healthy
- [ ] Check key metrics
- [ ] Review logs for errors
- [ ] Send completion notification
- [ ] Document changes

### Deployment Procedure

```bash
# 1. Backup current state
./scripts/deploy.sh production --backup

# 2. Deploy new version
./scripts/deploy.sh production --build --migrate

# 3. Run smoke tests
python scripts/smoke_tests.py

# 4. Monitor for 15 minutes
watch -n 10 'curl -s http://localhost:8000/analytics/dashboard | jq ".l3_actions.success_rate"'

# 5. If issues, rollback
./scripts/deploy.sh production --rollback
```

### Database Maintenance

**Weekly Tasks**:
```bash
# Backup database
./scripts/deploy.sh production --backup

# Check indexes
mongosh
> use ai_receptionist
> db.sessions.getIndexes()

# Clean expired sessions
mongosh
> use ai_receptionist
> db.sessions.deleteMany({expires_at: {$lt: new Date()}})
```

**Monthly Tasks**:
```bash
# Compact database
mongosh
> use ai_receptionist
> db.runCommand({compact: 'sessions'})

# Rebuild indexes
> db.sessions.reIndex()

# Check database size
> db.stats()
```

### Certificate Renewal

**Monthly Check**:
```bash
# Check expiration
sudo certbot certificates

# Renew if needed (automatic)
sudo certbot renew

# Verify renewal worked
curl -vI https://yourdomain.com 2>&1 | grep "expire"
```

---

## Emergency Contacts

### Internal Team

| Role | Name | Email | Phone | Timezone |
|------|------|-------|-------|----------|
| On-Call Engineer | [Name] | [Email] | [Phone] | UTC-6 |
| Backup On-Call | [Name] | [Email] | [Phone] | UTC-6 |
| Senior Engineer | [Name] | [Email] | [Phone] | UTC-6 |
| Engineering Lead | [Name] | [Email] | [Phone] | UTC-6 |
| DevOps Lead | [Name] | [Email] | [Phone] | UTC-6 |

### External Vendors

| Service | Support Contact | Phone | Portal |
|---------|----------------|-------|--------|
| Google Cloud | [Contact] | [Phone] | console.cloud.google.com |
| MongoDB Atlas | [Contact] | [Phone] | cloud.mongodb.com |
| AWS (if used) | [Contact] | [Phone] | console.aws.amazon.com |
| SSL Provider | [Contact] | [Phone] | [URL] |

### Communication Channels

- **Status Page**: status.yourdomain.com
- **Incident Chat**: #incidents (Slack)
- **On-Call**: #on-call (Slack)
- **PagerDuty**: pagerduty.com/your-account

---

## Post-Incident Review

### When to Conduct PIR

- All P0 incidents
- P1 incidents lasting >1 hour
- Any incident with customer impact
- Recurring issues

### PIR Template

```markdown
# Post-Incident Review: [Title]

**Incident ID**: INC-20251001-001
**Date**: 2025-10-01
**Duration**: 10:30 - 12:15 UTC (1h 45m)
**Severity**: P0 - Critical
**Participants**: [Names]

## Summary
Brief description of what happened and impact.

## Timeline
- 10:30 - Alert triggered: Health check failed
- 10:32 - On-call acknowledged
- 10:35 - Investigation started
- 10:45 - Root cause identified: OOM kill
- 11:00 - Fix applied: Increased memory limit
- 11:15 - Service restored
- 12:15 - Monitoring complete, incident closed

## Impact
- **Users Affected**: 500
- **Duration**: 45 minutes
- **Revenue Impact**: $1,200
- **Requests Failed**: 1,250

## Root Cause
Application memory usage exceeded 2GB limit, causing OOM kill.
No alerts configured for memory pressure.

## What Went Well
- Fast detection (2 minutes)
- Quick acknowledgment
- Clear runbook procedures
- Good communication

## What Went Poorly
- No memory alerts
- No automatic restart
- Took 15 minutes to identify OOM
- No monitoring of memory trends

## Action Items
- [ ] Add memory usage alerts (Owner: DevOps, Due: 2025-10-05)
- [ ] Increase memory limit to 4GB (Owner: DevOps, Due: 2025-10-02)
- [ ] Add automatic restart policy (Owner: DevOps, Due: 2025-10-03)
- [ ] Update runbook with OOM section (Owner: On-Call, Due: 2025-10-02)
- [ ] Review all resource limits (Owner: Engineering, Due: 2025-10-10)

## Lessons Learned
- Memory limits should have headroom
- Need better monitoring of resource usage
- Automatic restarts prevent extended outages
```

---

## Common Commands Reference

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Database health
mongosh --eval "db.runCommand('ping')"

# Redis health (if used)
redis-cli ping

# Full system status
docker-compose ps
```

### Logs
```bash
# View application logs
docker-compose logs -f app

# View last 100 lines
docker-compose logs --tail=100 app

# Search logs
grep "ERROR" logs/ai_receptionist.log

# Follow logs in real-time
tail -f logs/ai_receptionist.log
```

### Restart Services
```bash
# Restart application
docker-compose restart app

# Restart database
docker-compose restart mongodb

# Restart all services
docker-compose restart

# Full restart
docker-compose down && docker-compose up -d
```

### Database Operations
```bash
# Connect to MongoDB
mongosh "mongodb://localhost:27017/ai_receptionist"

# Backup database
./scripts/deploy.sh production --backup

# Restore database
./scripts/deploy.sh production --rollback

# Check database size
mongosh
> use ai_receptionist
> db.stats()
```

### Monitoring
```bash
# Real-time metrics
watch -n 5 'curl -s http://localhost:8000/analytics/dashboard | jq ".l3_actions.success_rate"'

# Resource usage
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

---

**Document Version**: 1.0  
**Last Updated**: October 2025  
**Next Review**: January 2026  

**Maintained By**: DevOps Team  
**On-Call Schedule**: PagerDuty rotation