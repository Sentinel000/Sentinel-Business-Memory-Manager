# Sentinel Agent Layer — Implementation Plan

## Goals
- Integrate DeepAgents / LangGraph ReAct runtime targeting Qwen 3.7 (qwen3.7-max).
- Build modular dynamic prompts with on-demand persona injection.
- Implement thread-safe and tenant-isolated tool closures for founder, employee, cron, and extractor.
- Integrate APScheduler for daily wake-ups and admin trigger endpoint.
- Connect meeting transcript extraction pipeline with automated confidence gating.
- Implement PostgreSQL thread checkpointing with user and company isolation.
