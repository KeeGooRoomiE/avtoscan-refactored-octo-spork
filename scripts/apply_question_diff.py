#!/usr/bin/env python3
"""Применяет diff (add/edit/delete) из редактора вопросов к data/questions.jsonl."""
import json
import os

DATA_PATH = "data/questions.jsonl"
REQUIRED_COMMON = {"section", "position_tags", "type", "text", "points"}


def load_bank(path):
    questions = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    questions.append(json.loads(line))
    return questions


def save_bank(path, questions):
    with open(path, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False))
            f.write("\n")


def validate_question(q):
    missing = REQUIRED_COMMON - q.keys()
    if missing:
        raise ValueError(f"Вопрос {q.get('id')}: не хватает полей {sorted(missing)}")

    qtype = q["type"]
    if qtype in ("single", "multiple"):
        options = q.get("options") or []
        correct = q.get("correct") or []
        if len(options) < 2:
            raise ValueError(f"Вопрос {q.get('id')}: нужно минимум 2 варианта ответа")
        if not correct:
            raise ValueError(f"Вопрос {q.get('id')}: не указан правильный ответ")
        if qtype == "single" and len(correct) != 1:
            raise ValueError(f"Вопрос {q.get('id')}: у single-вопроса должен быть ровно 1 correct")
        for idx in correct:
            if not isinstance(idx, int) or not (0 <= idx < len(options)):
                raise ValueError(f"Вопрос {q.get('id')}: индекс correct={idx} вне диапазона options")
    elif qtype == "free":
        if q.get("options") or q.get("correct"):
            raise ValueError(f"Вопрос {q.get('id')}: free-вопрос не должен иметь options/correct")
    else:
        raise ValueError(f"Вопрос {q.get('id')}: неизвестный type '{qtype}'")


def main():
    ops = json.loads(os.environ["DIFF_JSON"])
    if not isinstance(ops, list):
        raise ValueError("diff должен быть JSON-массивом операций")

    questions = load_bank(DATA_PATH)
    by_id = {q["id"]: i for i, q in enumerate(questions)}

    for op in ops:
        action = op.get("op")

        if action == "add":
            q = op["question"]
            if not q.get("id"):
                raise ValueError("add: у вопроса должен быть id (генерируется в редакторе)")
            if q["id"] in by_id:
                raise ValueError(f"add: id {q['id']} уже существует в банке")
            validate_question(q)
            questions.append(q)
            by_id[q["id"]] = len(questions) - 1

        elif action == "edit":
            qid = op["id"]
            if qid not in by_id:
                raise ValueError(f"edit: id {qid} не найден в банке")
            q = dict(op["question"])
            q["id"] = qid
            validate_question(q)
            questions[by_id[qid]] = q

        elif action == "delete":
            qid = op["id"]
            if qid not in by_id:
                raise ValueError(f"delete: id {qid} не найден в банке")
            questions[by_id[qid]] = None

        else:
            raise ValueError(f"Неизвестная операция: {action!r}")

    questions = [q for q in questions if q is not None]
    save_bank(DATA_PATH, questions)
    print(f"OK, вопросов в банке: {len(questions)}")


if __name__ == "__main__":
    main()
