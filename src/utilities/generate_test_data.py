import uuid
import random
import faker
import os
import json
import sys
from bson import ObjectId

from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError, CollectionInvalid
from dotenv import load_dotenv

# NEW: Google embeddings
import google.generativeai as genai

# Load .env file into environment
load_dotenv()

# Configure Google AI
GOOGLE_API_KEY = os.getenv("LLM__GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is required in your environment (.env)")
genai.configure(api_key=GOOGLE_API_KEY)

# Database configuration from environment variables
MONGO_URI = os.getenv("DATABASE__MONGODB_URL", "mongodb://localhost:27017/")
print(MONGO_URI)  # consider masking in production
DATABASE_NAME = os.getenv("DATABASE__DATABASE_NAME", "ai_receptionist")

# You can still keep this var to switch providers if desired, but it isn't used by sentence-transformers anymore.
EMBEDDING_MODEL = os.getenv("EMBEDDING__EMBEDDING_MODEL", "models/text-embedding-004")
COLLECTIONS = ["vendors", "clients", "properties", "jobs", "visits", "knowledge_base"]

fake = faker.Faker()

# Embedding helper using Google text-embedding-004
EMBEDDING_DIM_FALLBACK = 768  # current dimension for text-embedding-004

def create_google_embedding(text: str) -> list[float]:
    """
    Create an embedding using Google's text-embedding-004.
    Returns a float vector; on error returns a zero vector fallback.
    """
    try:
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM_FALLBACK
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        # genai returns a dict-like with 'embedding'
        vec = response.get("embedding") if isinstance(response, dict) else getattr(response, "embedding", None)
        if isinstance(vec, list) and vec:
            return vec
        return [0.0] * EMBEDDING_DIM_FALLBACK
    except Exception as e:
        print(f"⚠️ Embedding failed: {e}")
        return [0.0] * EMBEDDING_DIM_FALLBACK

def create_database_and_collections(connection_string=None):
    print("Executing create_database_and_collections")
    """
    Create the database and collections for the AI receptionist system.
    
    Args:
        connection_string (str): MongoDB connection string
        
    Returns:
        MongoClient: MongoDB client instance
    """
    try:
        # Prefer env var if not provided
        connection_string = connection_string or MONGO_URI

        # Connect to MongoDB
        client = MongoClient(connection_string)
        
        # Test the connection
        client.admin.command('ping')
        print(f"✅ Connected to MongoDB successfully")
        
        # Get or create the database
        db = client[DATABASE_NAME]
        print(f"✅ Database '{DATABASE_NAME}' ready")
        
        # Create collections
        existing_collections = db.list_collection_names()
        
        for collection_name in COLLECTIONS:
            if collection_name not in existing_collections:
                db.create_collection(collection_name)
                print(f"✅ Created collection: {collection_name}")
            else:
                print(f"📋 Collection '{collection_name}' already exists")
        
        return client
        
    except ConnectionFailure as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating database/collections: {e}")
        return None

def insert_data_to_mongodb(client, vendors, clients, properties, jobs, visits, kb):
    print("Executing insert_data_to_mongodb")
    """
    Insert generated data into MongoDB collections.
    
    Args:
        client: MongoDB client instance
        vendors, clients, properties, jobs, visits, kb: Generated data lists
    """
    if not client:
        print("❌ No MongoDB client available")
        return
    
    try:
        db = client[DATABASE_NAME]
        
        # Clear existing data (optional - remove if you want to append)
        print("🗑️  Clearing existing data...")
        for collection_name in COLLECTIONS:
            db[collection_name].delete_many({})
        
        # Insert data
        collections_data = {
            "vendors": vendors,
            "clients": clients,
            "properties": properties,
            "jobs": jobs,
            "visits": visits,
            "knowledge_base": kb
        }
        
        for collection_name, data in collections_data.items():
            if data:
                result = db[collection_name].insert_many(data)
                print(f"✅ Inserted {len(result.inserted_ids)} documents into '{collection_name}'")
            else:
                print(f"⚠️  No data to insert into '{collection_name}'")
                
        print("🎉 All data inserted successfully!")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")

def generate_guid():
    return str(uuid.uuid4())

def generate_vendors(n=25):
    print("Executing generate_vendors")
    vendors = []
    for _ in range(n):
        vendors.append({
            "_id": ObjectId(),
            "name": fake.company(),
            "contact_person": fake.name(),
            "phone": fake.phone_number(),
            "email": fake.company_email(),
            "address": fake.street_address(),
            "address_1": fake.secondary_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip": fake.zipcode(),
            "country": "USA",
            "service_type": random.choice(["residential_cleaning", "commercial_cleaning"]),
            "notes": f"Business Hours: {get_vendor_business_hours()}. Services: {get_vendor_services()}"
        })
    return vendors

def generate_clients(n=25, vendors=[]):
    print("Executing generate_clients")
    clients, properties, jobs, visits, kb = [], [], [], [], []
    
    for _ in range(n):
        client_id = ObjectId()
        client_city = fake.city()
        client = {
            "_id": client_id,
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.street_address(),
            "address_1": fake.secondary_address(),
            "city": client_city,
            "state": fake.state_abbr(),
            "zip": fake.zipcode(),
            "country": "USA",
            "notes": get_client_notes()
        }
        clients.append(client)
        kb_id = ObjectId()
        kb.append({
            "_id": kb_id, 
            "entity_id": client_id,
            "content": f"Client {client['name']} in {client_city}. Notes: {client['notes']}",
            "embedding": []
        })

        # Properties
        for _ in range(random.randint(2, 5)):
            property_id = ObjectId()
            property_obj = {
                "_id": property_id,
                "client_id": client_id,
                "address": fake.street_address(),
                "address_1": fake.secondary_address(),
                "city": client_city,
                "state": fake.state_abbr(),
                "zip": fake.zipcode(),
                "country": "USA",
                "property_type": random.choice(["residential", "commercial", "residential/commercial"]),
                "size": f"{random.randint(800, 5000)} sqft",
                "notes": get_property_notes()
            }
            properties.append(property_obj)
            kb_id = ObjectId()
            kb.append({
                "_id": kb_id,
                "entity_id": property_id,
                "content": f"Property in {client_city}, type {property_obj['property_type']}, size {property_obj['size']}. Notes: {property_obj['notes']}",
                "embedding": []
            })

            # Jobs
            num_jobs = random.randint(1, 4)
            active_job_index = random.randint(0, num_jobs - 1)

            for j in range(num_jobs):
                job_id = ObjectId()
                vendor = random.choice([v for v in vendors if v["city"] == client_city] or vendors)
                scheduled_date = datetime.now() + timedelta(days=random.randint(1, 30))
                status = "in-progress" if j == active_job_index else "completed"

                job_obj = {
                    "_id": job_id,
                    "property_id": property_id,
                    "vendor_id": vendor["_id"],
                    "title": f"{random.choice(['Weekly', 'Bi-weekly', 'Monthly'])} Cleaning",
                    "description": random.choice([
                        "Full cleaning of kitchen, bathrooms, and living areas.",
                        "Deep cleaning of carpets and windows.",
                        "Office cleaning including meeting rooms and restrooms."
                    ]),
                    "status": status,
                    "scheduled_date": scheduled_date.isoformat(),
                    "completion_date": "" if status != "completed" else (scheduled_date + timedelta(days=1)).isoformat(),
                    "notes": get_job_notes()
                }
                jobs.append(job_obj)
                kb_id = ObjectId()
                kb.append({
                    "_id": kb_id,
                    "entity_id": job_id,
                    "content": f"Job {job_obj['title']} for property {property_id}. Status: {status}. Notes: {job_obj['notes']}",
                    "embedding": []
                })

                # Visits
                visit_id = ObjectId()
                visit_obj = {
                    "_id": visit_id,
                    "job_id": job_id,
                    "visit_date": scheduled_date.isoformat(),
                    "technician_name": fake.name(),
                    "report": "" if status != "completed" else "Job completed successfully.",
                    "status": "scheduled" if status == "in-progress" else "completed",
                    "notes": get_visit_notes()
                }
                visits.append(visit_obj)

                kb_id = ObjectId()
                kb.append({
                    "_id": kb_id,
                    "entity_id": visit_id,
                    "entity_type": "visit",
                    "content": f"Visit for job {job_id} on {visit_obj['visit_date']} by {visit_obj['technician_name']}. Status: {visit_obj['status']}. Notes: {visit_obj['notes']}",
                    "embedding": []
                })

    return clients, properties, jobs, visits, kb

def add_embeddings_to_object(obj):
    """
    Vectorize all fields in an object except '_id' and add to 'embeddings' field.
    Uses Google's text-embedding-004.
    """
    obj_copy = obj.copy()
    
    # Extract all fields except '_id' and 'embeddings'
    text_fields = []
    for key, value in obj.items():
        if key not in ['_id', 'embeddings']:
            text_fields.append(f"{key}: {str(value)}")
    
    combined_text = " | ".join(text_fields)
    embedding = create_google_embedding(combined_text)
    obj_copy['embeddings'] = embedding
    
    return obj_copy

def add_embeddings_to_collection(collection_list):
    print("Executing add_embeddings_to_collection")
    """
    Add embeddings to all objects in a collection.
    """
    return [add_embeddings_to_object(obj) for obj in collection_list]

def validate_client(client: MongoClient) -> None:
    try:
        client.admin.command("ping")
        _ = client.server_info()
        print("✅ MongoDB client connected (ping ok)")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ Cannot connect to MongoDB server: {e}")
        sys.exit(1)

def validate_database(client: MongoClient, db_name: str):
    try:
        db = client[db_name]
        _ = db.list_collection_names()
        print(f"✅ Database accessible: {db_name}")
        return db
    except OperationFailure as e:
        print(f"❌ Cannot access database '{db_name}': {e}")
        sys.exit(1)

def validate_collections(db, required_collections: list[str], test_write: bool = False):
    try:
        existing = set(db.list_collection_names())
        missing = [c for c in required_collections if c not in existing]
        if missing:
            print(f"⚠️ Missing collections (not yet created): {missing}")
        else:
            print("✅ All required collections exist")

        for name in required_collections:
            coll = db[name]
            try:
                _ = coll.estimated_document_count()
                print(f"✅ Readable collection: {name}")
            except OperationFailure as e:
                raise RuntimeError(f"❌ Cannot read collection '{name}': {e}")
        return True
    except Exception as e:
        print(f"❌ Error validating collections: {e}")
        sys.exit(1)

def get_client_notes():
    notes = [
        "Bill monthly and send invoice via email only. Requires supervisor check after each visit. Client requests lavender-scented air freshener provided in cabinet.",
        "Prefers Saturday morning cleanings. Has two cats — keep them indoors and do not use strong chemicals. Bathrooms must be stocked with toilet paper and soap after cleaning.",
        "Client pays via credit card on file. Avoid parking in driveway. Clean barbecue grill in summer months and store cover after cleaning.",
        "Windows to be cleaned quarterly. Dust blinds using microfiber wand only. Client works from home, avoid office area between 9–5 unless approved.",
        "Fragrance-free cleaning products required due to allergies. Remove fingerprints from stainless appliances weekly. Change bed linens every Friday.",
        "Send digital receipt immediately after payment. Collect recycling separately and leave outside by garage. Sanitize kitchen sink daily using vinegar-based spray.",
        "Requires special hardwood cleaner located in closet. Mop floors with hot water only. Deep clean carpets every 3 months using steam cleaner.",
        "Polish silverware monthly and store in designated cabinet. Sweep balcony weekly. Children’s bedrooms require toys organized by bins.",
        "Shoes off policy inside home. Client sensitive to noise, so use cordless vacuum only after 1 p.m. Clean dishwasher filter every 3 months.",
        "Client travels frequently. Leave checklist signed on counter. Always lock back door and test before leaving. Collect mail and place on kitchen counter.",
        "Garage and basement excluded from cleaning. Dust bookshelves with microfiber only. Client allergic to citrus cleaners — avoid lemon/orange products.",
        "Laundry service included every second visit. Fold clothes KonMari style. Restock guest bathroom towels from linen closet.",
        "Trash pickup on Fridays. Ensure bins are taken out Thursday evening. Sweep driveway once a month, especially in fall season.",
        "Clean ceiling fans monthly. Use stainless steel cleaner on appliances under sink. Refill water pitcher in fridge after each visit.",
        "Client expects arrival within 15 minutes of scheduled time. Notify if late. Keep thermostat set at 72°F and do not adjust settings.",
        "Polish wood banisters monthly with beeswax polish provided. Garage floor should be swept monthly with no chemicals. Clean under beds every visit.",
        "Client prefers direct phone calls, not texts. Always refill pet water bowls and follow feeding instructions. Vacuum sofa cushions every visit.",
        "Collect mail from mailbox and place on kitchen counter. Wipe down gym equipment with antibacterial wipes. Inspect smoke detectors quarterly.",
        "Avoid moving fragile items in living room. Deep clean oven and fridge monthly. Children’s playroom requires extra sanitizing of toys weekly.",
        "Client pays by check. Leave invoice in mail slot. Change bed linens every Friday. Dust blinds weekly and use microfiber wand.",
        "Always restock pantry items when low. Sweep outdoor patio once a month. Restock cleaning supplies from storage room as needed.",
        "Emergency contact listed in file. Call if unable to complete visit. Clean microwave inside and out every visit. Check fridge for expired food and discard.",
        "Avoid loud vacuums due to small dog. Client allergic to dust, so clean ceiling fans monthly. Use hypoallergenic detergent for linens.",
        "Vacuum carpets in cross pattern for living room rug. Dust bookshelves weekly with microfiber only. Leave signed cleaning log after each visit.",
        "Clean outdoor patio monthly. Wash balcony furniture in summer. Always park on street instead of driveway.",
        "Client requests quarterly deep cleaning of vents. Remove cobwebs from garage monthly. Clean barbecue grill in summer.",
        "Polish brass fixtures monthly with provided cleaner. Dust blinds every visit. Sweep driveway once a month.",
        "Pet litter box to be changed weekly. Dispose waste in outdoor bins. Sweep garage monthly. Do not adjust house alarm system.",
        "Client works night shifts. Avoid loud noise before 11 a.m. Collect recycling separately and restock towels in guest bathroom.",
        "Shoes off policy with disposable covers available. Clean microwave weekly. Children’s bedrooms must be tidy with toys in labeled bins.",
        "Clean under beds each visit. Use vinegar-based cleaner for bathrooms. Collect and place mail neatly on kitchen counter.",
        "Client allergic to strong scents. Use baking soda for deodorizing. Sanitize doorknobs and light switches each visit.",
        "Check windows for mold during rainy season. Sweep balcony weekly. Laundry to be folded neatly and stored in drawers.",
        "Always use client-provided mop from laundry room. Use lemon oil on dining table monthly. Refill water pitcher in fridge.",
        "Clean barbecue grill in summer months. Dust blinds carefully. Store fragile glass shades safely after cleaning light fixtures.",
        "Client requests quarterly carpet shampoo. Always arrive on time and confirm entry/exit times in app. Restock pantry when low.",
        "Client prefers eco-friendly supplies. Avoid bleach in bathrooms. Children’s playroom requires disinfecting toys weekly.",
        "Polish silverware monthly. Restock guest towels. Client sensitive to noise, use cordless vacuum after 1 p.m. only.",
        "Deep clean carpets every 6 months. Use hypoallergenic detergent for linens. Sweep outdoor patio monthly.",
        "Client supplies paper towels, use only their stock. Vacuum sofa cushions every visit. Collect recycling weekly.",
        "Shoes off policy. Restock cleaning supplies from storage. Clean behind appliances every 6 months.",
        "Always lock front and back doors. Remove cobwebs monthly. Client pays via credit card on file.",
        "Send invoice grouped by quarter. Clean light fixtures quarterly. Organize closets every 3 months.",
        "Wipe down gym equipment weekly. Sweep garage monthly. Avoid moving fragile items in living room.",
        "Client works from home. Avoid office 9–5. Dust blinds weekly. Restock bathroom supplies each visit.",
        "Client prefers lavender air freshener. Sweep balcony weekly. Laundry folded KonMari style.",
        "Trash bins must go out Thursday evening. Collect mail daily. Client allergic to citrus cleaners.",
        "Check smoke detectors quarterly. Clean ceiling fans monthly. Vacuum sofa cushions and rotate monthly.",
        "Sweep driveway monthly. Collect recycling separately. Restock guest bathroom towels every visit.",
        "Client requests photos of home after cleaning when traveling. Store signed checklist in kitchen drawer."
        ]
    return random.choice(notes)

def get_property_notes():

    notes = [
        "Small pets on premises. Requires key pickup at concierge. Alarm code provided separately.",
        "Parking available in underground garage. Elevator access requires fob. Concierge must be notified before arrival.",
        "Property has steep driveway. Please park on street. Gate code will be texted before arrival.",
        "Security cameras in use throughout property. Alarm code provided. Client requests notification upon entry and exit.",
        "Requires key collection from lockbox at side gate. Lockbox code changes monthly. Always relock after use.",
        "Unit located on 12th floor. Use service elevator only. Concierge will provide visitor badge at desk.",
        "Dogs on property, kept in backyard. Ensure gates are closed. Avoid using side gate — only use main entrance.",
        "Requires garage remote for entry. Remote must be returned to storage room. Street parking not permitted.",
        "Property has pool in backyard. Extra caution required when staff present. Clean pool deck once monthly.",
        "Alarm system armed between visits. Code and instructions provided. Notify client immediately if alarm is triggered.",
        "Requires shoe covers before entering property. Additional covers provided inside foyer. Hardwood floors sensitive to scratches.",
        "Rural property with long dirt road. Use GPS coordinates provided. Cell service may be limited in area.",
        "Key must be collected from property manager office two blocks away. Return same day after visit.",
        "Requires guardhouse check-in. Provide company ID and sign logbook. Guards will escort to unit if needed.",
        "Property has locked basement. Access permitted only with client approval. Basement not part of cleaning scope.",
        "Elevator is out of service frequently. Be prepared to use stairs for access. Notify office if elevator is non-functional.",
        "Garage contains hazardous chemicals. Do not enter or store supplies inside garage. Use outdoor storage shed if needed.",
        "Gate entry requires phone call to intercom. Dial client’s extension for access. Do not share gate code.",
        "Water shutoff valve located in basement. Client requests staff note any leaks or drips during cleaning.",
        "Construction ongoing in neighboring property. Limited parking available. Enter via alleyway entrance only.",
        "Property has heavy traffic around school zone. Allow extra travel time. Avoid arrival during school dismissal hours.",
        "Client requests all deliveries and mail placed on kitchen counter. Packages often left at concierge desk.",
        "Requires pickup of keys from cleaning supervisor each morning. Keys to be returned by end of day.",
        "Property has solar panels on roof. Do not allow anyone access. Avoid spraying roof with water during outdoor cleaning.",
        "Septic system on property. Only flush paper products. Notify client immediately if toilets back up.",
        "Balcony doors must remain locked after cleaning. Report any issues with sliding doors or latches.",
        "Unit part of gated condo complex. Visitor parking is limited to two hours. Ticketing enforced strictly.",
        "Heating system located in attic. Avoid entering furnace room. Report if unusual noises are noticed.",
        "Client requests plants watered weekly. Use filtered water only. Plants located in living room and balcony.",
        "Alarm keypad near front door. Must disarm immediately after entry. Failure will trigger security company call.",
        "Trash must be taken to community dumpster at far end of lot. Do not leave bags outside unit.",
        "Property has smart locks. Access requires phone app. Ensure Wi-Fi is connected before entry attempt.",
        "Building requires staff to sign waiver at management office. Keep copy of signed waiver on file.",
        "Garage used for storage only. Do not move boxes. Pathways should remain clear for safety.",
        "Property has historic wood floors. Use only microfiber mops. No water-based solutions permitted.",
        "Client requests blinds remain fully closed after cleaning. Do not leave windows open under any circumstances.",
        "Pool equipment in shed behind garage. Do not tamper. Client handles pool maintenance separately.",
        "Requires double locking procedure when leaving. Confirm both deadbolt and knob lock engaged.",
        "Unit located in mixed-use building. Noise must be kept to a minimum during business hours.",
        "Property has multiple access gates. Use north gate only. South gate reserved for deliveries.",
        "Mailbox shared with multiple tenants. Ensure client’s mail is separated and placed inside unit.",
        "Balcony railing is loose. Avoid leaning or placing weight against railing. Report any safety hazards.",
        "Building requires background check for all service providers. ID badge must be worn at all times.",
        "Client stores valuables in master bedroom safe. Do not attempt to move safe or surrounding furniture.",
        "Elevator requires service key. Concierge will provide temporary key at front desk. Return immediately after use.",
        "Unit above commercial restaurant. Strong odors may linger. Ensure extra attention to air freshening.",
        "Main gate closes automatically at 8 p.m. Ensure staff have exited before closing time.",
        "Property has koi pond in backyard. Do not feed fish. Avoid spilling cleaning supplies near water.",
        "Keypad entry may fail in rain. Backup keys stored in lockbox under porch. Code provided separately.",
        "Property located in flood zone. Check for water intrusion in basement after storms.",
        "Requires removal of shoes inside. Slippers provided. Carpets are antique and highly delicate.",
        "Client requests garage to remain locked at all times. Entry permitted only with owner approval.",
        "Visitor parking requires hang tag displayed in car. Tag located on kitchen counter.",
        "Roof access prohibited. Report any signs of roof leaks or water damage.",
        "Shared laundry facilities in basement. Do not use machines during cleaning.",
        "Smart thermostat should not be adjusted. Client monitors remotely via app.",
        "Balcony prone to pigeon droppings. Sweep weekly and report infestations.",
        "Unit has water softener system. Check salt levels monthly and notify client.",
        "Requires passcode for building lobby entry. Passcode changes every 90 days.",
        "Client requests driveway gate remain closed at all times. Neighbors have complained of open gates.",
        "House has multiple staircases. Use main staircase only. Secondary staircase reserved for family.",
        "Elevator is oversized freight type. Staff may use only with concierge approval.",
        "Community pool area requires wristband. Cleaning does not include pool deck unless authorized.",
        "Key to property stored in office safe. Pickup required before first visit of day.",
        "Unit has electric car charging station. Do not block charger with vehicle.",
        "Building manager requires insurance certificate on file for service providers.",
        "Property includes wine cellar in basement. Do not adjust temperature or move bottles.",
        "Client requests garage door not be opened during service. Noise disturbs neighbors.",
        "Garden tools stored in outdoor shed. Lock after use. Report if tools missing.",
        "Balcony doors have faulty locks. Confirm secure before leaving property.",
        "Fireplace is decorative only. Do not remove items from mantle or hearth.",
        "Main entrance steps icy in winter. Use caution when entering property.",
        "Community HOA prohibits use of loud equipment after 6 p.m. Be mindful of schedule.",
        "Client keeps pets in separate locked room. Do not attempt entry. Room excluded from cleaning.",
        "Water filter in kitchen sink requires replacement every 3 months. Notify client if past due.",
        "Unit located near construction site. Dust levels higher than normal — extra vacuuming required.",
        "Building requires QR code check-in via mobile app. Staff must scan code on entry and exit.",
        "Client requests deliveries left in garage. Packages must not be left outside gate.",
        "Outdoor lighting on timer system. Do not adjust switches. Report if bulbs are out.",
        "Security guard will escort staff to property. Sign visitor logbook on entry and exit.",
        "Home office contains sensitive documents. Do not touch papers. Dust surface only.",
        "Balcony doors prone to drafts. Ensure they are sealed after cleaning.",
        "Client requests thermostat remain at 70°F year-round. Confirm setting before leaving.",
        "Neighborhood parking limited. Use public garage two blocks away when street spots unavailable.",
        "Property requires entry through back alley. Do not use front driveway per HOA rules.",
        "Unit equipped with motion sensors. Notify client if false alarms occur.",
        "Client requests fridge water filter monitored. Replace if red light indicator shows.",
        "House has multiple outdoor fountains. Clean bird droppings from edges monthly.",
        "Building concierge requires phone call before staff arrival. Confirm via intercom on entry.",
        "Garage contains luxury vehicles. Do not lean supplies on cars or touch interiors.",
        "Unit includes private rooftop terrace. Sweep and clear debris once monthly.",
        "Property requires double key system — one for gate, one for front door. Both must be returned.",
        "Community requires visitor parking permits. Ensure permit visible at all times.",
        "Client requests exterior doormats shaken out weekly. Replace if damaged.",
        "Unit located at end of hallway. Noise travels easily. Keep voice levels low.",
        "Home has septic alarm system. Report any flashing lights or alarms immediately.",
        "Mailbox is locked. Use key stored on kitchen counter. Return key after use.",
        "Client stores valuables in attic. Attic off-limits to staff. Do not enter.",
        "Unit in senior living complex. Be respectful of quiet hours between 7 p.m. and 8 a.m.",
        "Property landscaping done by third-party vendor. Do not water or move plants outdoors."
    ]

    return random.choice(notes)

