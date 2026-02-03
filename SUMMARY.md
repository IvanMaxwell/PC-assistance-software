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
