# Security Guide

Security policies, best practices, and compliance guidelines for the AI Receptionist System.

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Protection](#data-protection)
4. [Network Security](#network-security)
5. [API Security](#api-security)
6. [Compliance](#compliance)
7. [Security Best Practices](#security-best-practices)
8. [Incident Response](#incident-response)
9. [Security Checklist](#security-checklist)
10. [Reporting Vulnerabilities](#reporting-vulnerabilities)

---

## Security Overview

### Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimum necessary access rights
3. **Zero Trust**: Verify everything, trust nothing
4. **Privacy by Design**: Built-in privacy protections
5. **Security by Default**: Secure default configurations

### Threat Model

**Assets to Protect**:
- User PII (names, phone numbers, addresses)
- Conversation transcripts
- Business data (bookings, invoices)
- API keys and credentials
- System infrastructure

**Potential Threats**:
- Unauthorized data access
- Data breaches
- API abuse
- DDoS attacks
- SQL/NoSQL injection
- Man-in-the-middle attacks
- Insider threats

---

## Authentication & Authorization

### API Authentication

**Production Deployment** (Required):

```env
# Enable API key authentication
API_KEY_ENABLED=true
API_KEY=generate_secure_random_key_here
```

**Generate Secure API Key**:
```bash
# Generate 32-byte random key
openssl rand -hex 32
```

**Use API Key in Requests**:
```bash
curl -X POST http://localhost:8000/call \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

**Implementation** (main.py):
```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return credentials.credentials

@app.post("/call", dependencies=[Depends(verify_api_key)])
async def process_call(request: CallRequest):
    # Protected endpoint
    pass
```

### Service-to-Service Authentication

**MongoDB Authentication**:
```env
# Use strong passwords
MONGODB_URI=mongodb://username:strong_password@host:port/database

# For Atlas, use connection string with credentials
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

**Redis Authentication** (if used):
```env
REDIS_PASSWORD=strong_redis_password
REDIS_SSL=true
```

### User Authentication (Future)

For web dashboard access:

```python
# Implement JWT-based authentication
from fastapi_jwt_auth import AuthJWT

@app.post('/login')
def login(user: UserLogin, Authorize: AuthJWT = Depends()):
    # Verify credentials
    access_token = Authorize.create_access_token(subject=user.username)
    return {"access_token": access_token}

@app.get('/dashboard', dependencies=[Depends(verify_token)])
def dashboard():
    return FileResponse("templates/analytics_dashboard.html")
```

---

## Data Protection

### PII Protection

**Enable PII Masking**:
```env
PII_MASKING_ENABLED=true
PII_MASK_FIELDS=phone,email,ssn,credit_card,address
```

**Implementation** (src/utilities/pii_masking.py):
```python
import re

class PIIMasker:
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number: +14155551234 → +1415555****"""
        if len(phone) > 4:
            return phone[:-4] + "****"
        return "****"
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email: john@example.com → j***@example.com"""
        if "@" in email:
            local, domain = email.split("@")
            return f"{local[0]}***@{domain}"
        return "***"
    
    @staticmethod
    def mask_address(address: str) -> str:
        """Mask address: 123 Main St, Minneapolis → 123 Main St, ******"""
        parts = address.split(",")
        if len(parts) > 1:
            return f"{parts[0]}, ******"
        return "******"
    
    @staticmethod
    def mask_ssn(ssn: str) -> str:
        """Mask SSN: 123-45-6789 → ***-**-6789"""
        return re.sub(r'\d(?=\d{4})', '*', ssn)
    
    @staticmethod
    def mask_credit_card(cc: str) -> str:
        """Mask credit card: 1234567890123456 → ************3456"""
        return "*" * (len(cc) - 4) + cc[-4:] if len(cc) > 4 else "****"
```

### Data Encryption

**In Transit** (SSL/TLS):
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Additional security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

**At Rest** (Database):
```bash
# MongoDB encryption at rest
mongod --enableEncryption \
  --encryptionKeyFile /path/to/keyfile

# For MongoDB Atlas
# Encryption at rest is enabled by default
```

**Backup Encryption**:
```bash
# Encrypt backups with GPG
mongodump --archive | gpg --encrypt --recipient backup@yourdomain.com > backup.gz.gpg

# Decrypt when needed
gpg --decrypt backup.gz.gpg | mongorestore --archive
```

### Data Retention

**Configure Retention Policies**:
```env
# Automatic data cleanup
SESSION_RETENTION_DAYS=90
ROUTING_LOG_RETENTION_DAYS=365
TICKET_RETENTION_DAYS=730
LOG_FILE_RETENTION_DAYS=30

AUTO_CLEANUP_ENABLED=true
CLEANUP_SCHEDULE=0 2 * * *  # Daily at 2 AM
```

**Implementation** (src/services/retention_service.py):
```python
from datetime import datetime, timedelta, timezone

class RetentionService:
    async def cleanup_old_data(self):
        """Delete data past retention period"""
        cutoff_dates = {
            "sessions": datetime.now(timezone.utc) - timedelta(days=90),
            "routing_logs": datetime.now(timezone.utc) - timedelta(days=365),
            "tickets": datetime.now(timezone.utc) - timedelta(days=730),
        }
        
        for collection, cutoff in cutoff_dates.items():
            result = await db[collection].delete_many({
                "created_at": {"$lt": cutoff}
            })
            logger.info(f"Deleted {result.deleted_count} old records from {collection}")
```

### Right to be Forgotten (GDPR)

**Delete User Data Endpoint**:
```python
@app.delete("/users/{phone}/data")
async def delete_user_data(
    phone: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete all user data (GDPR compliance)"""
    # Delete from all collections
    await db.sessions.delete_many({"caller_phone": phone})
    await db.routing_logs.delete_many({"caller_phone": phone})
    await db.tickets.delete_many({"caller_phone": phone})
    
    # Anonymize in other collections
    await db.clients.update_one(
        {"phone": phone},
        {"$set": {"phone": "DELETED", "email": "DELETED", "name": "DELETED"}}
    )
    
    return {"status": "deleted", "phone": phone}
```

---

## Network Security

### Firewall Configuration

**Production Firewall Rules**:
```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (for redirect)
sudo ufw allow 80/tcp

# Allow SSH (from specific IPs only)
sudo ufw allow from YOUR_IP to any port 22

# Deny all other inbound
sudo ufw default deny incoming

# Allow all outbound
sudo ufw default allow outgoing

# Enable firewall
sudo ufw enable
```

### CORS Configuration

**Restrict Origins**:
```env
# .env
CORS_ENABLED=true
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE
CORS_ALLOW_HEADERS=Content-Type,Authorization
```

**Implementation**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORS