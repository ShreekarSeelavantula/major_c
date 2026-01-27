from pymongo import MongoClient

MONGO_URL = "mongodb+srv://dbUser:shreekar1572004@cluster0.4wsqsxc.mongodb.net/study_planner?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
db = client["ai_study_planner"]

users_collection = db["users"]
