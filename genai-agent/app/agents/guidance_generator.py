"""
genai-agent/app/agents/guidance_generator.py
Owner: Person 1 | Week: 3 (initial) -> Week 4 (proactive guidance)

Third agent in the LangGraph RCA pipeline.
- Takes the identified root cause and generates natural-language, step-by-step
  guidance for engineers (or automation) using Gemini
- Week 4: extend to generate *proactive* guidance — preventive steps before a
  predicted failure actually occurs
- Output matches the "guidance" block of shared/schemas/incident_record.schema.json
"""
