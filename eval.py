import json
import time
from pathlib import Path

from tutor import tutor_answer


if __name__ == "__main__":
    questions = json.loads(Path("eval_questions.json").read_text(encoding="utf-8"))
    correct = cited = 0
    times = []
    for item in questions:
        start = time.time()
        data = tutor_answer(item["q"])
        times.append(time.time() - start)
        text = " ".join([data.get("answer", ""), *data.get("worked_steps", [])]).lower()
        ok = all(word.lower() in text for word in item["expect"])
        cite = item["topic"].lower() in data.get("citation", "").lower()
        correct += ok
        cited += cite
        status = "PASS" if ok else "FAIL"
        citation_status = "CITED" if cite else "-----"
        print(f"{status}  {citation_status}  {times[-1]:5.1f}s  {item['q'][:60]}")

    count = len(questions)
    if not count:
        raise SystemExit("No evaluation questions found.")
    print(
        f"\nCorrect: {correct}/{count}   Cited: {cited}/{count}   "
        f"Average time: {sum(times) / count:.1f}s"
    )
