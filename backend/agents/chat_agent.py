import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List, Dict, Any, Union
from sqlalchemy import text
from loguru import logger
import json
import datetime
import traceback
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from database.session import SessionLocal
from config.config import AppConfig
from langchain_core.tools import tool

settings = AppConfig()

# 2. Define Tools
@tool
def query_database(query: str) -> str:
    """
    Executes a SQL query against the SQLite/PostgreSQL database to retrieve CCTV events.
    Use this to answer user questions about what happened.
    Table: camera_events
    Columns: id (Int), camera_id (String), timestamp (DateTime), events (JSONB).
    The 'events' column contains dynamic JSON depending on the plugin.
    Example query: SELECT events FROM camera_events ORDER BY timestamp DESC LIMIT 10
    """
    # SECURITY: Only allow SELECT queries to prevent destructive operations
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return "Error: For security reasons, only SELECT queries are permitted."
        
    try:
        with SessionLocal() as db:
            result = db.execute(text(query))
            # Fetch up to 10 rows to avoid blowing up Groq's strict 8000 TPM limit on free tiers
            rows = result.fetchmany(10)
            
            # Format nicely for the LLM
            output = []
            for row in rows:
                if len(row) > 0:
                    row_str = str(row)
                    # Truncate extremely long JSON arrays (like embeddings) to save tokens
                    if len(row_str) > 500:
                        row_str = row_str[:497] + "..."
                    output.append(row_str)
            return "\n".join(output) if output else "No results found for that query."
    except SQLAlchemyError as e:
        logger.error(f"SQL Query Failed: {e}")
        return f"Database error executing query: {str(e)}"
    except Exception as e:
        logger.error(f"Execution Failed: {e}")
        return f"Error executing query: {str(e)}"

@tool
def check_live_camera_status(camera_id: str = "all") -> str:
    """
    Checks the real-time live telemetry of the cameras, including person count.
    Use this to answer questions about 'how many people are present in live webcam' or 'what is happening now'.
    If camera_id is 'all', it checks all active cameras.
    """
    camera_id = str(camera_id)
    import requests
    try:
        if camera_id == "all" or camera_id == "":
            res = requests.get("http://localhost:8000/")
            if res.ok:
                cameras = res.json().get("active_cameras", [])
                output = []
                for cam in cameras:
                    stats_res = requests.get(f"http://localhost:8000/stats/{cam}")
                    if stats_res.ok:
                        count = stats_res.json().get("person_count", 0)
                        output.append(f"Camera '{cam}' has {count} people present.")
                return "\n".join(output) if output else "No live cameras currently active."
            return "Failed to fetch camera status."
        else:
            stats_res = requests.get(f"http://localhost:8000/stats/{camera_id}")
            if stats_res.ok:
                count = stats_res.json().get("person_count", 0)
                return f"Camera '{camera_id}' has {count} people present."
            return f"Failed to fetch status for camera '{camera_id}'."
    except Exception as e:
        return f"Error connecting to live server: {str(e)}"

@tool
def track_visitor_path(name: str) -> str:
    """
    Tracks a specific person/visitor's path throughout the day across all cameras.
    Use this when the user asks where a person has been or which cameras they appeared on.
    """
    from app.plugins.visitor.models import Visitor, Visit
    try:
        with SessionLocal() as db:
            visitors = db.query(Visitor).filter(Visitor.name.ilike(f"%{name}%")).all()
            if not visitors:
                return f"No visitor or employee found matching the name '{name}'."
            
            output = []
            for visitor in visitors:
                output.append(f"Tracking history for {visitor.role} '{visitor.name}' (ID: {visitor.visitor_id}):")
                visits = db.query(Visit).filter(Visit.visitor_id == visitor.visitor_id).order_by(Visit.entry_time.asc()).all()
                if not visits:
                    output.append("  - No camera appearances recorded yet.")
                else:
                    for v in visits:
                        time_str = v.entry_time.strftime("%I:%M %p")
                        output.append(f"  - Present in camera '{v.camera_id}' at {time_str}")
            return "\n".join(output)
    except Exception as e:
        logger.error(f"Error tracking visitor: {e}")
        return f"Database error while tracking visitor: {str(e)}"

