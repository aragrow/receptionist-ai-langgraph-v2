# FrontEnd Project Requirements: MongoDB Data Model with AI Receptionist Integration

## Overview
The system will store data in MongoDB across several collections: **Clients**, **Properties**, **Jobs**, **Visits**, **Vendors**, and a **Knowledge Base**.  
An **AI receptionist** will leverage this data by retrieving and combining all relevant information for a given entity (client, property, job, visit, vendor) into a prompt/context for an LLM.  

The AI receptionist should be able to answer **client and vendor questions** while respecting access control rules.

---

## Relationships
- **Clients** have many **Properties**.
- **Properties** have many **Jobs**.
- **Jobs** have many **Visits**.
- **Jobs** are associated with a **Vendor**.
- **Vendors** can have many **Jobs**.

---

## Collections & Common Fields

### 1. Clients
- `_id` (string, unique across database)
- `name` (string)
- `email` (string)
- `phone` (string)
- `address` (string, e.g., street number)
- `address_1` (string, e.g., apartment/suite)
- `city` (string)
- `state` (string)
- `zip` (string)
- `country` (string)
- `notes` (string)

### 2. Properties
- `_id` (string, unique)
- `client_id` (string, reference to Clients._id)
- `address` (string, e.g., street number)
- `address_1` (string, e.g., apartment/suite)
- `city` (string)
- `state` (string)
- `zip` (string)
- `country` (string)
- `property_type` (string, e.g., residential, commercial)
- `size` (string, e.g., sqft or description)
- `notes` (string)

### 3. Jobs
- `_id` (string, unique)
- `property_id` (string, reference to Properties._id)
- `vendor_id` (string, reference to Vendors._id)
- `title` (string, short description of the job)
- `description` (string, details of the work)
- `status` (string, e.g., pending, in-progress, completed)
- `scheduled_date` (string, ISO date format)
- `completion_date` (string, ISO date format)
- `notes` (string)

### 4. Visits
- `_id` (string, unique)
- `job_id` (string, reference to Jobs._id)
- `visit_date` (string, ISO date format)
- `technician_name` (string)
- `report` (string)
- `status` (string, e.g., scheduled, completed, canceled)
- `notes` (string)

### 5. Vendors
- `_id` (string, unique)
- `name` (string)
- `contact_person` (string)
- `phone` (string)
- `email` (string)
- `address` (string, e.g., street number)
- `address_1` (string, e.g., suite/floor)
- `city` (string)
- `state` (string)
- `zip` (string)
- `country` (string)
- `service_type` (string, e.g., plumbing, electrical, landscaping)
- `notes` (string)

---

## Knowledge Base Collection

### knowledge_base
- `_id` (string, unique, references any entity across Clients, Properties, Jobs, Visits, Vendors)
- `content` (string, concatenated text from the entity’s fields)
- `embedding` (array of numbers, vector representation for search/retrieval)

---

## AI Receptionist Workflow

### Node-Based Flow

1. **Call Reception**  
   - Twilio receives incoming call.  
   - Caller’s voice digitized (speech-to-text).  
   - Sent to webhook for processing.  

2. **Identity Check**  
   - Lookup caller by phone in **Clients** and **Vendors** collections.  
   - If found → classify as **Client** or **Vendor**.  
   - If not found → classify as **Lead**.  

3. **Context Builder**  
   - **Client**: aggregate profile, properties, jobs, visits, vendors and KB entries.  
   - **Vendor**: aggregate profile, jobs, visits, clients and KB entries.  
   - **Lead**: limited KB access.  

4. **Intent/Goal Decider**  
   - If Client/Vendor → structured context passed to LLM.  
   - If Lead → analyze intent (sales inquiry, service request, general question).  

5. **Instruction Generator**  
   - LLM outputs response + next-step instruction.  
   - Response packaged into text for Twilio.  

6. **Digital-to-Voice Connector (DOV)**  
   - Response sent back to Twilio for TTS.  
   - Caller hears AI receptionist’s reply.  
   - Loop continues until call ends.  

7. **Logging & Post-Call Actions**  
   - Transcript saved to MongoDB.  
   - Caller metadata and updates stored.  
   - Trigger follow-up tasks (CRM update, human callback).  

---