def get_job_notes():

    notes = [
        "Job scheduled for Mondays at 9 a.m. Requires eco-friendly supplies. Leave detailed checklist signed by staff.",
        "Deep clean requested every second Friday. Focus on bathrooms and kitchen. Supervisor must approve before leaving.",
        "Windows to be cleaned only on exterior. Client provides ladder. Safety gear required for second floor.",
        "Job requires two cleaners minimum. Staff rotation not allowed without client approval. Log arrival times.",
        "Use fragrance-free products due to allergies. Vacuum under all furniture. Report pet hair accumulation.",
        "Monthly carpet shampoo included. Drying fans required after service. Notify client before starting.",
        "Clean refrigerator interior once per month. Discard expired items only with client confirmation.",
        "Job requires supervisor inspection. Pictures to be uploaded for quality control. Staff to clock out only after approval.",
        "All garbage must be placed in community dumpster. Recycling must be separated and logged weekly.",
        "Clean oven once monthly. Use only non-abrasive cleaner. Document before/after pictures for client.",
        "Job involves sanitizing all doorknobs and switches. Extra attention to shared workspaces. Supplies restocked as needed.",
        "Requires disinfection of gym equipment. Client requests all machines wiped down with alcohol-based solution.",
        "Clean balcony tiles monthly. Use mop with mild detergent. Ensure sliding doors remain locked after service.",
        "Dusting required on high ceiling fans. Extension poles provided by staff. Safety check before use.",
        "Client requests washing machine cleaned every quarter. Run hot cycle with cleaning tablets provided.",
        "Job includes interior window cleaning every visit. Do not remove window screens. Use microfiber only.",
        "Garage must be swept monthly. Avoid moving heavy items. Photograph storage area after cleaning.",
        "Job requires flexible hours due to client schedule. Confirm via text message night before each visit.",
        "Client provides supplies stored in laundry room. Use only designated products. Reorder list updated weekly.",
        "Kitchen requires deep cleaning every 2 weeks. Focus on grout and backsplash. Upload progress pictures.",
        "Bathrooms must be restocked with toilet paper. Client keeps supplies in hallway closet. Note any shortages.",
        "Clean office desks but avoid moving papers. Dust electronics with microfiber cloth only. No liquid sprays near devices.",
        "Job requires security alarm reset after cleaning. Ensure alarm armed before leaving property.",
        "Client requests pet bowls cleaned daily. Replace water bowls. Sweep around feeding area thoroughly.",
        "Job includes cleaning patio furniture. Cover furniture after cleaning. Report damage if found.",
        "Job requires sanitizing air vents monthly. Use vacuum attachment only. Do not remove covers.",
        "Client requests all mirrors polished weekly. Use streak-free spray only. Avoid spraying directly on frames.",
        "Restock kitchen with client-provided bottled water. Note any missing deliveries. Place cases in pantry.",
        "Job includes dusting bookshelves. Do not rearrange items. Clean around decorative objects carefully.",
        "Client requires sanitization of children’s playroom. Focus on toys and mats. Use non-toxic cleaner.",
        "Job scheduled on alternating Saturdays. Provide staff of 3 cleaners. Minimum 4 hours per session.",
        "Clean light fixtures monthly. Use ladder for chandelier. Gloves required to avoid fingerprints.",
        "Clean under beds and behind sofas monthly. Move furniture carefully. Replace everything as found.",
        "Client requests vacuuming upholstery. Use handheld vacuum with brush attachment. Focus on pet hair removal.",
        "Job requires polishing stainless steel appliances. Use client-provided polish. Avoid abrasive sponges.",
        "Client requests outdoor grill cleaned quarterly. Use degreaser provided. Document cleaning steps.",
        "Bathrooms require mold inspection weekly. Notify office of any visible growth. Use bleach only if approved.",
        "Job requires documenting supply usage. Record products used in log sheet. Submit weekly to office.",
        "Client requests laundry folded and placed in baskets. Do not put clothes away in drawers.",
        "Job requires staff to water balcony plants. Use filtered water. Note plant health monthly.",
        "Clean office conference table weekly. Polish with wood conditioner. Do not use harsh chemicals.",
        "Client requests beds made with hotel-style fold. Pillows fluffed and arranged. Send photos for review.",
        "Job requires sweeping garage entrance. Leaves often accumulate. Report any oil spills or stains.",
        "Client requests extra care for antique furniture. Use furniture polish only. Avoid moving heavy pieces.",
        "Job requires wiping baseboards bi-weekly. Kneepads recommended for staff comfort. Document with checklist.",
        "Client requests coffee machine cleaned weekly. Rinse all removable parts. Refill water reservoir.",
        "Job requires sanitizing remote controls and phones. Use disinfectant wipes. Avoid leaving surfaces wet.",
        "Client requests interior trash cans lined after each cleaning. Replace liners even if unused.",
        "Job requires reporting maintenance issues. Document leaks, broken tiles, or damaged fixtures.",
        "Client requests staff wear uniforms and name badges. Arrival must be logged with concierge.",
        "Job requires end-of-service checklist. Supervisor signature mandatory. Email sent to client after approval."
    ]
    
    return random.choice(notes)

