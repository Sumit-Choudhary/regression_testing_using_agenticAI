import asyncio
import os
from playwright.async_api import async_playwright
from core.agent_graph import create_agent_graph

# Configuration
# 1. Define a comprehensive end-to-end goal
TARGET_GOAL = (
    "1. Login to SauceDemo using 'standard_user' and 'secret_sauce'. "
    "2. Sort the items on the inventory page"
    #"2. Add the 'Sauce Labs Backpack' to the cart. "
    #"3. Go to the cart and complete the checkout process by entering valid firstname, lastname and zip code. "
    #"4. Terminate once you reach the checkout complete page."
)

async def run_automation():
    async with async_playwright() as p:
        # 1. Launch Browser
        print("🚀 [STARTING]: Launching Chromium...")
        browser = await p.chromium.launch(headless=False)  # Set to True for production
        context = await browser.new_context()
        page = await context.new_page()

        # 2. Define Initial State
        # Note: 'history' is initialized as an empty list
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

        # 3. Compile the Graph
        print("🕸️  [GRAPH]: Compiling Agent Graph...")
        app = create_agent_graph()

        # 4. Invoke the Graph
        # We pass the 'page' object via the 'configurable' dict so nodes can access it
        print(f"🎯 [MISSION]: {TARGET_GOAL}")
        
        try:
            # We use a recursion limit to prevent infinite loops during testing
            config = {"configurable": {"page": page,
                                       "thread_id": "test_session_2026"}, "recursion_limit": 50}
            
            final_state = await app.ainvoke(initial_state, config=config)
            
            # 5. Validation Logic
            print("\n--- 🏁 MISSION RESULTS ---")
            if final_state.get("history") and "Goal Achieved" in final_state["history"][-1]:
                print("✅ SUCCESS: The agent reached the goal and terminated correctly.")
            else:
                print("⚠️  PARTIAL: The graph ended, but 'Goal Achieved' was not found in history.")
            
            print(f"📝 Final Page: {final_state.get('current_page')}")
            print(f"🔗 Final URL: {final_state.get('url')}")
            
        except Exception as e:
            print(f"❌ [CRITICAL FAILURE]: {str(e)}")
        
        finally:
            print("\n🏁 [MISSION ENDED]: Closing browser in 5 seconds...")
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    # Ensure environment variables are loaded
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ ERROR: GOOGLE_API_KEY not found in environment.")
    else:
        asyncio.run(run_automation())