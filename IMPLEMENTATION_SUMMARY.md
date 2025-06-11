graph TD
    subgraph "AGENT INITIALIZATION"
        A["🚀 User starts agent"] --> B["Initialize AgentConfig<br/>• codebase_path<br/>• model_key<br/>• mission<br/>• verification_target"]
        
        B --> C["Setup ToolHandler<br/>• Path validation<br/>• Security constraints<br/>• Tool mapping"]
        
        C --> D["Initialize Google AI Client<br/>• API key validation<br/>• Model configuration<br/>• Thinking capabilities"]
        
        D --> E["Generate Directory Tree<br/>• Smart filtering (security files)<br/>• Exclude noise (node_modules)<br/>• Max depth: 4 levels"]
    end
    
    subgraph "PROMPT ARCHITECTURE"
        E --> F["Load System Instruction Template<br/>from system_prompt.md"]
        
        F --> G{"verification_target<br/>provided?"}
        
        G -->|No| H["STATIC WORKFLOW:<br/>• Analyze codebase<br/>• Generate PoC<br/>• NO building/deployment<br/>• Accept unverified results"]
        
        G -->|Yes| I["DYNAMIC WORKFLOW:<br/>• Analyze codebase<br/>• Generate PoC<br/>• Test against live target<br/>• Verify dynamically"]
        
        H --> J["Format System Instruction<br/>• Include workflow section<br/>• Include directory tree<br/>• Static context (sent once)"]
        I --> J
        
        J --> K["Create Initial User Message<br/>'My mission is: {mission}.<br/>Begin your analysis.'"]
    end
    
    subgraph "CONVERSATION LOOP"
        K --> L["🔄 TURN LOOP<br/>(max 50 turns)"]
        
        L --> M["Configure API Request<br/>• Tools: All tool definitions<br/>• Temperature: 0.1<br/>• Max tokens: 8192<br/>• System instruction in config<br/>• Thinking config (if supported)"]
        
        M --> N["⏳ Rate Limit Protection<br/>4 second delay"]
        
        N --> O["Send Request to Google AI<br/>with retry logic"]
        
        O --> P{"API Response<br/>successful?"}
        
        P -->|Rate Limited| Q["Wait & Retry<br/>(max 3 attempts)"]
        Q --> O
        
        P -->|Failed| R["❌ Return Error"]
        
        P -->|Success| S["📊 Display Token Usage<br/>• Prompt tokens<br/>• Output tokens<br/>• Thought tokens<br/>• Total tokens"]
    end
    
    subgraph "RESPONSE PROCESSING"
        S --> T["Parse Response<br/>• Extract text parts<br/>• Find tool calls<br/>• Separate reasoning"]
        
        T --> U{"Response contains<br/>tool call?"}
        
        U -->|No| V["🎯 CONCLUSION<br/>Agent provides final report"]
        
        U -->|Yes| W["Display Reasoning<br/>💭 Thought or 🧠 Reasoning"]
        
        W --> X["🛠️ Execute Tool Call<br/>via ToolHandler"]
        
        X --> Y["Tool Security Validation<br/>• Path traversal check<br/>• Workspace boundary<br/>• Malicious command filter"]
        
        Y --> Z["Execute Actual Tool<br/>• Shell commands<br/>• File operations<br/>• Static analysis<br/>• Code search"]
        
        Z --> AA["🔬 Display Observation<br/>Tool execution result"]
        
        AA --> BB["Add to Chat History<br/>• Tool call<br/>• Tool response<br/>• Continue conversation"]
        
        BB --> L
    end
    
    subgraph "TOOL ECOSYSTEM"
        CC["SHELL TOOLS<br/>• execute_shell_command<br/>• Working directory control<br/>• Output formatting"]
        
        DD["FILE SYSTEM TOOLS<br/>• write_to_file<br/>• read_file_content<br/>• Path validation"]
        
        EE["STATIC ANALYSIS TOOLS<br/>• search_codebase<br/>• search_pattern_in_file<br/>• list_functions_in_file<br/>• find_taints_in_file"]
        
        FF["UTILITY TOOLS<br/>• get_directory_tree<br/>• Smart filtering<br/>• Security-focused"]
        
        Z --> CC
        Z --> DD  
        Z --> EE
        Z --> FF
    end
    
    subgraph "SANDBOX AWARENESS"
        GG["Plan & Sandbox Check<br/>Every reasoning step includes:<br/>• Network limitations<br/>• Permission constraints<br/>• Available alternatives"]
        
        HH["Adaptive Execution<br/>• Network error → Expected<br/>• Permission denied → Use /tmp<br/>• Missing deps → Install --user<br/>• Build fails → Static analysis only"]
        
        W --> GG
        GG --> HH
        HH --> X
    end
    
    subgraph "CONFIDENCE EVALUATION"
        V --> II["CONFIDENCE CHECKLIST<br/>1. Trace analysis complete?<br/>2. Input sanitization bypassed?<br/>3. Exploit conditions met?<br/>4. PoC properly grounded?<br/>5. Verification status clear?"]
        
        II --> JJ{"All conditions<br/>satisfied?"}
        
        JJ -->|Yes| KK["✅ HIGH CONFIDENCE<br/>Report with verified findings"]
        JJ -->|No| LL["⚠️ MEDIUM/LOW CONFIDENCE<br/>Report with caveats"]
        
        KK --> MM["📋 FINAL REPORT<br/>• Vulnerability details<br/>• Proof of Concept<br/>• Verification status<br/>• Exploitation steps<br/>• Remediation advice"]
        LL --> MM
    end
    
    MM --> NN["💾 Save to Log File<br/>Complete transcript with<br/>timestamps and metadata"]
    
    style A fill:#e3f2fd
    style F fill:#f3e5f5  
    style L fill:#fff3e0
    style X fill:#e8f5e8
    style V fill:#ffebee
    style MM fill:#e0f2f1