# Sentinel Agent Layer — Tasks

- [x] Integrate LangGraph / DeepAgents runtime and Qwen 3.7 LLM configuration
- [x] Create modular prompt rendering layer in pp/agentic_ai/prompts/
- [x] Implement thread-safe tool closures in pp/agentic_ai/tools/
- [x] Implement Sentinel factory and agent runners in pp/agentic_ai/
- [x] Implement conversation threads model and checkpointer integration
- [x] Implement Chat API router (POST /api/v1/chat, GET /api/v1/conversations/{id})
- [x] Implement Transcripts API router (POST /api/v1/knowledge/transcripts)
- [x] Implement Follow-up Cron runner & Admin endpoint (POST /api/v1/admin/run-followup)
- [x] Implement isolated Audit Logging layer
- [x] Add Alembic migration for uto_approve_threshold
- [x] Verify all 117 end-to-end assertions in scripts/verify.py