def get_visit_notes():

    notes = [
        "Arrived on time. Client requested additional focus on kitchen counters. Completed checklist and confirmed with client.",
        "Entry via concierge desk. Concierge requested staff sign in and out. Visit took 2 hours.",
        "Alarm code entered successfully. Reset before leaving. No issues reported.",
        "Client not home. Gained entry via lockbox. Lockbox code changed — update required.",
        "Client requested cleaning of balcony in addition to regular tasks. Added 30 minutes to visit.",
        "Dog was present on property. Secured pet in backyard during cleaning. Returned to original area before leaving.",
        "Client asked for additional dusting in home office. Avoided moving documents as instructed.",
        "Found small water leak in bathroom sink. Reported to office for maintenance follow-up.",
        "Arrived 15 minutes early. Waited until scheduled time per client request. Notified office of early arrival.",
        "Client requested supervisor walk-through at end of visit. Supervisor confirmed checklist complete.",
        "Key pickup from concierge went smoothly. Concierge required ID verification before key handover.",
        "Trash bins were overflowing. Removed and replaced all liners. Took garbage to community dumpster.",
        "Used client-provided supplies for bathroom cleaning. Refilled spray bottles after use.",
        "Client requested window cleaning skipped this visit. Focused extra time on vacuuming carpets.",
        "Alarm triggered on entry due to incorrect code. Client resolved remotely. No further issues.",
        "Noted mold spots starting in shower grout. Informed office for documentation.",
        "Client requested additional attention to children’s play area. Sanitized toys and mats thoroughly.",
        "Client was present and walked through cleaning expectations. Adjusted visit plan accordingly.",
        "Garage door remote malfunctioned. Entered via side gate. Reported issue to office.",
        "Client asked for plants to be watered during visit. Completed using filtered water as requested.",
        "Supervisor conducted random spot check during visit. Found work satisfactory.",
        "Staff wore shoe covers as required. Hardwood floors polished. Client expressed satisfaction.",
        "Completed deep clean in 3.5 hours. Added additional vacuuming of rugs due to pet hair.",
        "Client requested assistance moving small furniture to clean underneath. Returned items afterward.",
        "Supplies were low. Noted to office for replenishment before next visit.",
        "Client requested bed linens changed. Used fresh set provided in laundry room.",
        "Client asked to avoid using upstairs bathroom. Cleaned all other bathrooms as normal.",
        "Inspection of refrigerator revealed expired food. Did not discard — awaiting client instructions.",
        "Children were present in home. Staff worked quietly and avoided playroom until children left.",
        "Client requested polishing of stainless steel appliances. Completed using provided polish.",
        "Access delayed due to locked gate. Waited 20 minutes before gaining entry.",
        "Client asked for extra attention on balcony glass doors. Completed streak-free cleaning.",
        "No one available for checkout. Left note for client with summary of completed tasks.",
        "Client requested laundry folded but not put away. Placed baskets neatly in laundry room.",
        "Extra trash generated from client’s event. Took longer than scheduled. Reported overtime.",
        "Neighbor complained about noise during visit. Staff reduced vacuum use temporarily.",
        "Supplies closet reorganized for easier access. Client appreciated the adjustment.",
        "Supervisor noted excellent completion. No corrective actions required.",
        "Garage sweeping requested. Collected debris near entrance. Notified client of oil stain.",
        "Client requested thermostat remain untouched. Verified temperature at end of visit.",
        "Client requested return visit scheduled earlier in the week. Adjusted scheduling accordingly.",
        "Staff encountered parking difficulty. Parked two blocks away. Delayed arrival by 10 minutes.",
        "Client requested additional sanitization of doorknobs and light switches. Completed per request.",
        "Vacuum malfunctioned. Used backup equipment. Reported maintenance need to office.",
        "Client expressed concern about dust on blinds. Staff scheduled extra attention for next visit.",
        "Client requested skipping one bathroom this week. Focus shifted to kitchen deep clean.",
        "Staff found pet accident on rug. Cleaned using enzymatic spray. Notified client.",
        "Client requested end-of-visit call. Staff phoned before leaving to confirm satisfaction.",
        "Visit included cleaning of outdoor furniture. Covered with tarps afterward as requested.",
        "Client provided positive feedback. Requested same staff for next scheduled visit."
    ]
    return random.choice(notes)

