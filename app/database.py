from pymongo import MongoClient
import gridfs

MONGO_URL = "mongodb+srv://dbUser:shreekar1572004@cluster0.4wsqsxc.mongodb.net/study_planner?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
db = client["ai_study_planner"]

# Collections
users_collection = db["users"]
syllabus_collection = db["syllabus"]

# GridFS bucket
fs = gridfs.GridFS(db)


syllabus_collection = db["syllabus"]

