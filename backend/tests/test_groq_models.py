import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Lấy danh sách các model từ API
models = client.models.list()

print("--- DANH SÁCH MODEL KHẢ DỤNG TRÊN GROQ CỦA BẠN ---")
for model in models.data:
    print(f"- {model.id}")