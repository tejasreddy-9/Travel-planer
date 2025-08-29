import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"C:\Users\Dell\OneDrive - ZENNIAL PRO PRIVATE LIMITED\Desktop\Travel-planer\.env")

print("Hugging Face Key:", os.getenv("HUGGINGFACEHUB_API_TOKEN"))
