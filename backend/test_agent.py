import sys
import os
from dotenv import load_dotenv

# Load env before importing agent
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.chat_agent import agent

print("Testing agent...")
try:
    response = agent.chat("Are there any events in the database?")
    print("Response:", response)
except Exception as e:
    import traceback
    traceback.print_exc()
