import os
import sys
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from tools.agent_tools import (
    parse_sow_pdf, 
    synthesize_hld_architecture, 
    generate_implementation_guidance,
    render_requested_diagrams, 
    compile_hld_deliverables
)

load_dotenv()


def start_autonomous_agent():
    print("=" * 60)
    print("🤖 Autonomous SOW-HLD Agent Active")
    print("Ask anything (e.g., 'Make an ER diagram for C:\\Users\\Yash\\Downloads\\SOW.pdf', ")
    print("'Generate sequence diagram', or 'Compile PPTX deliverables')")
    print("=" * 60 + "\n")

    # Map tool names to tool functions for execution
    tools_map = {
        "parse_sow_pdf": parse_sow_pdf,
        "synthesize_hld_architecture": synthesize_hld_architecture,
        "generate_implementation_guidance": generate_implementation_guidance,
        "render_requested_diagrams": render_requested_diagrams,
        "compile_hld_deliverables": compile_hld_deliverables,
    }

    # Bind tools directly to ChatGroq model
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.0,
        api_key=os.getenv("GROQ_API_KEY")
    ).bind_tools(list(tools_map.values()))

    messages = [
        ("system", (
            "You are an expert AI Software Architecture Agent.\n"
            "You have access to tools to parse SOW PDFs, synthesize HLD specs,generate detailed tech-stack implementation guidance (with FOSS alternatives), render Mermaid diagrams, and compile PPTX/DOCX deliverables.\n\n"
            "AUTONOMOUS RULES:\n"
            "1. When the user asks for implementation details, technology choices, or open-source alternatives, execute `generate_implementation_guidance`.\n"
            "2. BE EFFICIENT WITH DIAGRAMS: When the user asks for the tech stack or implementation, ONLY call `render_requested_diagrams` with the argument `['deployment']`. Do not generate all diagrams unless the user explicitly asks for 'all diagrams'.\n"
            "3. If a user asks for a specific diagram (e.g. ER diagram, sequence diagram), parse the PDF and synthesize the HLD if needed, then execute `render_requested_diagrams` for that diagram type only. DO NOT run `generate_implementation_guidance` unless the user explicitly asks for tech stack or implementation guidance..\n"
            "4. If a prerequisite step is missing (e.g., no SOW parsed or HLD in memory), explain what is missing or politely ask for the required input (PDF path or system description)."
        ))
    ]

    while True:
        user_input = input("\n👤 You: ").strip()
        if not user_input or user_input.lower() in ["exit", "quit", "q"]:
            print("👋 Bye!")
            break

        messages.append(HumanMessage(content=user_input))

        # Autonomous Tool Calling Loop
        while True:
            response = llm.invoke(messages)
            messages.append(response)

            # If the LLM didn't request any tools, output its final message and wait for user input
            if not response.tool_calls:
                print(f"\n🤖 Assistant: {response.content}")
                break

            # Execute tool calls requested by the LLM
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                print(f"    [Agent Calling Tool: {tool_name}] -> Args: {tool_args}")
                
                selected_tool = tools_map.get(tool_name)
                if selected_tool:
                    tool_output = selected_tool.invoke(tool_args)
                    messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))
                    # Removed 12-second pause here for instant execution
                else:
                    messages.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_call["id"]))


if __name__ == "__main__":
    start_autonomous_agent()