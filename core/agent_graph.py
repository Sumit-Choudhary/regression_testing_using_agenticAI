"""
Agentic Workflow Orchestrator (LangGraph)
-----------------------------------------
This module defines the State Machine and node logic for the Autonomous Agent.
It manages the transition between visual observation, LLM reasoning, 
and Playwright-based action execution.
"""

import os
import json
import base64
import operator
from typing import TypedDict, Annotated, List, Union, Dict, Any
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from core.prompts import SYSTEM_PROMPT
from core.config_loader import ConfigLoader
from core.config_healer import ConfigHealer
from langchain_core.runnables import RunnableConfig

# Load environment variables
load_dotenv()

# --- CONFIG & CONSTANTS ---
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

if not API_KEY:
    raise ValueError("[AUTH ERROR]: GOOGLE_API_KEY not found in .env")

# --- STATE DEFINITION ---
class AgentState(TypedDict):
    """Represents the unified state of the agent across all nodes."""
    goal: str
    current_page: str
    history: Annotated[List[str], operator.add]
    selectors_string: str  
    raw_selectors: dict    
    next_action: dict
    screenshot: bytes 
    url: str

# --- INITIALIZATION ---
llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=API_KEY,
    temperature=0,
    convert_system_message_to_human=True 
)

config_loader = ConfigLoader("nav_config.json") 
healer = ConfigHealer("nav_config.json")

# --- NODES ---

async def vision_node(state: AgentState, config: RunnableConfig):
    """STEP 1: OBSERVATION - Identifies page state and resolves selectors."""
    page = config["configurable"]["page"]
    
    # 1. Navigation Synchronization
    current_url = page.url
    if current_url == "about:blank" or not current_url:
        start_url = config_loader.get_base_url()
        print(f"🌐 [VISION]: Blank page detected. Navigating to: {start_url}")
        if start_url:
            await page.goto(start_url)
            await page.wait_for_load_state("networkidle")
            current_url = page.url
        else:
            print("❌ [VISION ERROR]: No base_url found in nav_config.json!")

    # 2. State Capture
    screenshot = await page.screenshot(type="jpeg", quality=50)
    base64_img = base64.b64encode(screenshot).decode()

    # 3. LLM Inference for Page Identification
    known_pages = [p['page_name'] for p in config_loader.data.get("pages", [])]
    inference_prompt = f"URL: {current_url}. Which page is this from: {known_pages}? Return only the name or 'unknown'."
    
    response = await llm.ainvoke([
        HumanMessage(content=[
            {"type": "text", "text": inference_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ])
    ])
    inferred_name = response.content.strip().lower()

    # 4. Auto-Heal Trigger
    if inferred_name == "unknown":
        new_page_key = current_url.split("/")[-1].split(".")[0].replace("-", "_") + "_page"
        print(f"🕵️‍♂️ [VISION]: Page unrecognized. Triggering Healer for '{new_page_key}'...")
        await healer.scan_and_update(page, new_page_key)
        config_loader.load_config() 
        inferred_name = new_page_key

    # 5. Selector Resolution
    page_details = next((p for p in config_loader.data.get("pages", []) if p['page_name'] == inferred_name), None)
    if page_details:
        raw_selectors = page_details["selectors"]
        formatted_selectors = f"CONTEXT: {page_details['page_name']}\nTOOLS:\n"
        for key in raw_selectors:
            formatted_selectors += f"- {key}: Interact with this element\n"
    else:
        raw_selectors = {}
        formatted_selectors = "Unknown page. Identify elements from the screenshot."

    return {
        "current_page": inferred_name,
        "selectors_string": formatted_selectors, 
        "raw_selectors": raw_selectors,           
        "url": current_url,
        "screenshot": screenshot
    }

async def reasoning_node(state: AgentState):
    """STEP 2: REASONING - Determines the next action based on goal and visual state."""
    prompt_content = SYSTEM_PROMPT.format(
        goal=state["goal"],
        page_name=state["current_page"],
        url=state["url"],
        history=", ".join(state["history"][-3:]) if state["history"] else "None",
        selectors=state["selectors_string"]
    )

    base64_img = base64.b64encode(state['screenshot']).decode()
    messages = [
        HumanMessage(content=[
            {"type": "text", "text": prompt_content},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ])
    ]

    print(f"🧠 [REASONING]: Calculating next move...")
    response = await llm.ainvoke(messages)
    
    try:
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        decision = json.loads(clean_json)
        print(f"   • Gemini Decision: {decision.get('action')} on {decision.get('element_key')}")
    except Exception:
        print(f"   ❌ JSON Parse Error. Model response was not valid JSON.")
        decision = {"action": "wait", "reasoning": "Failed to parse model output."}

    return {"next_action": decision}

async def execution_node(state: AgentState, config: RunnableConfig):
    """STEP 3: EXECUTION - Performs the resolved action in the browser."""
    page = config["configurable"]["page"]
    action_data = state.get("next_action", {})
    action_type = action_data.get("action", "").lower()
    element_key = action_data.get("element_key")
    
    # Resolve the CSS selector
    sel_data = state.get("raw_selectors", {}).get(element_key)
    selector = sel_data.get("locator") if isinstance(sel_data, dict) else sel_data

    print(f"⚙️  [EXECUTION]: {action_type.upper()} on '{element_key}'")
    
    if action_type == "terminate":
        return {"history": ["Goal Achieved"]}

    # Validation: Ensure selector exists before attempting interaction
    if not selector and action_type in ["click", "type", "select"]:
        error_msg = f"Missing selector for '{element_key}'."
        print(f"   ❌ {error_msg}")
        return {"history": [f"Error: {error_msg}"]}

    try:
        if action_type == "click":
            await page.click(selector, timeout=5000)
            print(f"   ✅ Clicked {element_key}")
            
        elif action_type == "type":
            # Clear field for deterministic input
            await page.fill(selector, "") 
            await page.type(selector, str(action_data.get("value", "")), delay=50)
            
            expected_value = str(action_data.get("value", ""))
            await page.wait_for_function(
                f"selector => document.querySelector(selector).value === '{expected_value}'",
                arg=selector,
                timeout=3000
            )
            print(f"   ✅ Verified input in {element_key}")
            print(f"   ✅ Typed into {element_key}")
            
        elif action_type == "select":
            selection_value = str(action_data.get("value", ""))
            await page.select_option(selector, value=selection_value)
            print(f"   ✅ Selected {selection_value} in {element_key}")
        
        # Stability delay
        await page.wait_for_timeout(1000) 
        return {"history": [f"Success: {action_type} {element_key}"]}
        
    except Exception as e:
        short_error = str(e)[:100]
        print(f"   ❌ Playwright Error: {short_error}")
        return {"history": [f"Failure: {action_type} on {element_key}. Reason: {short_error}"]}

# --- GRAPH LOGIC ---

def should_continue(state: AgentState):
    """Determines if the graph should cycle back to vision or terminate."""
    if state.get("history") and "Goal Achieved" in state["history"][-1]:
        print("--- ✅ EXITING GRAPH: Success ---")
        return END
    return "vision"

def create_agent_graph():
    """Compiles the StateGraph workflow."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("vision", vision_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("execution", execution_node)
    
    workflow.set_entry_point("vision")
    workflow.add_edge("vision", "reasoning")
    workflow.add_edge("reasoning", "execution")
    workflow.add_conditional_edges("execution", should_continue)
    
    return workflow.compile()