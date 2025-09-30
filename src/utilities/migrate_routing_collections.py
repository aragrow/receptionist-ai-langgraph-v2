# ==================== src/utilities/migrate_routing_collections.py ====================
"""
Database migration script for routing system.
Creates new collections and indexes needed for 3-tier agent routing.

Run this script after updating to the new routing system.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import CollectionInvalid
from config.settings import settings


class RoutingMigration:
    """Migration handler for routing system."""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.database.mongodb_url)
            self.db = self.client[settings.database.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {settings.database.database_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("📡 Disconnected from MongoDB")
    
    async def create_collections(self):
        """Create new collections for routing system."""
        print("\n" + "=" * 80)
        print("CREATING COLLECTIONS")
        print("=" * 80)
        
        collections_to_create = [
            {
                "name": "sessions",
                "description": "Session state storage for multi-turn conversations",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["session_id", "state_data", "created_at", "expires_at"],
                        "properties": {
                            "session_id": {"bsonType": "string"},
                            "state_data": {"bsonType": "object"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                            "expires_at": {"bsonType": "date"}
                        }
                    }
                }
            },
            {
                "name": "routing_logs",
                "description": "Routing decision logs for analytics",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["session_id", "from_tier", "to_tier", "timestamp"],
                        "properties": {
                            "session_id": {"bsonType": "string"},
                            "from_tier": {"bsonType": "string"},
                            "to_tier": {"bsonType": "string"},
                            "reason": {"bsonType": "string"},
                            "confidence": {"bsonType": "double"},
                            "timestamp": {"bsonType": "date"},
                            "metadata": {"bsonType": "object"}
                        }
                    }
                }
            },
            {
                "name": "escalation_tickets",
                "description": "Human escalation tickets",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["ticket_id", "session_id", "created_at"],
                        "properties": {
                            "ticket_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "escalation_reason": {"bsonType": "string"},
                            "priority": {"bsonType": "string"},
                            "status": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "resolved_at": {"bsonType": "date"}
                        }
                    }
                }
            }
        ]
        
        existing_collections = await self.db.list_collection_names()
        
        for coll_config in collections_to_create:
            name = coll_config["name"]
            
            if name in existing_collections:
                print(f"⏭️  Collection '{name}' already exists - skipping")
                continue
            
            try:
                # Create collection with validator
                await self.db.create_collection(
                    name,
                    validator=coll_config.get("validator")
                )
                print(f"✅ Created collection: {name}")
                print(f"   Description: {coll_config['description']}")
                
            except CollectionInvalid as e:
                print(f"⚠️  Collection '{name}' creation warning: {e}")
            except Exception as e:
                print(f"❌ Failed to create collection '{name}': {e}")
    
    async def create_indexes(self):
        """Create indexes for performance."""
        print("\n" + "=" * 80)
        print("CREATING INDEXES")
        print("=" * 80)
        
        indexes_to_create = [
            # Existing collections - improved indexes
            {
                "collection": "clients",
                "indexes": [
                    {"keys": [("phone", 1)], "name": "phone_idx"},
                    {"keys": [("email", 1)], "name": "email_idx"}
                ]
            },
            {
                "collection": "vendors",
                "indexes": [
                    {"keys": [("phone", 1)], "name": "phone_idx"},
                    {"keys": [("email", 1)], "name": "email_idx"}
                ]
            },
            {
                "collection": "agent_action_prompts",
                "indexes": [
                    {
                        "keys": [("agent", 1), ("action", 1), ("level", 1), ("active", 1)],
                        "name": "agent_action_level_active_idx"
                    },
                    {
                        "keys": [("agent", 1), ("action", 1), ("active", 1)],
                        "name": "agent_action_active_idx"
                    }
                ]
            },
            # New collections - indexes
            {
                "collection": "sessions",
                "indexes": [
                    {"keys": [("session_id", 1)], "name": "session_id_idx", "unique": True},
                    {"keys": [("created_at", 1)], "name": "created_at_idx"},
                    {"keys": [("expires_at", 1)], "name": "expires_at_idx"}
                ]
            },
            {
                "collection": "routing_logs",
                "indexes": [
                    {"keys": [("session_id", 1)], "name": "session_id_idx"},
                    {"keys": [("timestamp", -1)], "name": "timestamp_idx"},
                    {"keys": [("from_tier", 1), ("to_tier", 1)], "name": "tier_transition_idx"}
                ]
            },
            {
                "collection": "escalation_tickets",
                "indexes": [
                    {"keys": [("ticket_id", 1)], "name": "ticket_id_idx", "unique": True},
                    {"keys": [("session_id", 1)], "name": "session_id_idx"},
                    {"keys": [("status", 1)], "name": "status_idx"},
                    {"keys": [("created_at", -1)], "name": "created_at_idx"},
                    {"keys": [("priority", 1), ("status", 1)], "name": "priority_status_idx"}
                ]
            }
        ]
        
        for coll_config in indexes_to_create:
            collection_name = coll_config["collection"]
            collection = self.db[collection_name]
            
            print(f"\n📊 Creating indexes for '{collection_name}'...")
            
            for index_config in coll_config["indexes"]:
                try:
                    keys = index_config["keys"]
                    name = index_config["name"]
                    unique = index_config.get("unique", False)
                    
                    await collection.create_index(
                        keys,
                        name=name,
                        unique=unique
                    )
                    
                    unique_str = " (unique)" if unique else ""
                    print(f"   ✅ Created index: {name}{unique_str}")
                    
                except Exception as e:
                    # Index might already exist - that's okay
                    if "already exists" in str(e):
                        print(f"   ⏭️  Index '{name}' already exists - skipping")
                    else:
                        print(f"   ⚠️  Index creation warning: {e}")
        
        print("\n✅ All indexes processed")
    
    async def verify_setup(self):
        """Verify migration was successful."""
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        # Check collections
        collections = await self.db.list_collection_names()
        required_collections = ["sessions", "routing_logs", "escalation_tickets", "agent_action_prompts"]
        
        print("\n📋 Checking collections...")
        for coll in required_collections:
            if coll in collections:
                count = await self.db[coll].estimated_document_count()
                print(f"   ✅ {coll} (documents: {count})")
            else:
                print(f"   ❌ {coll} - NOT FOUND")
        
        # Check indexes on sessions
        print("\n📊 Checking indexes on 'sessions'...")
        indexes = await self.db.sessions.index_information()
        for idx_name, idx_info in indexes.items():
            print(f"   ✅ {idx_name}: {idx_info.get('key', [])}")
        
        # Check indexes on routing_logs
        print("\n📊 Checking indexes on 'routing_logs'...")
        indexes = await self.db.routing_logs.index_information()
        for idx_name, idx_info in indexes.items():
            print(f"   ✅ {idx_name}: {idx_info.get('key', [])}")
        
        # Check agent_action_prompts
        print("\n📝 Checking agent_action_prompts...")
        prompt_count = await self.db.agent_action_prompts.count_documents({})
        active_count = await self.db.agent_action_prompts.count_documents({"active": True})
        print(f"   Total prompts: {prompt_count}")
        print(f"   Active prompts: {active_count}")
        
        if active_count == 0:
            print("\n⚠️  WARNING: No active prompts found!")
            print("   Run: python src/utilities/seed_l1_prompts.py")
    
    async def seed_sample_data(self):
        """Optionally seed some sample data for testing."""
        print("\n" + "=" * 80)
        print("SEEDING SAMPLE DATA (OPTIONAL)")
        print("=" * 80)
        
        response = input("\nSeed sample session and routing log for testing? (y/n): ")
        
        if response.lower() != 'y':
            print("⏭️  Skipping sample data seeding")
            return
        
        # Sample session
        sample_session = {
            "session_id": "test-session-001",
            "state_data": {
                "caller_phone": "555-123-4567",
                "speech_text": "I need to schedule a cleaning",
                "current_tier": "L1"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        
        try:
            await self.db.sessions.insert_one(sample_session)
            print("✅ Inserted sample session: test-session-001")
        except Exception as e:
            print(f"⚠️  Sample session insert warning: {e}")
        
        # Sample routing log
        sample_routing_log = {
            "session_id": "test-session-001",
            "from_tier": "START",
            "to_tier": "L1",
            "reason": "Initial classification",
            "confidence": 0.92,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "intent": "scheduling",
                "caller_type": "client"
            }
        }
        
        try:
            await self.db.routing_logs.insert_one(sample_routing_log)
            print("✅ Inserted sample routing log")
        except Exception as e:
            print(f"⚠️  Sample routing log insert warning: {e}")
        
        print("\n✅ Sample data seeded successfully!")
        print("   You can query these using the DatabaseService methods")
    
    async def run_migration(self):
        """Run the complete migration."""
        print("\n" + "=" * 80)
        print("ROUTING SYSTEM DATABASE MIGRATION")
        print("=" * 80)
        print(f"Database: {settings.database.database_name}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("=" * 80)
        
        if not await self.connect():
            return False
        
        try:
            # Create collections
            await self.create_collections()
            
            # Create indexes
            await self.create_indexes()
            
            # Verify setup
            await self.verify_setup()
            
            # Optional: seed sample data
            await self.seed_sample_data()
            
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print("\nNext steps:")
            print("1. Run: python src/utilities/seed_l1_prompts.py")
            print("2. Test the routing system with sample calls")
            print("3. Monitor routing_logs collection for analytics")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            await self.disconnect()


async def rollback_migration():
    """Rollback migration (remove new collections)."""
    print("\n" + "=" * 80)
    print("⚠️  ROLLBACK MIGRATION")
    print("=" * 80)
    print("This will DELETE the following collections:")
    print("  - sessions")
    print("  - routing_logs")
    print("  - escalation_tickets")
    print()
    
    response = input("Are you sure? Type 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("❌ Rollback cancelled")
        return
    
    migration = RoutingMigration()
    
    if not await migration.connect():
        return
    
    try:
        collections_to_drop = ["sessions", "routing_logs", "escalation_tickets"]
        
        for coll_name in collections_to_drop:
            try:
                await migration.db[coll_name].drop()
                print(f"🗑️  Dropped collection: {coll_name}")
            except Exception as e:
                print(f"⚠️  Error dropping '{coll_name}': {e}")
        
        print("\n✅ Rollback completed")
        
    finally:
        await migration.disconnect()


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        await rollback_migration()
    else:
        migration = RoutingMigration()
        await migration.run_migration()


if __name__ == "__main__":
    asyncio.run(main())