def get_vendor_business_hours():
    notes= [
        "Standard janitorial services available Monday–Friday, 8 a.m.–6 p.m. Weekend work requires prior approval.",
        "Emergency cleaning crews available 24/7 for water damage, fire cleanup, or biohazard incidents.",
        "Overnight cleaning available for commercial offices. Crews typically operate between 10 p.m. and 6 a.m.",
        "Vendor offers Saturday service for recurring residential clients. No Sunday operations unless emergency.",
        "Holiday closures include Thanksgiving, Christmas, and New Year’s Day. Emergency crews remain on-call.",
        "Peak demand occurs at end-of-month for move-out cleanings. Requests must be submitted two weeks ahead.",
        "Vendor offers early morning service starting at 6 a.m. for retail stores before opening hours.",
        "Summer hours extended: crews available until 9 p.m. for exterior and window cleaning jobs.",
        "Winter weather delays possible. Snow or ice may shift job start times by up to 2 hours.",
        "Special event cleanup available outside regular business hours. Requires booking at least 5 days in advance.",
        "Recurring office cleaning contracts allow for flexible scheduling — mornings, evenings, or overnight.",
        "Crews typically scheduled in 4-hour minimum blocks. Additional hours billed at overtime rate.",
        "Holiday week schedules are adjusted. Vendor confirms time changes with clients at least 7 days prior.",
        "Overnight crews require building access approval. Clients must ensure alarm codes and keys are active.",
        "Emergency callouts during off-hours billed at double standard hourly rate.",
        "Vendor adjusts start times seasonally to maximize daylight for exterior cleaning jobs."
    ]
    return random.choice(notes)

