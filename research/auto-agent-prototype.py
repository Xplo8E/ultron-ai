

from google import genai
from google.genai import types

import json
import os
try:
    # Get the API key from environment variable
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    print("✅ Gemini API configured successfully!")
except Exception as e:
    print("❌ Please set your GEMINI_API_KEY environment variable.")
    raise

# -------------- configure client -----------

client = genai.Client(api_key=GEMINI_API_KEY)

# =======================================================================
#  STEP 2: THE SIMULATED WORLD - OUR VULNERABLE CODEBASE (Unchanged)
# =======================================================================
print("\n[+] Setting up the simulated codebase...")

VIRTUAL_FILESYSTEM = {
    "AndroidManifest.xml": """
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.ultronbank.auditlogger">
    <permission android:name="com.ultronbank.auditlogger.permission.VIEW_LOGS" android:protectionLevel="signature" />
    <application>
        <receiver
            android:name=".SupportActionReceiver"
            android:exported="true"
            android:permission="com.ultronbank.auditlogger.permission.VIEW_LOGS">
            <intent-filter>
                <action android:name="com.ultronbank.auditlogger.action.VIEW_AUDIT_LOG" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
""",
    "src/com/ultronbank/auditlogger/SupportActionReceiver.java": """
package com.ultronbank.auditlogger;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
public class SupportActionReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        Uri dataUri = intent.getData();
        Intent viewIntent = new Intent(Intent.ACTION_VIEW);
        viewIntent.setData(dataUri);
        viewIntent.setPackage(context.getPackageName());
        viewIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        context.startActivity(viewIntent);
    }
}
"""
}

DIRECTORY_TREE = """
/
├── AndroidManifest.xml
└── src
    └── com
        └── ultronbank
            └── auditlogger
                └── SupportActionReceiver.java
"""
print("✅ Virtual codebase created.")

# =======================================================================
#  STEP 3: DEFINE THE AGENT'S TOOLS (Modern SDK Compliant)
# =======================================================================
print("\n[+] Defining agent tools...")



# NEW: The modern SDK inspects the function's signature and docstring directly.
def read_file_content(file_path: str) -> str:
    """
    Reads the full text content of a single file from the provided codebase.
    The file path must be one of the files listed in the initial directory tree.
    """
    print(f"    - Tool `read_file_content` called with path: '{file_path}'")
    return VIRTUAL_FILESYSTEM.get(file_path, f"Error: File not found at path: {file_path}")



# We pass the function object itself to the model.
AVAILABLE_TOOLS = [read_file_content]


print("✅ Agent tools defined.")

# =======================================================================
#  STEP 4: THE AUTONOMOUS AGENT (Refactored for the new SDK)
# =======================================================================
print("\n[+] Initializing the Autonomous Agent...")


# --- Configuration ---
AGENT_MODEL = 'gemini-2.0-flash-001'
MAX_TURNS = 20
MISSION = "Find a vulnerability related to insecure inter-component communication or data handling that could lead to sensitive data access. Start by analyzing the manifest to understand the application's components and trust boundaries."

# --- The Initial Prompt ---
initial_prompt = f"""
You are Ultron 2.0, an autonomous security research agent. Your goal is to identify and create a PoC for a critical vulnerability based on your mission.
You have access to a set of tools to read and analyze files. You must work in a loop: think, choose a tool, execute, observe the result, and repeat until you have enough evidence. When you have confirmed a vulnerability, stop calling tools and provide your final analysis as a detailed report.

**Codebase Structure:**
{DIRECTORY_TREE}

**Your Mission:**
{MISSION}

Begin your investigation.
"""

# --- Main ReAct Loop (Simplified with ChatSession) ---
print(f"🚀 MISSION STARTING: {MISSION}")

# Create a ChatSession object with tools configured
chat = client.chats.create(model=AGENT_MODEL)
final_report = None

# First message to the chat is the initial prompt with tools configured
response = chat.send_message(
    initial_prompt,
    config=types.GenerateContentConfig(
        tools=[read_file_content]
    )
)

for i in range(MAX_TURNS):
    print("-" * 40)
    print(f"🧠 AGENT TURN {i+1} / {MAX_TURNS}")
    print("-" * 40)
    
    # Get the model's response part.
    part = response.candidates[0].content.parts[0]

    # Check if the model decided to call a tool
    if hasattr(part, 'function_call') and part.function_call:
        function_call = part.function_call
        tool_name = function_call.name
        tool_args = {key: value for key, value in function_call.args.items()}
        
        print(f"🤔 Agent's thought leading to action (inferred): The next logical step is to use the `{tool_name}` tool.")
        print(f"🛠️ Agent is executing tool: `{tool_name}` with arguments: `{tool_args}`")
        
        # Execute the tool
        tool_function = None
        for tool in AVAILABLE_TOOLS:
            if tool.__name__ == tool_name:
                tool_function = tool
                break
                
        if tool_function is None:
            tool_result = f"Error: Attempted to call unknown tool '{tool_name}'"
        else:
            try:
                tool_result = tool_function(**tool_args)
            except Exception as e:
                tool_result = f"Error executing tool: {str(e)}"
            
        print(f"🔬 Observation (Result of tool call):\n---\n{tool_result[:500]}{'...' if len(tool_result) > 500 else ''}\n---")
        
        # Send the tool's result back to the same chat session using FunctionResponse
        response = chat.send_message(
            types.FunctionResponse(
                name=tool_name,
                response={"result": tool_result}
            ),
            config=types.GenerateContentConfig(
                tools=[read_file_content]
            )
        )
        
    else:
        # The model is finished and has provided its final text response
        print("✅ Agent has concluded its investigation and is providing the final report.")
        final_report = part.text
        break

print("=" * 40)
print("🚀 MISSION COMPLETE")
print("=" * 40)
if final_report:
    print("\n\n--- FINAL REPORT ---")
    print(final_report)
else:
    print("Agent reached maximum turns without providing a final report.")