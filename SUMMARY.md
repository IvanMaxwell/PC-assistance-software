# PC Automation Framework - Handoff Summary

## Goal
Safe multi-LLM orchestration for PC troubleshooting. LLMs plan, code executes.

## Architecture
- **Orchestrator (FSM)**: IDLE→NEGOTIATE→DIAGNOSE→PLAN→SCORE→VALIDATE→EXECUTE→LEARN
- **Planner LLM**: Deepseek R1 (local 8B) - generates JSON plans
- **Validator LLM**: Reviews low-confidence plans
- **API LLMs**: Fast (analysis), Dev (code gen, mock for now)
- **Executor**: Deterministic dispatcher, no AI

## Key Safety
1. Tools are whitelisted in `SAFE_TOOLS` dict
2. LLM cannot run arbitrary code
3. Generated code runs in sandbox first
4. Halt on any step failure

## Project Structure
```
/pc_automation_framework
├── /core (orchestrator, memory, config, logger)
├── /llm (planner, validator, api_wrapper, prompts)
├── /tools (registry, diagnostics, actions, sandbox)
├── /data (memory_vector, logs)
└── main.py
```

flow:
User → CM Agent only (no direct access to anything else)
CM Agent → Orchestrator (submit intent, pause, resume, abort from user)
Orchestrator → Planner Client (request plan generation)
Orchestrator → CS Agent (request risk evaluation, only if triggered)
Orchestrator → Executor (send validated plan for execution)
Orchestrator → CM Agent (send execution events for monitoring)
Executor → Tools (invoke registered tools only)
CS Agent → Orchestrator (return risk assessment)
Planner → Orchestrator (return generated plan)
CM Agent → User (all responses, notifications, alerts)




---

## 📊 **Responsibilities Summary**

### **CM Agent (Communication & Monitoring)**

**BEFORE Execution:**
1. Receive user message
2. **NEW**: Summarize intent back to user for confirmation
3. Send to Orchestrator

**DURING Execution:**
4. Monitor each step in real-time
5. Detect drift (error, timeout, unexpected state)
6. **NEW**: If error, retry with prompt variations (max 3 attempts)
7. If drift persists, **pause** execution (not abort)
8. Alert user with options: Resume, Abort, Modify

**AFTER Execution:**
9. Summarize results to user in natural language
10. Record in memory

---

### **CS Agent (Safety & Risk Assessment)**

**BEFORE Execution:**
1. Triggered when: confidence < 0.8 OR risky keywords OR HIGH risk tools
2. Analyze plan for risks
3. Run counterfactual simulation ("what could go wrong?")
4. **NEW**: If risky, provide constraints for safer approach
5. Return recommendation:
   - APPROVE → Execute as-is
   - APPROVE_WITH_MODIFICATIONS → Send constraints to Planner for regeneration
   - REJECT → Send constraints to Planner, if still rejected after 3 attempts, abort

**Flow for APPROVE_WITH_MODIFICATIONS:**
```
CS Agent → provides constraints
→ Orchestrator → sends to Planner
→ Planner → generates new plan with constraints
→ CS Agent → reviews again (if still risky, reject)
```

**Max loop**: 3 Planner attempts before giving up

---

## ✅ **Corrected Interaction Example**
```
USER COMMAND: "Delete all files older than 1 year in Downloads"

STEP 1: CM Agent receives and confirms intent
CM → User: "I understand you want to delete files older than 1 year 
            from Downloads to free up space. Is this correct?"
User: "Yes"

STEP 2: Planner generates plan (Attempt 1)
Plan: [
  {"tool": "find_files", "params": {"dir": "Downloads", "age": ">365"}},
  {"tool": "delete_files", "params": {"files": "{{step1.result}}"}}
]
Confidence: 0.72 (low)

STEP 3: CS Agent reviews (triggered by low confidence + HIGH risk tool + "delete" keyword)
CS Agent Output: {
  "risk_level": "HIGH",
  "concerns": [
    "Permanent deletion without recovery",
    "No backup exists",
    "Could include important files"
  ],
  "constraints": [
    "Must check file importance before deletion",
    "Must create temporary backup",
    "Backup deleted after 30 days confirmation"
  ],
  "recommendation": "APPROVE_WITH_MODIFICATIONS"
}

STEP 4: Orchestrator sends constraints back to Planner
Planner generates plan (Attempt 2) with constraints:
Plan: [
  {"tool": "find_files", "params": {"dir": "Downloads", "age": ">365"}},
  {"tool": "analyze_file_importance", "params": {"files": "{{step1.result}}"}},
  {"tool": "create_backup", "params": {"files": "{{step2.important}}"}},
  {"tool": "delete_files", "params": {"files": "{{step2.unimportant}}"}},
  {"tool": "schedule_backup_deletion", "params": {"backup": "{{step3}}", "days": 30}}
]
Confidence: 0.88 (high)

STEP 5: CS Agent reviews again
CS Agent: {
  "risk_level": "MEDIUM",
  "concerns": [],
  "recommendation": "APPROVE"
}

STEP 6: Orchestrator asks user for confirmation (MEDIUM risk requires confirmation)
Orchestrator → User: "Plan approved. Requires confirmation for MEDIUM risk. 
                      Will backup important files before deletion. Proceed?"
User: "Yes"

STEP 7: Executor runs tools

STEP 8: CM Agent monitors execution
Step 1: ✅ Found 50 files
Step 2: ✅ 3 marked as important (recent downloads)
Step 3: ✅ Backup created
Step 4: ⚠️ 2 files in use, skipped (DRIFT DETECTED)
CM Agent → PAUSE execution
CM Agent → User: "2 files are currently in use and cannot be deleted. 
                  Options: (1) Skip and continue (2) Retry later (3) Abort"
User: "Skip and continue"
CM Agent → RESUME execution
Step 4: ✅ Deleted 45 files, skipped 2
Step 5: ✅ Backup scheduled for deletion in 30 days

STEP 9: CM Agent summarizes
CM Agent → User: "Completed! Deleted 45 old files (47 were safe to remove, 
                  2 were in use and skipped). Created backup of 3 important 
                  files which will be deleted in 30 days."