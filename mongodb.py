from pymongo import MongoClient

MONGODB_URI = ""

client = MongoClient(MONGODB_URI)

db = client["mydatabase"]
user_colloction = db["users"]

user_colloction.insert_one({"name" : "Tejas","age":"24"})

user = user_colloction.find_one({})