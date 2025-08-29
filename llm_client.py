# llm_client.py
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# LangChain + HF imports
from langchain_community.llms import HuggingFaceHub
from langchain import LLMChain
from langchain.prompts import PromptTemplate

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
MODEL_ID = os.getenv("HUGGINGFACE_MODEL", "gpt2")  # change to a better model if available

if not HF_TOKEN:
    raise RuntimeError("Set HUGGINGFACEHUB_API_TOKEN in .env")

# create the LangChain LLM wrapper for a HuggingFace model
llm = HuggingFaceHub(
    repo_id=MODEL_ID,
    huggingfacehub_api_token=HF_TOKEN,
    model_kwargs={"temperature": 0.7, "max_new_tokens": 400},
)

prompt_template = """
You are a helpful AI travel planner. Create a clear day-by-day itinerary for a trip.

Destination: {destination}
Dates: {dates}
Travelers: {travelers}
Preferences: {preferences}

Output a human-friendly itinerary with:
- Day headings (Day 1, Day 2...)
- Activities with approximate times
- Short transport tips and estimated budget summary (low/medium/high; give approximate total cost in INR and USD)
Keep output concise and structured.
"""

prompt = PromptTemplate(
    input_variables=["destination", "dates", "travelers", "preferences"],
    template=prompt_template
)

chain = LLMChain(llm=llm, prompt=prompt)

async def generate_itinerary(destination: str, dates: str, travelers:int, preferences: str) -> str:
    """
    Run the chain in a thread to avoid blocking the async loop (the HF client may be blocking).
    Returns generated text.
    """
    params = {
        "destination": destination,
        "dates": dates or "flexible",
        "travelers": travelers or 1,
        "preferences": preferences or "general"
    }
    # run chain in a thread so FastAPI event loop isn't blocked
    return await asyncio.to_thread(chain.run, params)
