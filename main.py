"""
Agentic QA Explorer - Entry Point
---------------------------------
This is the primary execution script for the Autonomous Web Agent. 
It initializes the browser environment, defines the mission objectives, 
and invokes the compiled LangGraph to begin the observation-reasoning-action loop.
"""

import asyncio
import os
from playwright.async_api import async_playwright
from core.agent_graph import create_agent_graph

# --- MISSION CONFIGURATION ---
# Define a multi-step objective for the Agent to verify end-to-end functionality.

TARGET_GOAL = (
    "1. Login to SauceDemo using valid user name and valid password credentials. "
    "2. Sort the items on the page."
    "2. Add a product from the page to the cart."
    "3. Complete the checkout page"
    "4. Fill user info page with Mexican names"
    "3. Terminate once the final success message is seen"
)

async def run_automation():
    """
    Orchestrates the lifecycle of an automation mission:
    1. Resource Setup (Browser & Context)
    2. State Initialization
    3. Graph Compilation & Execution
    4. Post-Mission Validation & Cleanup
    """
    async with async_playwright() as p:
        
        # 1. BROWSER INITIALIZATION
        # 'headless=False' allows real-time monitoring of the Agent's navigation.
        print("🚀 [STARTING]: Launching Chromium instance...")
        browser = await p.chromium.launch(headless=False) 
        context = await browser.new_context()
        page = await context.new_page()

        # 2. STATE INITIALIZATION
        # Configures the initial 'AgentState' schema required by LangGraph.
        initial_state = {
            "goal": TARGET_GOAL,
            "current_page": "initialization",
            "history": [],
            "selectors_string": "",
            "raw_selectors": {},
            "screenshot": b"",
            "url": "about:blank",
            "next_action": {}
        }

        # 3. GRAPH ORCHESTRATION
        # Compiles the Vision-Reasoning-Execution nodes into an executable app.
        print("🕸️  [GRAPH]: Compiling state machine nodes...")
        app = create_agent_graph()

        print(f"🎯 [MISSION]: {TARGET_GOAL}")
        
        try:
            # 4. GRAPH INVOCATION
            # config: contains 'configurable' parameters (like the page object) 
            # and safety constraints (recursion_limit).
            config = {
                "configurable": {
                    "page": page,
                    "thread_id": "test_session_2026"
                }, 
                "recursion_limit": 50  # Prevents infinite loops if the LLM gets stuck
            }
            
            # Start the asynchronous loop
            final_state = await app.ainvoke(initial_state, config=config)
            
            # 5. MISSION DEBRIEF
            print("\n" + "="*30)
            print("🏁 MISSION RESULTS")
            print("="*30)
            
            # Check for the logical termination signal in the accumulated history
            if final_state.get("history") and "Goal Achieved" in final_state["history"][-1]:
                print("✅ SUCCESS: The agent achieved the objective and exited gracefully.")
            else:
                print("⚠️  PARTIAL: Workflow concluded, but mission completion signal was missing.")
            
            print(f"📝 Final Context: {final_state.get('current_page')}")
            print(f"🔗 Final URL: {final_state.get('url')}")
            
        except Exception as e:
            print(f"❌ [CRITICAL FAILURE]: An unhandled exception occurred: {str(e)}")
        
        finally:
            # 6. GRACEFUL TEARDOWN
            # Allows time for final visual inspection before closing the browser.
            print("\n🏁 [MISSION ENDED]: Closing session in 5 seconds...")
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    """
    Bootstrap the execution environment.
    Verifies authentication requirements before launching the async event loop.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ [CONFIG ERROR]: GOOGLE_API_KEY missing. Please check your .env file.")
    else:
        # Launch the high-level automation routine
        asyncio.run(run_automation())