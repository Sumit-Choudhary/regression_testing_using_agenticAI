🤖 Agentic-QA-Explorer: Autonomous UI Testing Framework
Project Overview: This is a next-generation automated testing framework that uses Agentic AI to navigate and test web applications autonomously. Unlike traditional static scripts, this agent "reasons" through UI changes using a Observe-Decide-Act loop.

🚀 Key Features
Agentic Orchestration: Built with LangGraph to manage complex, stateful testing loops.

Driver: Powered by Playwright for high-speed, reliable browser interaction.

Config-Driven: Decoupled navigation logic using nav_config.json, making it reusable for any web app.

Self-Healing: The agent uses LLM reasoning to "find a way" even if a UI element changes slightly.

AI Evaluation: Integrated with DeepEval (Confident AI) to measure "Task Completion" and "Action Efficiency."

📁 Project Structure
Plaintext
.
├── configs/            # JSON blueprints for different apps (SauceDemo, etc.)
├── core/               # The "Brain" (LangGraph, Browser Logic, Config Loader)
├── utils/              # DOM Parsing and Screenshot helpers
├── tests/              # DeepEval test suites and performance metrics
├── main.py             # Entry point to run the Autonomous Agent
└── requirements.txt    # Project dependencies
🛠️ Setup & Installation
Create Virtual Environment:

Bash
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
Install Dependencies:

Bash
pip install -r requirements.txt
playwright install chromium
Configure Environment:
Create a .env file and add your keys:

Plaintext
OPENAI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
📊 How it Works (The Loop)
The agent follows a circular logic path defined in core/agent_graph.py:

Vision: Captures the current page state and filters the DOM.

Reasoning: The LLM compares the Goal against the Config and picks the next move.

Execution: Playwright performs the physical action (Click/Type).

Validate: The loop repeats until the "Terminate" condition is met.

🧪 Evaluation Metrics
We use Confident AI (DeepEval) to ensure the agent is performing optimally:

Success Rate: Did the agent reach the checkout page?

Step Efficiency: Did it take the shortest path or wander around?

Tool Correctness: Did it use the correct selectors from our JSON config?