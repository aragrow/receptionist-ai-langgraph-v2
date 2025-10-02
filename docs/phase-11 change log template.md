# Changelog

All notable changes to the AI Receptionist System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Items that are added but not yet released

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in upcoming releases

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security improvements and vulnerability fixes

---

## [2.0.0] - 2025-10-01

### Added
- **3-Tier Agentic Routing System**: Complete implementation of L1 → L2 → L3 architecture
  - L1 Receptionist: Ultra-light intent classifier
  - L2 Intent Refiners: Specialized by caller type (Client, Prospect, Partner, General)
  - L3 Domain Specialists: Action-oriented agents (Sales, Support, Billing, Scheduling, Partner, General)
- **Session Management**: Multi-turn conversation support with MongoDB persistence
  - Session TTL and automatic cleanup
  - Conversation history tracking
  - Session continuity across multiple interactions
- **Intelligent Routing**: Confidence-based routing with automatic clarification and escalation
  - Configurable confidence thresholds (0.75, 0.4)
  - Maximum 2 clarification attempts before escalation
  - Routing history tracking
- **Telemetry & Analytics**: Comprehensive metrics collection and monitoring
  - Real-time analytics dashboard
  - L1/L2/L3 performance metrics
  - Clarification and escalation statistics
  - CSV export functionality
- **Deployment Infrastructure**: Production-ready deployment setup
  - Docker Compose orchestration
  - Multi-stage Dockerfile
  - Automated deployment script with backup/rollback
  - Health check endpoints
- **Documentation**: Complete documentation suite
  - README with quick start guide
  - Architecture documentation
  - API reference
  - Deployment guide
  - Troubleshooting guide
  - Operations runbook
  - Security guide
  - Contributing guide
- **Security Features**:
  - PII masking in logs
  - API key authentication support
  - Rate limiting
  - CORS configuration
  - Data retention policies

### Changed
- **Workflow Engine**: Migrated from linear workflow to LangGraph-based conditional routing
- **Database Schema**: Enhanced schema with new collections:
  - `sessions` - Session state storage
  - `routing_logs` - Routing decision tracking
  - `tickets` - Human escalation tickets
- **Response Format**: Enriched API responses with routing metadata and performance metrics
- **Configuration**: Centralized configuration in `.env` file with 100+ options

### Improved
- **Performance**: Optimized LLM token usage by reducing conversation history
- **Reliability**: Added graceful error handling and automatic retries
- **Observability**: Structured JSON logging with full context
- **Scalability**: Support for horizontal scaling with load balancing

### Fixed
- Database connection pooling issues
- Session expiration race conditions
- Memory leaks in long-running sessions
- Timezone handling for scheduled bookings

### Security
- Implemented PII masking for logs
- Added rate limiting to prevent abuse
- Enabled HTTPS/TLS support
- Configured secure defaults for production

---

## [1.0.0] - 2024-06-01

### Added
- Initial release of AI Receptionist System
- Basic call processing with single-tier workflow
- MongoDB integration for data persistence
- Google Gemini LLM integration
- Simple intent classification
- Context building from database
- Response generation
- FastAPI REST API
- Basic health check endpoint
- Docker support
- Initial documentation

### Features
- Linear workflow: Identity → Context → Intent → Response
- Client and vendor recognition
- Property and job lookup
- Basic conversation handling
- Logging infrastructure

---

## [0.5.0] - 2024-04-15 (Beta)

### Added
- Proof of concept implementation
- Database models for clients, properties, jobs, visits
- Embedding-based semantic search
- Basic LLM integration
- Test data generation
- Unit tests

### Changed
- Migrated from OpenAI to Google Gemini
- Simplified database schema

---

## Version History

| Version | Release Date | Major Changes |
|---------|--------------|---------------|
| 2.0.0 | 2025-10-01 | 3-tier routing, session management, analytics |
| 1.0.0 | 2024-06-01 | Initial release |
| 0.5.0 | 2024-04-15 | Beta release |

