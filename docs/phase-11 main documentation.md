# AI Receptionist System v2.0

**3-Tier Agentic Routing System for Intelligent Call Handling**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0+-green.svg)](https://www.mongodb.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

The AI Receptionist System is an intelligent call routing and handling platform that uses a **3-tier agent architecture** (L1 → L2 → L3) to classify caller intent, extract information, and execute domain-specific actions. The system supports:

- **Multi-turn conversations** with session management
- **Intelligent routing** based on confidence thresholds
- **Automated clarification** when information is missing
- **Human escalation** for complex cases
- **Real-time analytics** and monitoring
- **Domain-specific actions** (booking, billing, support, scheduling)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Level 1 (L1): Receptionist - Ultra-light Classifier        │
│  • Identifies broad intent (scheduling, billing, support)   │
│  • Detects caller type (client, prospect, partner)          │
│  • Confidence: 0-1.0                                         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────┴──────────────┐
        │   Confidence >= 0.75?       │
        └──────┬───────────────┬──────┘
               │ YES           │ NO
               │               │
               ▼               ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Route to L2         │  │  Ask Clarification   │
└──────┬───────────────┘  └──────────┬───────────┘
       │                             │
       │        ┌────────────────────┘
       │        │
       ▼        ▼
┌─────────────────────────────────────────────────────────────┐
│  Level 2 (L2): Intent Refiners (by caller type)             │
│  • Client L2: Existing client intents                        │
│  • Prospect L2: Sales/lead intents                           │
│  • Partner L2: Vendor/partner intents                        │
│  • Extracts entities & required slots                        │
│  • Generates clarification questions if needed               │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────┴──────────────┐
        │  All slots filled?          │
        └──────┬───────────────┬──────┘
               │ YES           │ NO
               │               │
               ▼               ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Route to L3         │  │  Clarification Loop  │
└──────┬───────────────┘  │  (max 2 attempts)    │
       │                  └──────────┬───────────┘
       │                             │
       │        ┌────────────────────┘
       │        │
       ▼        ▼
┌─────────────────────────────────────────────────────────────┐
│  Level 3 (L3): Domain Specialists                           │
│  • Sales Agent: Bookings, quotes, scheduling                │
│  • Support Agent: Tickets, complaints, issues               │
│  • Billing Agent: Invoices, payments, account questions     │
│  • Scheduling Agent: Reschedule, cancel, modify bookings    │
│  • Partner Agent: Vendor check-ins, updates                 │
│  • General Agent: FAQs, business info                       │
│  • Executes actions & returns confirmation                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────┴──────────────┐
        │  Action successful?         │
        └──────┬───────────────┬──────┘
               │ YES           │ NO
               │               │
               ▼               ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Return Result       │  │  Escalate to Human   │
└──────────────────────┘  └──────────────────────┘
```

## ✨ Key Features

### 🎭 3-Tier Agent System
- **L1 Receptionist**: Fast (<200ms), broad classification
- **L2 Intent Refiners**: Specialized by caller type, slot extraction
- **L3 Domain Agents**: Action execution with business logic

### 🔄 Intelligent Routing
- Confidence-based routing (thresholds: 0.75, 0.4)
- Automatic clarification loops (max 2 attempts)
- Human escalation for low confidence or complex cases
- Session continuity across multiple turns

### 📊 Analytics & Monitoring
- Real-time metrics dashboard
- L1/L2/L3 performance tracking
- Clarification and escalation statistics
- Structured JSON logging with full context
- CSV export for data analysis

### 🛡️ Production-Ready
- Session management with MongoDB
- Graceful error handling and retries
- Health check endpoints
- PII masking in logs
- Comprehensive test suite

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB 7.0+
- Google Gemini API key (or compatible LLM)

### Installation

```bash
# Clone repository
git clone 
cd ai-receptionist

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Configuration

Edit `.env` file:

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=ai_receptionist

# LLM Provider
GOOGLE_API_KEY=your_gemini_api_key_here
MODEL_NAME=gemini-2.0-flash-exp

# Routing Configuration
CONFIDENCE_THRESHOLD_HIGH=0.75
CONFIDENCE_THRESHOLD_MEDIUM=0.4
MAX_CLARIFICATIONS=2

# Session Management
SESSION_TTL_MINUTES=30
MAX_CONVERSATION_HISTORY=10

# Server
HOST=0.0.0.0
PORT=8000
```

### Database Setup

```bash
# Run database migration (creates collections and indexes)
python src/utilities/migrate_routing_collections.py

# Seed prompts for L1 agents
python src/utilities/seed_l1_prompts.py

# Seed prompts for L2 agents
python src/utilities/seed_l2_prompts.py

# Seed prompts for L3 agents (optional, if implemented)
python src/utilities/seed_l3_prompts.py

# Generate test data (optional)
python src/utilities/generate_test_data.py
```

### Run the Application

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Analytics Dashboard**: http://localhost:8000/dashboard

### Quick Test

```bash
# Test with curl
curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{
    "caller_phone": "+14155551234",
    "speech_text": "I need to schedule a cleaning for next Tuesday",
    "call_sid": "test-call-001"
  }'
```

## 📖 Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - Detailed system design
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and fixes
- **[Monitoring Guide](docs/MONITORING.md)** - Observability setup
- **[Operations Runbook](docs/RUNBOOK.md)** - On-call procedures

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_workflow.py
pytest tests/test_integration/

# Run with coverage
pytest --cov=src --cov-report=html

# Run end-to-end tests
pytest tests/test_e2e_scenarios.py -v
```

## 📊 Project Structure

```
ai-receptionist/
├── config/
│   └── settings.py              # Configuration management
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   ├── TROUBLESHOOTING.md
│   ├── MONITORING.md
│   └── RUNBOOK.md
├── logs/                        # Application logs (generated)
├── scripts/
│   ├── deploy.sh               # Deployment script
│   └── health_check.py         # Health check utility
├── src/
│   ├── actions/                # Domain actions (booking, billing, etc.)
│   ├── agents/                 # L1/L2/L3 agent implementations
│   ├── api/                    # API endpoints
│   │   └── analytics_endpoints.py
│   ├── models/                 # Data models
│   │   ├── agent_models.py     # Agent input/output models
│   │   ├── database_models.py  # MongoDB models
│   │   └── workflow_models.py  # Workflow state models
│   ├── nodes/                  # LangGraph nodes
│   │   ├── clarification_handler.py
│   │   ├── human_escalation.py
│   │   ├── receptionist_l1.py
│   │   ├── receptionist_l2_*.py
│   │   └── l3_*.py
│   ├── services/               # Business services
│   │   ├── context_service.py
│   │   ├── database_service.py
│   │   ├── embedding_service.py
│   │   ├── logging_service.py
│   │   ├── metrics_service.py
│   │   ├── routing_service.py
│   │   ├── session_service.py
│   │   ├── slot_filling_service.py
│   │   └── ticket_service.py
│   ├── utilities/              # Helper utilities
│   │   ├── generate_test_data.py
│   │   ├── migrate_routing_collections.py
│   │   ├── phone_utils.py
│   │   ├── pii_masking.py
│   │   ├── seed_l1_prompts.py
│   │   ├── seed_l2_prompts.py
│   │   └── text_processing.py
│   └── workflow/               # LangGraph workflow
│       ├── ai_receptionist_workflow.py
│       ├── routing_conditions.py
│       └── workflow_runner.py
├── templates/
│   └── analytics_dashboard.html
├── tests/                      # Test suites
│   ├── test_agents/
│   ├── test_integration/
│   ├── test_e2e_scenarios.py
│   └── test_performance.py
├── .env.example                # Environment template
├── .gitignore
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container definition
├── main.py                     # FastAPI application
├── pyproject.toml             # Project metadata
├── README.md                   # This file
└── requirements.txt            # Python dependencies
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` | Yes |
| `MONGODB_DB_NAME` | Database name | `ai_receptionist` | Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | - | Yes |
| `MODEL_NAME` | LLM model name | `gemini-2.0-flash-exp` | No |
| `CONFIDENCE_THRESHOLD_HIGH` | High confidence threshold | `0.75` | No |
| `CONFIDENCE_THRESHOLD_MEDIUM` | Medium confidence threshold | `0.4` | No |
| `MAX_CLARIFICATIONS` | Max clarification attempts | `2` | No |
| `SESSION_TTL_MINUTES` | Session expiration time | `30` | No |
| `MAX_CONVERSATION_HISTORY` | Max messages to retain | `10` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |

### Routing Configuration

Edit `config/settings.py` for advanced routing configuration:

```python
# Confidence thresholds
CONFIDENCE_HIGH = 0.75      # Auto-route to next tier
CONFIDENCE_MEDIUM = 0.4     # Ask clarification first
CONFIDENCE_LOW = 0.4        # Escalate to human

# Caller type to L2 agent mapping
CALLER_TYPE_L2_ROUTING = {
    CallerType.CLIENT: "client_receptionist_l2",
    CallerType.PROSPECT: "prospect_receptionist_l2",
    CallerType.PARTNER: "partner_receptionist_l2",
    CallerType.UNKNOWN: "general_receptionist_l2"
}

# Intent to L3 agent mapping
INTENT_L3_ROUTING = {
    "book_service": "sales_agent_l3",
    "reschedule": "scheduling_agent_l3",
    "billing_inquiry": "billing_agent_l3",
    "support_issue": "support_agent_l3",
    # ... more mappings
}
```

## 🔍 API Usage

### Process a Call

```bash
POST /call
Content-Type: application/json

{
  "caller_phone": "+14155551234",
  "speech_text": "I want to schedule a cleaning",
  "call_sid": "CA1234567890",
  "session_id": "optional-session-id"  # Optional, auto-generated if omitted
}
```

**Response:**

```json
{
  "response_text": "I'd be happy to help you schedule a cleaning! What date and time works best for you?",
  "session_id": "sess_abc123xyz",
  "intent": "book_service",
  "confidence": 0.92,
  "requires_clarification": true,
  "missing_slots": ["preferred_date", "address"],
  "current_tier": "L2",
  "processing_time_ms": 245,
  "routing_history": [
    {
      "from_tier": "L1",
      "to_tier": "L2",
      "agent": "client_receptionist_l2",
      "confidence": 0.92,
      "reason": "High confidence client scheduling intent"
    }
  ]
}
```

### Continue Conversation

```bash
POST /call
Content-Type: application/json

{
  "caller_phone": "+14155551234",
  "speech_text": "Next Tuesday at 2pm, 123 Main St",
  "call_sid": "CA1234567890",
  "session_id": "sess_abc123xyz"  # Use the session_id from previous call
}
```

### Get Session Details

```bash
GET /analytics/sessions/{session_id}
```

### View Analytics Dashboard

Open in browser:
```
http://localhost:8000/dashboard
```

## 📈 Monitoring

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "database": "connected",
  "session_service": "active",
  "uptime_seconds": 3600
}
```

### Metrics Endpoints

```bash
# Get L1 classification metrics
GET /analytics/l1/accuracy

