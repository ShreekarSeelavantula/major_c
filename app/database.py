import os
from pymongo import MongoClient
import gridfs
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise RuntimeError(
        "MONGO_URL is not set. "
        "Please add it to your .env file."
    )

client = MongoClient(MONGO_URL)
db = client["ai_study_planner"]

# Collections
users_collection     = db["users"]
syllabus_collection  = db["syllabus"]

# GridFS bucket
fs = gridfs.GridFS(db)