## Access Control Rules
- **Clients**: can only access their own data (properties, jobs, visits, jobs vendors, and KB).  
- **Vendors**: can only access their own jobs, jobs clients,visits, and KB.  
- **Leads**: only general KB info.  
- **System/AI receptionist**: full access.  

---

## Technology Stack

### Core Runtime
- **Language**: Python  
- **Package Manager**: pip + uv  

#### Dependencies by category
    # Core dependencies
    aiofiles
    aiohappyeyeballs
    aiohttp
    aiosignal
    annotated-types
    anyio
    asyncio-throttle
    attrs
    backoff
    cachetools
    certifi
    charset-normalizer
    click
    colorama
    dill
    filetype
    frozenlist
    google-ai-generativelanguage
    google-api-core
    google-auth
    googleapis-common-protos
    gql
    graphql-core
    grpcio
    grpcio-status
    h11
    httpcore
    httpx
    idna
    jsonpatch
    jsonpointer
    langchain
    langchain-core
    langchain-google-genai
    langchain-text-splitters
    langgraph
    langgraph-checkpoint
    langgraph-prebuilt
    langgraph-sdk
    langsmith
    mando
    markdown-it-py
    mdurl
    multidict
    numpy
    orjson
    ormsgpack
    packaging
    pandas
    propcache
    proto-plus
    protobuf
    pyasn1
    pyasn1_modules
    pydantic
    pydantic-settings
    pydantic_core
    python-dateutil
    python-dotenv
    pytz
    PyYAML
    requests
    requests-toolbelt
    rich
    rsa
    six
    sniffio
    SQLAlchemy
    structlog
    tenacity
    typing-inspection
    typing_extensions
    tzdata
    urllib3
    uv
    xxhash
    yarl
    zstandard
    google.generativeai 

    #### Dev / Linting / Testing
    mypy
    mypy_extensions
    pathspec
    platformdirs
    tomlkit
    black
    isort
    flake8
    pylint
    mccabe
    pycodestyle
    pyflakes
    radon
    pytest
    pytest-asyncio
    pytest-mock


## App Hierarchy
    Root
        config
            settings.py
        src
            models
            nodes
            utilities
            services
            worflow
                workflow_runner.py
                    Workflow Runner for AI Receptionist.
                    Command-line interface and programmatic runner for the workflow.
                ai_receptionist_workflow.py
                    LangGraph workflow for AI Receptionist analysis.

# Code Intructions.

    I want to make sure that the nodes pass the state.  So create a model with the following class. BaseModel is a pydantic model:
        class WorkflowState(BaseModel):
            """Complete workflow state for PageSpeed Insights LangGraph workflow."""
    Make sure that the functions used are not going to be deprecated soon.
    Make sure that you use best practices when creating the code.
    Make sure that you use Object-Oriented Programming Practices.
    All data should be sanaized before being saved to the DB.
    All data should be escaped before displaying to the screen.
    Remove the Stop Words from the text to vectorize.
    I want to use google.generativeai to generate embeddings.  The model should be: models/text-embedding-004
    I want to use google.generativeai to chat with the data.  The model should be: gemini-2.5-flash-lite
    If the text to vectorize is over 1000 tokens, then break in chucks, with 100 tokens overlap.
    Make sure that v2 of pydantic is implemented
    Create test scripts using pytest to test all the functionality.  The tests must be controller by a single test service.
    Each test should return to the test service whether or not the test passed, if not return message too.


# Testing
    create a list with all the recomended tests to run before promoting to production.
    Use that list to create tests scripts, name them for what they do.
    Create a master test script controller to run all tests.  Report the results in nice tabulated table.
# App Hierchacy Output

 .env
 README.MD                                
 config/settings.py                       
 main.py                                  
 pyproject.toml                           
 src/models/database_models.py            
 src/models/workflow_models.py           
 src/nodes/context_builder.py            
 src/nodes/identity_checker.py            
 src/nodes/intent_analyzer.py            
 src/nodes/response_generator.py          
 src/services/context_service.py          
 src/services/database_service.py         
 src/services/embedding_service.py        
 src/utilities/phone_utils.py             
 src/utilities/text_processing.py         
 src/workflow/ai_receptionist_workflow.py 
 src/workflow/workflow_runner.py          
 tests/test_workflow.py                   
