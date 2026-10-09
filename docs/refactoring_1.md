# Refactoring `ai-stack`

## Refactoring rubrics
1. System design & architecture: detecting system architecture flaws and poor choices.
2. Conventions & readability: ensuring consistent formatting, clear naming.
3. Modularity: providing loose coupling where reasonable, allowing flexibility for future architecture/framework/tool/provider swapping without disrupting core functionality.
4. Public source security: eliminating any sensitive, private or local information from leaking to the origin repo.
5. Basic mistakes in the current logic or code.
6. Clear documentation: meaningful `README.md`, dedicated section for documenting decisions, issues etc.

## Output
Save refactoring plan under `docs/refactoring_1_plan.md`

## About the app
`ai-stack` is a multi-container personal app providing full blown set of AI features for a single user. The app is meant to be used for various purposes including: personal assistant with wide range of features, coding partner, fictional character persona.The work is in progress. 

### Models
- `Fictional character persona - L3-8B-Stheno-v3.2-Q4_K_M.gguf`
- `Coding/assistant - Qwen3-8B Q4_K_M`

### Currently implemented
 - Local models module `llama-server`
 - Database module `db` serving shared application data storage
 - Python server `py-server` hosting the voice assistant pipeline
 - Voice assistant pipeline:
	- voice/text -> local network device -> server device -> `py-server` (STT+LLM+TTS) -> streaming voice chunks ->  local network device

### Next stage changes
- Wake word for voice assistant
- Persistent memory across single session & different sessions
- Initial setup for tool access + first simple tool
- Coding agent setup

### Future stages changes
- Multiple personas/prompts (changed using  wake-word/tool call)
- Smart routing based on the task (using tools such as 9router)
- Persistent context and knowledge data accumulation
- Telegram voice message/call communication
- Desktop & mobile apps, web app
- ...