---

## Migration Guides

### Migrating from 1.0.0 to 2.0.0

**Breaking Changes**:
1. **Workflow Structure**: Linear workflow replaced with 3-tier routing
   - Action: Update any custom workflow integrations
   
2. **Database Schema**: New collections added
   - Action: Run migration script: `python src/utilities/migrate_routing_collections.py`
   
3. **API Response Format**: Additional fields in response
   - Action: Update API client to handle new fields

4. **Configuration**: New environment variables required
   - Action: Update `.env` file with new variables from `.env.example`

**Step-by-Step Migration**:

```bash
# 1. Backup your data
./scripts/deploy.sh production --backup

# 2. Stop the application
docker-compose down

# 3. Pull latest code
git pull origin main

# 4. Update environment
cp .env .env.backup
cat .env.example >> .env
nano .env  # Review and update new variables

# 5. Run migrations
python src/utilities/migrate_routing_collections.py
python src/utilities/seed_l1_prompts.py
python src/utilities/seed_l2_prompts.py

# 6. Deploy new version
./scripts/deploy.sh production --build

# 7. Verify
curl http://localhost:8000/health
```

**New Features to Leverage**:
- Enable session management for multi-turn conversations
- Use analytics dashboard for performance monitoring
- Configure confidence thresholds for your use case
- Set up automated escalation workflows

---

## Deprecation Notices

### Deprecated in 2.0.0
- **`/process` endpoint**: Use `/call` endpoint instead (will be removed in 3.0.0)
- **`identity_type` field**: Use `caller_type` instead (will be removed in 3.0.0)
- **Linear workflow**: Use 3-tier routing system (old workflow removed)

---

## Upgrade Notes

### 2.0.0 Upgrade Notes

**Performance**:
- Expected 30% improvement in response time due to optimized LLM calls
- Memory usage may increase by 20% due to session caching
- Recommend increasing worker count to 4 for production

**Configuration Changes**:
- New required env vars: `SESSION_TTL_MINUTES`, `MAX_CLARIFICATIONS`
- Renamed vars: `CONFIDENCE_THRESHOLD` → `CONFIDENCE_THRESHOLD_HIGH`
- New optional vars: `REDIS_ENABLED`, `PROMETHEUS_ENABLED`

**Database**:
- New indexes created automatically by migration script
- Expected database size increase: 15-20% due to new collections
- TTL indexes for automatic session cleanup

---

## Future Roadmap

### Planned for 3.0.0
- Multi-language support (Spanish, French, Mandarin)
- Voice synthesis for outbound responses
- Advanced analytics with ML-based insights
- A/B testing framework for prompts
- Fine-tuning pipeline for domain-specific models

### Under Consideration
- Integration with CRM systems (Salesforce, HubSpot)
- Calendar integration (Google Calendar, Outlook)
- Payment processing (Stripe, Square)
- Webhook support for external integrations
- GraphQL API alongside REST

---

## Contributors

### 2.0.0 Release
- [Your Name] - Lead Developer
- [Contributor 1] - L3 Agent Implementation
- [Contributor 2] - Analytics Dashboard
- [Contributor 3] - Documentation
- [Contributor 4] - Testing Infrastructure

### 1.0.0 Release
- [Your Name] - Initial Implementation

---

## Links

- **Repository**: https://github.com/your-org/ai-receptionist
- **Documentation**: https://docs.yourdomain.com
- **Issue Tracker**: https://github.com/your-org/ai-receptionist/issues
- **Releases**: https://github.com/your-org/ai-receptionist/releases

---

## Support

For questions about changes:
- **Email**: dev@yourdomain.com
- **Slack**: #ai-receptionist
- **GitHub Discussions**: https://github.com/your-org/ai-receptionist/discussions

---

**Format**: [Keep a Changelog](https://keepachangelog.com/)  
**Versioning**: [Semantic Versioning](https://semver.org/)  
**Last Updated**: October 2025