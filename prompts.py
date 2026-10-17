import json
from pathlib import Path


SKILL_PATH = Path(__file__).parent / "skills" / "ncdc-physics-tutor" / "SKILL.md"


def load_skill_body(path: Path = SKILL_PATH) -> str:
    """Read the skill instructions without their YAML frontmatter."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError(f"Agent Skill frontmatter is missing from {path}")
    _, separator, body = content[4:].partition("\n---")
    if not separator:
        raise ValueError(f"Agent Skill frontmatter is not closed in {path}")
    return body.strip()


TUTOR_RULES = load_skill_body()

APP_FORMAT = """Reply with JSON that matches the schema:
- "in_syllabus": false only when the context does not cover the question.
- "hint": one guiding question or first step. Never give the final answer in the hint.
- "answer": the full explanation in 3 to 6 short sentences.
- "worked_steps": for calculations, each step with formula, substitution and result
  with units. An empty list otherwise.
- "citation": the topic and sub-topic you used, e.g.
  "Topic 5: Thermal Physics, Sub-topic 3: Transfer of Heat Energy".
- "check_question": one short question that tests understanding."""

SYSTEM_PROMPT = TUTOR_RULES + "\n\n" + APP_FORMAT

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "in_syllabus": {"type": "boolean"},
        "hint": {"type": "string"},
        "answer": {"type": "string"},
        "worked_steps": {"type": "array", "items": {"type": "string"}},
        "citation": {"type": "string"},
        "check_question": {"type": "string"},
    },
    "required": ["in_syllabus", "hint", "answer", "worked_steps", "citation", "check_question"],
}


def _shot(user, answer):
    return [{"role": "user", "content": user}, {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)}]


FEW_SHOT = _shot(
    "SYLLABUS CONTEXT:\n[Topic 5: Thermal Physics, Sub-topic 3: Transfer of Heat Energy]\n"
    "Learners explain conduction, convection and radiation with everyday examples.\n\n"
    "QUESTION: Why does the metal handle of a saucepan get hot on a charcoal stove?",
    {
        "in_syllabus": True,
        "hint": "Think about the tiny particles at the hot bottom of the pan. How could their energy travel up to the handle?",
        "answer": "Heat travels from the hot bottom of the pan to the handle by conduction. "
                  "Particles near the fire vibrate faster and pass energy to their neighbours. "
                  "Metals also have free electrons that carry energy quickly. "
                  "That is why many saucepans have wooden or plastic handles, which are poor conductors.",
        "worked_steps": [],
        "citation": "Topic 5: Thermal Physics, Sub-topic 3: Transfer of Heat Energy",
        "check_question": "Why is a wooden spoon better than a metal spoon for stirring hot porridge?",
    },
) + _shot(
    "SYLLABUS CONTEXT:\n[Topic 3: Forces and their Effects, Sub-topic 5: Pressure]\n"
    "Learners define pressure, use pressure = force / area, and apply it to daily life.\n\n"
    "QUESTION: A full jerrycan weighs 200 N. Its base area is 0.05 m². "
    "What pressure does it exert on the ground?\n\n"
    "CALCULATOR RESULTS (use exactly):\n200 / 0.05 = 4000",
    {
        "in_syllabus": True,
        "hint": "Pressure tells us how much force acts on each square metre. Which formula links force, area and pressure?",
        "answer": "Pressure is force divided by area. The jerrycan pushes down with 200 N on 0.05 m². "
                  "So the pressure is 4000 Pa. One pascal is one newton on each square metre.",
        "worked_steps": ["Formula: pressure = force ÷ area",
                         "Substitute: pressure = 200 N ÷ 0.05 m²",
                         "Result: pressure = 4000 Pa"],
        "citation": "Topic 3: Forces and their Effects, Sub-topic 5: Pressure",
        "check_question": "If the same jerrycan stood on a smaller base, would the pressure be bigger or smaller?",
    },
)

SOLVER_PROMPT = """You are a careful physics problem solver for Senior 1 and 2.
Plan the solution step by step using the SYLLABUS CONTEXT.
For EVERY arithmetic operation, call the calculate tool. Never do arithmetic in your head.
When finished, write the worked solution: formula, substitution, result with SI units."""

CHECK_PROMPT = """You are a strict physics marker. Check the worked steps for wrong formulas,
missing or wrong units, and numbers that do not match the calculator results.
Set "ok" to true only if everything is correct. Otherwise describe the problem in one
sentence and give the corrected final answer with units."""

CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "problem": {"type": "string"},
        "corrected_answer": {"type": "string"},
    },
    "required": ["ok", "problem", "corrected_answer"],
}

ACTIVITY_PROMPT = """You design activities of integration for Uganda's competence-based lower
secondary curriculum. An activity of integration gives learners a real-life scenario and asks
them to use what they learned to solve a problem or make something.
Rules:
- Base the physics on the SYLLABUS CONTEXT.
- Set the scenario in rural or small-town Uganda.
- Use only cheap, locally available materials.
- The learner must produce something: an explanation, a design, a simple device,
  a poster or a short report.
- Write for a learner aged 12 to 15. Short sentences."""

ACTIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenario": {"type": "string"},
        "task": {"type": "string"},
        "materials": {"type": "array", "items": {"type": "string"}},
        "guiding_steps": {"type": "array", "items": {"type": "string"}},
        "success_criteria": {"type": "array", "items": {"type": "string"}},
        "citation": {"type": "string"},
    },
    "required": ["title", "scenario", "task", "materials", "guiding_steps",
                 "success_criteria", "citation"],
}

IMAGE_PROMPT = """Read the physics question in this image. Write it out exactly as text.
If there is a diagram, add one sentence listing the values and labels it shows.
Reply with the question text only."""

AUDIO_PROMPT = """Transcribe this audio exactly. The speaker is a student asking a physics
question. Reply with the transcription only."""
