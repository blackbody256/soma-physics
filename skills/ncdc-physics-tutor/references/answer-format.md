# Answer format

Return an object with these required fields:

- `in_syllabus`: boolean
- `hint`: one guiding question or first step; never reveal the final answer here
- `answer`: full explanation in 3 to 6 short sentences
- `worked_steps`: calculation steps with formula, substitution and units; empty for non-calculations
- `citation`: the syllabus topic and sub-topic
- `check_question`: one short question that tests understanding

```json
{
  "in_syllabus": true,
  "hint": "Think about how the energy moves from the hot part to the cooler part.",
  "answer": "Heat moves by conduction.",
  "worked_steps": [],
  "citation": "Topic 5: Thermal Physics, Sub-topic 3: Transfer of Heat Energy",
  "check_question": "Why is a wooden spoon safer than a metal spoon?"
}
```

Use SI units for all calculations. Base curriculum claims on the supplied syllabus context only.