def get_vendor_services():
    notes= [
        "Provides carpet and upholstery deep cleaning. Uses hot water extraction machines. Requires 24-hour drying period.",
        "Specializes in window cleaning for high-rise apartments. Staff are certified for rope and harness safety.",
        "Offers eco-friendly house cleaning. Uses only biodegradable, non-toxic products. Requires client-supplied vacuum.",
        "Handles post-construction cleanup. Includes debris removal, dust control, and floor polishing.",
        "Provides commercial office cleaning. Includes nightly trash removal, desk sanitization, and floor vacuuming.",
        "Vendor specializes in floor strip and wax for vinyl and linoleum. Requires cleared areas before service.",
        "Offers pressure washing for sidewalks, driveways, and patios. Service dependent on weather conditions.",
        "Handles deep kitchen cleaning. Includes oven degreasing, exhaust hood scrubbing, and floor sanitization.",
        "Provides move-in/move-out cleaning. Full unit detail including appliances, cabinets, and windows.",
        "Specializes in tile and grout restoration. Uses steam cleaning and sealing. Requires 2 hours curing time.",
        "Offers recurring residential maid service. Weekly or bi-weekly scheduling available. Supplies included.",
        "Handles janitorial services for retail spaces. Includes restroom sanitization and window cleaning.",
        "Provides sanitization and disinfection services. Uses electrostatic sprayers. Focus on high-touch areas.",
        "Specializes in rug cleaning. Pickup and delivery included. Uses gentle, fabric-specific detergents.",
        "Vendor offers ceiling and wall cleaning. Removes smoke stains, grease, and accumulated dust.",
        "Handles outdoor furniture cleaning. Includes mold removal, cushion washing, and fabric protection.",
        "Provides chimney and fireplace cleaning. Includes soot removal and inspection of flue.",
        "Offers event cleanup services. Includes pre-event setup cleaning and post-event waste removal.",
        "Specializes in green-certified office cleaning. Uses HEPA vacuums and chemical-free solutions.",
        "Handles air duct cleaning. Uses industrial vacuum system and sanitizing fogger."
    ]
    return random.choice(notes)


if __name__ == "__main__":
    print("🚀 Starting AI Receptionist Data Generation...")
    
    # Create database and collections
    print("\n📊 Setting up MongoDB database...")
    client = create_database_and_collections(MONGO_URI)
    
    validate_client(client)
    db = validate_database(client, DATABASE_NAME)
    validate_collections(db, COLLECTIONS, test_write=False)

    # NOTE: This exit stops execution before data generation; comment it out to proceed.
    # sys.exit(1)

    if client:
        # Generate data
        print("\n Generating fake data...")
        vendors = generate_vendors()
        clients, properties, jobs, visits, kb = generate_clients(vendors=vendors)

        print("\n Generated Data Summary:")
        print(f"   Clients: {len(clients)}")
        print(f"   Properties: {len(properties)}")
        print(f"   Jobs: {len(jobs)}")
        print(f"   Visits: {len(visits)}")
        print(f"   Vendors: {len(vendors)}")
        print(f"   Knowledge Base: {len(kb)}")
        
        # Add embeddings to all collections (vendors, clients, properties, jobs, visits)
        print("\n Generating embeddings...")
        vendors_with_embeddings = add_embeddings_to_collection(vendors)
        clients_with_embeddings = add_embeddings_to_collection(clients)
        properties_with_embeddings = add_embeddings_to_collection(properties)
        jobs_with_embeddings = add_embeddings_to_collection(jobs)
        visits_with_embeddings = add_embeddings_to_collection(visits)

        # Insert data into MongoDB — use the versions with embeddings
        print("\nInserting data into MongoDB...")
        insert_data_to_mongodb(client,
            vendors_with_embeddings,
            clients_with_embeddings,
            properties_with_embeddings,
            jobs_with_embeddings,
            visits_with_embeddings,
            kb)

        # Close connection
        client.close()
        print("\n🎉 Process completed successfully!")
    else:
        print("❌ Could not establish database connection. Exiting...")