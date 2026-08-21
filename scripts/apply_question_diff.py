#!/usr/bin/env python3
"""Применяет diff (тесты + вопросы) из редактора к data/tests.jsonl и data/questions.jsonl."""
import json
import os

TESTS_PATH = "data/tests.jsonl"
QUESTIONS_PATH = "data/questions.jsonl"

QUESTION_REQUIRED = {"test_id", "type", "text"}
TEST_REQUIRED = {"position", "name"}
VALID_POSITIONS = {"mop", "tp", "service"}
VALID_CATEGORIES = {"Регламенты", "Оборудование", "ЦРМ/Битрикс", "1С", "Законодательство"}


def load_jsonl(path):
    items = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
    return items


def save_jsonl(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False))
            f.write("\n")


def validate_test(t):
    missing = TEST_REQUIRED - t.keys()
    if missing:
        raise ValueError(f"Тест {t.get('id')}: не хватает полей {sorted(missing)}")
    if t["position"] not in VALID_POSITIONS:
        raise ValueError(f"Тест {t.get('id')}: неизвестная должность '{t['position']}'")
    if not t["name"].strip():
        raise ValueError(f"Тест {t.get('id')}: пустое название")
    if "question_count" in t and t["question_count"] is not None:
        qc = t["question_count"]
        if not isinstance(qc, int) or isinstance(qc, bool) or qc <= 0:
            raise ValueError(f"Тест {t.get('id')}: question_count должен быть положительным целым числом")
    if "category_counts" in t and t["category_counts"] is not None:
        cc = t["category_counts"]
        if not isinstance(cc, dict) or not cc:
            raise ValueError(f"Тест {t.get('id')}: category_counts должен быть непустым объектом {{категория: количество}}")
        for cat, n in cc.items():
            if cat not in VALID_CATEGORIES:
                raise ValueError(f"Тест {t.get('id')}: неизвестная категория '{cat}' в category_counts")
            if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
                raise ValueError(f"Тест {t.get('id')}: category_counts['{cat}'] должен быть положительным целым числом")


def validate_question(q):
    missing = QUESTION_REQUIRED - q.keys()
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

    if "category" in q and q["category"] is not None:
        if q["category"] not in VALID_CATEGORIES:
            raise ValueError(f"Вопрос {q.get('id')}: неизвестная категория '{q['category']}'")


def apply_ops(items, ops, item_key, validate_fn, entity_name):
    by_id = {item["id"]: i for i, item in enumerate(items)}

    for op in ops:
        action = op.get("op")

        if action == "add":
            item = op[item_key]
            if not item.get("id"):
                raise ValueError(f"add {entity_name}: у объекта должен быть id (генерируется в редакторе)")
            if item["id"] in by_id:
                raise ValueError(f"add {entity_name}: id {item['id']} уже существует")
            validate_fn(item)
            items.append(item)
            by_id[item["id"]] = len(items) - 1

        elif action == "edit":
            oid = op["id"]
            if oid not in by_id:
                raise ValueError(f"edit {entity_name}: id {oid} не найден")
            item = dict(op[item_key])
            item["id"] = oid
            validate_fn(item)
            items[by_id[oid]] = item

        elif action == "delete":
            oid = op["id"]
            if oid not in by_id:
                raise ValueError(f"delete {entity_name}: id {oid} не найден")
            items[by_id[oid]] = None

        else:
            raise ValueError(f"Неизвестная операция для {entity_name}: {action!r}")

    return [item for item in items if item is not None]


def main():
    diff = json.loads(os.environ["DIFF_JSON"])
    if not isinstance(diff, dict):
        raise ValueError("diff должен быть JSON-объектом {tests: [...], questions: [...]}")

    tests = load_jsonl(TESTS_PATH)
    tests = apply_ops(tests, diff.get("tests", []), "test", validate_test, "test")
    save_jsonl(TESTS_PATH, tests)

    test_ids = {t["id"] for t in tests}

    questions = load_jsonl(QUESTIONS_PATH)

    def validate_question_with_test_ref(q):
        validate_question(q)
        if q["test_id"] not in test_ids:
            raise ValueError(f"Вопрос {q.get('id')}: test_id '{q['test_id']}' не существует")

    questions = apply_ops(questions, diff.get("questions", []), "question", validate_question_with_test_ref, "question")
    save_jsonl(QUESTIONS_PATH, questions)

    print(f"OK, тестов: {len(tests)}, вопросов: {len(questions)}")


if __name__ == "__main__":
    main()
