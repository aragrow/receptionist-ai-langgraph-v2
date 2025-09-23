# ==================== README.md ====================
"""
# AI Receptionist System

A MongoDB-based AI Receptionist system with LangGraph workflow integration for automated call handling and customer service.

## Features

- **Caller Identification**: Automatically identify clients, vendors, or leads by phone number
- **Context Building**: Aggregate relevant data for personalized responses
- **Intent Analysis**: Understand caller needs and route appropriately
- **Access Control**: Respect data privacy rules for different caller types
- **LangGraph Integration**: Structured workflow processing with state management
- **MongoDB Storage**: Scalable document database for all entity relationships

## Architecture

### Collections
- **Clients**: Customer information and contact details
- **Properties**: Real estate properties linked to clients
- **Jobs**: Work orders and service requests
- **Visits**: Technician visits and service reports
- **Vendors**: Service provider information
- **Knowledge Base**: Vectorized content for AI responses

### Workflow Nodes
1. **Identity Checker**: Identifies caller type by phone lookup
2. **Context Builder**: Aggregates relevant data for the caller
3. **Intent Analyzer**: Determines caller's purpose/need
4. **Response Generator**: Creates appropriate responses with context

## Installation

### Prerequisites
- Python 3.11+
- MongoDB 7.0+
- pip and uv package managers

### Setup

1. **Clone and setup environment:**
```bash
git clone <repository>
cd ai-receptionist-system
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install uv
uv sync --dev
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start MongoDB:**
```bash
# Using Docker
docker-compose up mongodb -d

# Or install MongoDB locally
# https://docs.mongodb.com/manual/installation/
```

### Docker Setup

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Usage

### Command Line Interface

```bash
# Process a test call
python -m src.workflow.workflow_runner "+15551234567" "What's the status of my repair?"

# Run with minimal input
python -m src.workflow.workflow_runner "+15551234567"
```

### Programmatic Usage

```python
from src.workflow.workflow_runner import WorkflowRunner

runner = WorkflowRunner()

call_data = {
    "caller_phone": "+15551234567",
    "speech_text": "I need help with my property",
    "call_sid": "unique_call_id"
}

result = await runner.run_workflow(call_data)
print(result['response'])
```

## Data Model

### Entity Relationships
- Clients → Properties → Jobs → Visits
- Vendors → Jobs (many-to-many)
- Knowledge Base entries linked to any entity

### Access Control
- **Clients**: Own data only (properties, jobs, visits, related vendors)
- **Vendors**: Own jobs only (related clients, visits)
- **Leads**: General information only
- **System**: Full access

## Development

### Project Structure
```
ai-receptionist-system/
├── config/
│   └── settings.py          # Configuration management
├── src/
│   ├── models/             # Data models
│   ├── services/           # Business logic services
│   ├── nodes/              # LangGraph workflow nodes
│   ├── utilities/          # Helper functions
│   └── workflow/           # Main workflow logic
├── tests/                  # Test suite
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker services
└── README.md
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
pylint src/

# Type checking
mypy src/
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE__MONGODB_URL=mongodb://localhost:27017
DATABASE__DATABASE_NAME=ai_receptionist

# Twilio Integration
TWILIO__ACCOUNT_SID=your_account_sid
TWILIO__AUTH_TOKEN=your_auth_token
TWILIO__PHONE_NUMBER=your_phone_number

# LLM Configuration
LLM__GOOGLE_API_KEY=your_api_key
LLM__MODEL_NAME=gemini-pro
LLM__TEMPERATURE=0.7

# Text Processing
EMBEDDING__CHUNK_SIZE=1000
EMBEDDING__CHUNK_OVERLAP=100
```

## Security

- **Input Sanitization**: All user inputs are sanitized before database storage
- **Output Escaping**: All outputs are escaped to prevent XSS
- **Access Control**: Strict data access rules based on caller type
- **Data Privacy**: Customers can only access their own information

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation in `/docs`
- Review the test suite for usage examples

## Roadmap

- [ ] Twilio voice integration
- [ ] Advanced vector search for knowledge base
- [ ] Web dashboard for call analytics
- [ ] Multi-language support
- [ ] Advanced intent classification
- [ ] Integration with CRM systems
"""