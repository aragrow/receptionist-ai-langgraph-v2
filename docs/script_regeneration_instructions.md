# Instructions for Regenerating This Script with an LLM

## Summary
You will instruct an LLM to generate a Python script that:
- Loads configuration from environment variables (.env)
- Connects to MongoDB and ensures a database and collections exist
- Generates synthetic data for vendors, clients, properties, jobs, visits, and knowledge base
- Builds sentence-transformer embeddings from all object fields except _id
- Inserts the data into MongoDB
- Uses uv for dependency management

## Dependencies
- Python 3.9+
- uv (recommended)
- Packages:
  - faker
  - pymongo
  - python-dotenv
  - sentence-transformers

Install with:
```bash
uv add faker pymongo python-dotenv sentence-transformers
```

## Required environment variables (.env)
```bash
DATABASE__MONGODB_URL=mongodb://localhost:27017/
DATABASE__DATABASE_NAME=ai_receptionist
EMBEDDING__EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Regeneration Prompt (copy-paste into your LLM)
```
You are a senior Python engineer. Generate a single, runnable Python script that does all of the following:

1) Configuration
- Use python-dotenv to load a .env file (call load_dotenv() near the top).
- Read the following environment variables (with these defaults if missing):
  - MONGO_URI = os.getenv("DATABASE__MONGODB_URL", "mongodb://localhost:27017/")
  - DATABASE_NAME = os.getenv("DATABASE__DATABASE_NAME", "ai_receptionist")
  - EMBEDDING_MODEL = os.getenv("EMBEDDING__EMBEDDING_MODEL", "all-MiniLM-L6-v2")

2) Imports
- import uuid, random, os, json
- from datetime import datetime, timedelta
- import faker
- from pymongo import MongoClient
- from pymongo.errors import ConnectionFailure, CollectionInvalid
- from dotenv import load_dotenv
- from sentence_transformers import SentenceTransformer

3) Initialization
- Initialize faker: fake = faker.Faker()
- Initialize the embedding model: embedding_model = SentenceTransformer(EMBEDDING_MODEL)
- Define COLLECTIONS = ["vendors", "clients", "properties", "jobs", "visits", "knowledge_base"]

4) Database utilities
- create_database_and_collections(connection_string: str = MONGO_URI) -> MongoClient
  - Connect to MongoDB using the provided connection_string
  - Ping the server
  - Ensure database DATABASE_NAME exists
  - Ensure collections in COLLECTIONS exist (create if missing)
  - Return the MongoClient instance
  - Handle exceptions with clear print messages

- insert_data_to_mongodb(client, vendors, clients, properties, jobs, visits, kb)
  - Use the DATABASE_NAME from config
  - Optionally clear existing data (delete_many({})) before inserting
  - Insert each list into its respective collection
  - Print the number of inserted documents or a warning if list is empty

5) Data generators
- generate_guid() -> str (uuid4 string)
- generate_vendors(n=25) -> list[dict]
  - Fields: _id, name, contact_person, phone, email, address, address_1, city, state, zip, country="USA", service_type in {"residential_cleaning","commercial_cleaning"}, notes (randomized text)
- generate_clients(n=25, vendors=[]) -> tuple of lists (clients, properties, jobs, visits, kb)
  - Create client with typical contact fields + notes
  - For each client, generate 2-5 properties
  - For each property, 1-4 jobs with scheduled_date and optional completion_date
  - For each job, one visit reflecting scheduled/completed status
  - Add a KB entry for clients, properties, jobs, and visits with "content" and an empty "embedding" (or "embeddings") array

6) Embeddings
- add_embeddings_to_object(obj: dict) -> dict
  - Create a copy of obj, combine all fields except "_id" and "embeddings" into a single string "key: value" joined by " | "
  - Compute embedding with embedding_model.encode(text).tolist()
  - Save into obj_copy["embeddings"]
  - Return obj_copy

- add_embeddings_to_collection(collection_list: list[dict]) -> list[dict]
  - Map add_embeddings_to_object over the list

7) Main block
- Print a startup banner
- Call create_database_and_collections(connection_string=MONGO_URI)
- If client is truthy:
  - Generate all data with the generators
  - Print summary counts
  - Generate embeddings for all of these collections: vendors, clients, properties, jobs, visits
    - IMPORTANT: Use the embedded versions for insertion (e.g., vendors_with_embeddings, etc.)
  - Insert data into MongoDB (use the embedded versions; kb can remain with empty embeddings if you choose)
  - Close Mongo client and print success message
- Else print a connection failure message

8) Quality constraints
- The script must be a single file, runnable as `uv run python script.py`
- Use informative print statements with clear status indicators
- Keep function docstrings concise and clear
- Do not assume external files except .env
- Use the exact env var names specified above
- Avoid global state mutation where not needed; return values explicitly

9) Known pitfalls to avoid (ensure these are correct in the script):
- Call load_dotenv() so env variables load from .env
- Pass MONGO_URI to create_database_and_collections (don't hardcode "mongodb://localhost:27017/")
- Use the plural key "embeddings" when saving vectors
- When inserting into MongoDB, insert the *_with_embeddings versions (not the originals)
- Keep error handling around Mongo connection and insertion robust
```

## Acceptance Criteria
- Running `uv run python script.py`:
  - Connects to MongoDB using DATABASE__MONGODB_URL
  - Ensures database DATABASE__DATABASE_NAME exists with all collections
  - Generates data and prints counts
  - Builds embeddings for vendors, clients, properties, jobs, visits
  - Inserts embedded data into collections (counts printed)
  - Closes Mongo client without exceptions

## Quick Start Commands
- Create .env:
```bash
printf "DATABASE__MONGODB_URL=mongodb://localhost:27017/\nDATABASE__DATABASE_NAME=ai_receptionist\nEMBEDDING__EMBEDDING_MODEL=all-MiniLM-L6-v2\n" > .env
```
- Install deps and run:
```bash
uv add faker pymongo python-dotenv sentence-transformers
uv run python script.py
```

## Notes on Your Provided Code
- Call load_dotenv() to actually load env vars.
- In main(), you generated vendors_with_embeddings, etc., but the insert_data_to_mongodb call still passes the original vendors/clients/etc. Pass the with_embeddings versions to persist vectors.
- Consider passing MONGO_URI into create_database_and_collections instead of the hardcoded default.
- You used "embeddings" (plural) consistently in the new function—keep that consistent across the codebase.