# 3. Setup LangGraph Workflow
class LogicEyeAgent:
    def __init__(self):
        from langchain_groq import ChatGroq
        from langgraph.graph.message import add_messages
        from typing import TypedDict, Annotated
        
        class AgentState(TypedDict):
            messages: Annotated[list, add_messages]
            camera_id: str
        self.AgentState = AgentState
        
        # We use the user's provided model and API key from configuration
        groq_api_key = settings.GROQ_API_KEY
        groq_model = settings.GROQ_MODEL
        
        # Initialize Groq LLM
        if groq_api_key:
            self.llm = ChatGroq(temperature=0.2, groq_api_key=groq_api_key, model_name=groq_model)
        else:
            self.llm = None
            logger.error("GROQ_API_KEY is not set. Chat Agent will not work.")
            
        self.tools = [query_database, check_live_camera_status, track_visitor_path]
        
        if self.llm:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        self.graph = self._build_graph()

    def _build_graph(self):
        from langgraph.graph import StateGraph, END
        workflow = StateGraph(self.AgentState)
        
        # Define nodes
        workflow.add_node("agent", self.call_agent)
        workflow.add_node("tools", self.execute_tools)
        
        # Define edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
        
    def should_continue(self, state: dict) -> str:
        messages = state["messages"]
        last_message = messages[-1]
        if getattr(last_message, "tool_calls", None):
            return "continue"
        return "end"

    def call_agent(self, state: dict):
        from langchain_core.messages import SystemMessage
        if not self.llm:
            return {"messages": [SystemMessage(content="AI Agent is disabled. Please configure GROQ_API_KEY.")]}
            
        messages = state["messages"]
        # Inject system prompt dynamically
        if len(messages) > 0 and not isinstance(messages[0], SystemMessage):
            system_prompt = f"""
            You are Logic Clutch CCTV AI, an intelligent assistant for a CCTV surveillance system. 
            When a user greets you (e.g., "hello", "hi", "hlo"), always reply with a warm greeting on behalf of Logic Clutch CCTV, and DO NOT invoke any tools.
            You can query the PostgreSQL (TimescaleDB) database for historical camera events, intrusions, fires, and attendance.
            Current time is {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
            Always be concise and helpful. When querying JSONB columns, use standard PostgreSQL JSONB extraction.
            If asked about the current or live status (like how many people are present right now), ALWAYS use the check_live_camera_status tool.
            If asked about a specific person or visitor's whereabouts, trajectory, or which cameras they appeared on, ALWAYS use the track_visitor_path tool.
            
            CRITICAL INSTRUCTIONS FOR TOOL CALLING:
            1. ONLY use the tools explicitly provided to you (query_database, check_live_camera_status, track_visitor_path).
            2. NEVER hallucinate tools (e.g., do not invent tools like brave_search).
            3. NEVER use XML-style function calls like <function=name>. Use the native JSON tool calling format exclusively.
            """
            messages = [SystemMessage(content=system_prompt)] + messages
            
        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def execute_tools(self, state: dict):
        from langchain_core.messages import ToolMessage
        messages = state["messages"]
        last_message = messages[-1]
        
        tool_responses = []
        for tool_call in getattr(last_message, "tool_calls", []):
            if tool_call["name"] == "query_database":
                # Execute the tool
                query = tool_call["args"].get("query", "")
                result = query_database.invoke({"query": query})
                tool_responses.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
            elif tool_call["name"] == "check_live_camera_status":
                cam_id = tool_call["args"].get("camera_id", "all")
                result = check_live_camera_status.invoke({"camera_id": cam_id})
                tool_responses.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
            elif tool_call["name"] == "track_visitor_path":
                name = tool_call["args"].get("name", "")
                result = track_visitor_path.invoke({"name": name})
                tool_responses.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                
        return {"messages": tool_responses}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _execute_graph_with_retry(self, inputs):
        for output in self.graph.stream(inputs):
            pass
        return output

    def chat(self, user_input: str, camera_id: str = "") -> str:
        from langchain_core.messages import HumanMessage
        """Entry point for the FastAPI endpoint"""
        if not self.llm:
            return "I am currently offline. Please ask the administrator to configure the Groq API key."
            
        inputs = {
            "messages": [HumanMessage(content=user_input)],
            "camera_id": camera_id
        }
        
        try:
            output = self._execute_graph_with_retry(inputs)
                
            # The final state is stored in the last node's output
            final_messages = output.get("agent", {}).get("messages", [])
            if final_messages:
                return final_messages[-1].content
            return "I couldn't process that request."
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Agent error traceback:\n{tb}")
            
            # Phase 5: Structured mapping, NEVER leak provider errors
            error_msg = str(e).lower()
            if "413" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                return "I'm receiving too much data or am temporarily rate-limited. Please try again in a moment."
            elif "401" in error_msg or "authentication" in error_msg:
                return "There is an issue with the AI authentication key. Please check the system configuration."
            elif "timeout" in error_msg or "deadline" in error_msg:
                return "The AI service timed out while processing your request. Please try again."
                
            return "The AI service is temporarily unavailable. Please try again later."

class LogicEyeAgentProxy:
    def __init__(self):
        self._agent = None
        
    @property
    def agent(self):
        if self._agent is None:
            self._agent = LogicEyeAgent()
        return self._agent
        
    def chat(self, user_input: str, camera_id: str = "") -> str:
        return self.agent.chat(user_input, camera_id)

# Singleton instance proxy
agent = LogicEyeAgentProxy()
