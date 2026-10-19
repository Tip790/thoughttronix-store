---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

Run the tdd skill in @.claude/skills/tdd/SKILL.md and follow it's process. Then implement the remaining phase requirements using the normal process of the project.

## 3. Run Feedback Loops

Follow existing conventions to run the test suite, linter, formatter, and any additional feedback loops in the project.

## 4. Manual Verification

Answer this question: "How do I verify this phase or feature manually in the browser?" then stop and wait for manual approval that the manual verification passed.

## 5. Finish the Phase

Append Prompts.md following the format listed in @PROMPTS.md, then commit the finished phase to Github.