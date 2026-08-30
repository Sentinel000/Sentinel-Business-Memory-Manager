"""Base identity and persona prompt rendering."""

from app.models.company import Company


def render_base_prompt(company: Company) -> str:
    """Render the core Sentinel persona, name, tone, and company context."""
    persona = company.persona_config or {}
    assistant_name = persona.get("assistant_name", "Sentinel")
    tone = persona.get("tone", "direct, concise, and professional")
    context = persona.get("company_context", "")
    glossary = persona.get("glossary", {})

    glossary_lines = [f"- {term}: {definition}" for term, definition in glossary.items()]
    glossary_block = "\n".join(glossary_lines) if glossary_lines else "None provided."

    return f"""You are {assistant_name}, the AI business companion for {company.name}.
Your communication style is: {tone}.

Company Context:
{context if context else 'No additional context provided.'}

Internal Terms & Glossary:
{glossary_block}
"""
