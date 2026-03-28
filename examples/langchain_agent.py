"""
Example: LangChain agent instrumented with the Retrace callback handler.

Setup (two terminals):

  Terminal 1 — Start the Retrace TUI:
    $ retrace ui

  Terminal 2 — Run this script:
    $ pip install langchain langchain-community duckduckgo-search
    $ python examples/langchain_agent.py

The agent's thoughts, actions, and observations will appear in the TUI
in real-time.
"""

from retrace.callbacks.langchain import RetraceLangChainHandler

# Create the retrace callback handler.
# It will automatically connect to the Retrace TUI server at 127.0.0.1:8765.
handler = RetraceLangChainHandler()


def main() -> None:
    """Run a LangChain ReAct agent with the Retrace callback."""
    try:
        from langchain.agents import AgentType, initialize_agent, load_tools
        from langchain_community.llms import OpenAI
    except ImportError:
        print(
            "This example requires langchain and langchain-community.\n"
            "Install them with: pip install langchain langchain-community openai"
        )
        return

    llm = OpenAI(temperature=0)
    tools = load_tools(["ddg-search"], llm=llm)
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    # Pass the retrace handler as a callback — that's all it takes!
    agent.run("What is the capital of France?", callbacks=[handler])


if __name__ == "__main__":
    main()
