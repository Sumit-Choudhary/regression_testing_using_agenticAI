import os
import json
import base64
import operator
from typing import TypedDict, Annotated, List, Union
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from core.prompts import SYSTEM_PROMPT
from core.config_loader import ConfigLoader

load_dotenv()

# --- CONFIG & CONSTANTS ---
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")

# --- STATE DEFINITION ---
class AgentState(TypedDict):
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

# --- NODES ---

# ... (imports remain same)

# Node update only:
from core.config_healer import ConfigHealer

# Initialize healer along with loader
healer = ConfigHealer("nav_config.json")

import asyncio
from core.config_healer import ConfigHealer

# Re-initialize with updated logic
config_healer = ConfigHealer("nav_config.json")

async def vision_node(state: AgentState, config):
    page = config["configurable"]["page"]
    
    # 🚨 NAVIGATION FIX: 
    # Check if we are on a blank page OR if the URL is empty
    current_url = page.url
    if current_url == "about:blank" or not current_url or current_url == "":
        start_url = config_loader.get_base_url()
        print(f"🌐 [VISION]: Blank page detected. Navigating to: {start_url}")
        
        if start_url:
            await page.goto(start_url)
            # Wait for the network to be quiet so the page actually loads
            await page.wait_for_load_state("networkidle")
            current_url = page.url
        else:
            print("❌ [VISION ERROR]: No base_url found in nav_config.json!")

    # Capture the state after navigation
    screenshot = await page.screenshot(type="jpeg", quality=50)
    base64_img = base64.b64encode(screenshot).decode()
    
    # 1. Capture current state
    current_url = page.url
    screenshot = await page.screenshot(type="jpeg", quality=50)
    base64_img = base64.b64encode(screenshot).decode()

    # 2. LLM Inference for Page Identification
    known_pages = [p['page_name'] for p in config_loader.data.get("pages", [])]
    inference_prompt = f"URL: {current_url}. Which page is this from: {known_pages}? Return only the name or 'unknown'."
    
    response = await llm.ainvoke([
        HumanMessage(content=[
            {"type": "text", "text": inference_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ])
    ])
    inferred_name = response.content.strip().lower()

    # 3. 🚀 AUTO-HEAL: If unknown, scan the cart/checkout page
    if inferred_name == "unknown":
        new_page_key = current_url.split("/")[-1].split(".")[0].replace("-", "_") + "_page"
        print(f"🕵️‍♂️ [VISION]: Page unrecognized. Triggering Healer for '{new_page_key}'...")
        await healer.scan_and_update(page, new_page_key) #
        config_loader.load_config() #
        inferred_name = new_page_key

    # 4. Load Selectors
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

async def execution_node(state: AgentState, config):
    page = config["configurable"]["page"]
    action_data = state.get("next_action", {})
    action_type = action_data.get("action", "").lower()
    element_key = action_data.get("element_key")
    
    # Resolve selector from dictionary
    sel_data = state.get("raw_selectors", {}).get(element_key)
    selector = sel_data.get("locator") if isinstance(sel_data, dict) else sel_data

    if action_type == "terminate":
        return {"history": ["Goal Achieved"]}

    try:
        if action_type == "click":
            await page.click(selector, timeout=5000)
        elif action_type == "type":
            await page.fill(selector, str(action_data.get("value", "")))
        elif action_type == "select":
            # value will be something like "lohi" (Price low to high)
            selection_value = str(action_data.get("value", ""))
            await page.select_option(selector, value=selection_value)
            print(f"   ✅ Selected {selection_value} in {element_key}")
        
        return {"history": [f"Success: {action_type} on {element_key}"]}
    except Exception as e:
        # FEEDBACK: Tell the LLM exactly what went wrong so it doesn't repeat the loop
        return {"history": [f"Error: {action_type} failed on {element_key}. Reason: {str(e)[:50]}"]}

async def reasoning_node(state: AgentState):
    # Format the SYSTEM_PROMPT with current state
    prompt_content = SYSTEM_PROMPT.format(
        goal=state["goal"],
        page_name=state["current_page"],
        url=state["url"],
        history=", ".join(state["history"][-3:]) if state["history"] else "None",
        selectors=state["selectors_string"]
    )

    # Convert screenshot to Base64 for multimodal input
    base64_img = base64.b64encode(state['screenshot']).decode()

    messages = [
        HumanMessage(content=[
            {"type": "text", "text": prompt_content},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ])
    ]

    print(f"🧠 [STEP 2: REASONING]")

    print("Following instruction interpreted by llm")
    # Extract the text part and print
    for block in messages[0].content:
        if block["type"] == "text":
            print(block["text"])

    response = await llm.ainvoke(messages)
    
    try:
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        decision = json.loads(clean_json)
        print(f"   • Gemini Decision: {decision.get('action')} on {decision.get('element_key')}")
    except Exception:
        print(f"   ❌ JSON Parse Error. Model response was not valid JSON.")
        decision = {"action": "wait", "reasoning": "Failed to parse model output."}

    return {"next_action": decision}

async def execution_node(state: AgentState, config):
    page = config["configurable"]["page"]
    action_data = state.get("next_action", {})
    action_type = action_data.get("action", "").lower()
    element_key = action_data.get("element_key")
    
    # Resolve the selector
    sel_data = state.get("raw_selectors", {}).get(element_key)
    selector = sel_data.get("locator") if isinstance(sel_data, dict) else sel_data

    print(f"⚙️  [STEP 3: EXECUTION]")
    
    if action_type == "terminate":
        return {"history": ["Goal Achieved"]}

    # If the LLM picked an element that doesn't have a locator in our config
    if not selector and action_type in ["click", "type"]:
        error_msg = f"Missing selector for '{element_key}'. Please try another element or wait."
        print(f"   ❌ {error_msg}")
        return {"history": [f"Error: {error_msg}"]}

    try:
        if action_type == "click":
            await page.click(selector, timeout=5000)
            print(f"   ✅ Clicked {element_key}")
        elif action_type == "type":
            await page.fill(selector, "") 
            await page.type(selector, str(action_data.get("value", "")), delay=50)
            print(f"   ✅ Typed into {element_key}")
        
        await page.wait_for_timeout(1000) 
        return {"history": [f"Success: {action_type} {element_key}"]}
        
    except Exception as e:
        # 💡 CRITICAL: We pass the error back to the LLM's history
        # This prevents the LLM from clicking the same broken button again
        short_error = str(e)[:100]
        print(f"   ❌ Playwright Error: {short_error}")
        return {"history": [f"Failure: {action_type} on {element_key} failed. Reason: {short_error}"]}

# --- GRAPH LOGIC ---

def should_continue(state: AgentState):
    if state.get("history") and "Goal Achieved" in state["history"][-1]:
        print("--- ✅ EXITING GRAPH: Success ---")
        return END
    return "vision"

def create_agent_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("vision", vision_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("execution", execution_node)
    
    workflow.set_entry_point("vision")
    workflow.add_edge("vision", "reasoning")
    workflow.add_edge("reasoning", "execution")
    workflow.add_conditional_edges("execution", should_continue)
    
    return workflow.compile()