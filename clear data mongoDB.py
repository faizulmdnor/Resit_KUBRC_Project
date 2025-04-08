from pymongo import MongoClient

MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "KUBRC_DB"
COLLECTION_NAME = "payments"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Drop the collection
db.drop_collection(COLLECTION_NAME)
print(f"Collection '{COLLECTION_NAME}' has been cleared.")