# Get L2 refinement metrics
GET /analytics/l2/refinement

# Get L3 action metrics
GET /analytics/l3/actions

# Get escalation statistics
GET /analytics/escalations

# Export metrics as CSV
GET /analytics/export/csv?metric_type=sessions&time_window_hours=24
```

### Logs

Structured JSON logs are written to `logs/ai_receptionist.log`:

```json
{
  "timestamp": "2025-10-01T10:30:45.123Z",
  "level": "INFO",
  "event": "l1_classification",
  "session_id": "sess_abc123",
  "intent": "scheduling",
  "confidence": 0.92,
  "caller_type": "client",
  "processing_time_ms": 145.2
}
```

## 🚢 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Scale workers
docker-compose up -d --scale app=4
```

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python src/utilities/migrate_routing_collections.py

# Start with Gunicorn (production)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed production deployment guide.

## 🧩 Development

### Adding a New L3 Agent

1. Create agent file in `src/agents/`:

```python
from src.agents.l3_base_agent import L3BaseAgent

class MyNewAgentL3(L3BaseAgent):
    async def execute_action(self, state: WorkflowState) -> WorkflowState:
        # Your action logic here
        return state
```

2. Add prompts to database:

```python
# Add to src/utilities/seed_l3_prompts.py
{
    "agent_name": "my_new_agent_l3",
    "action_name": "my_action",
    "system_prompt": "Your system prompt here...",
    # ...
}
```

3. Update routing configuration in `config/settings.py`:

```python
INTENT_L3_ROUTING = {
    # ... existing mappings
    "my_new_intent": "my_new_agent_l3"
}
```

4. Run tests:

```bash
pytest tests/test_agents/test_my_new_agent_l3.py
```

### Code Style

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/
pylint src/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`pytest`)
- Code is formatted (`black` and `isort`)
- Documentation is updated
- Type hints are included

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- Powered by [FastAPI](https://fastapi.tiangolo.com/) for the REST API
- Uses [MongoDB](https://www.mongodb.com/) for data persistence
- LLM integration via [Google Gemini](https://ai.google.dev/)

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/ai-receptionist/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ai-receptionist/discussions)

## 🗺️ Roadmap

- [ ] Add support for additional LLM providers (OpenAI, Anthropic)
- [ ] Implement voice synthesis for outbound responses
- [ ] Add multi-language support
- [ ] Implement A/B testing framework for prompts
- [ ] Add fine-tuning pipeline for domain-specific models
- [ ] Implement advanced analytics with ML insights
- [ ] Add webhook support for external integrations
- [ ] Implement rate limiting and authentication

---

**Built with ❤️ for intelligent, scalable call handling**