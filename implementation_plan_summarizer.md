# Implementation Plan - Final Summary Generation

## Objective
Implement a final summarization step in the automation workflow. The system should provide a natural language summary of the actions taken or the answer to the user's question based on tool outputs.

## Proposed Changes

### 1. Configuration (`core/config.py`)
- Add `REPORTING` state to the `State` enum.

### 2. LLM Planner (`llm/planner/planner.py`)
- Add `generate_summary(goal, plan, results)` method.
- This method will:
    - Construct a prompt with the user's goal, the executed plan, and the results.
    - Ask the LLM to provide a concise summary or answer.
    - Return the generated string.

### 3. Orchestrator (`core/orchestrator.py`)
- Update `ExecutionContext` to include a `summary` field.
- Add `_handle_reporting` state handler.
    - Call `planner.generate_summary`.
    - Store summary in context.
    - Display summary.
- Update `_handle_executing` to transition to `REPORTING` instead of `LEARNING`.
- Update `_handle_reporting` to transition to `LEARNING`.
- Update `_register_default_handlers` to include `REPORTING`.

### 4. Display (`core/display.py`)
- Add `show_final_summary(summary)` method to display the summary in a distinct, user-friendly panel.

## Verification
- Run a simple command (e.g., "Check system status").
- Verify that after execution, a natural language summary is displayed (e.g., "I have checked your system status. Your IP is ... and you are online.").
