"""Process seed_tickets.json through the classifier and print results."""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from app.classifier import classify_ticket  # noqa: E402

tickets = json.loads(Path("seed_tickets.json").read_text(encoding="utf-8"))

COL = {"title": 45, "category": 16, "priority": 8, "status": 6, "tags": 40}
header = (
    f"{'Título':<{COL['title']}} "
    f"{'Categoría':<{COL['category']}} "
    f"{'Prioridad':<{COL['priority']}} "
    f"{'Estado':<{COL['status']}} "
    f"Tags"
)
sep = "-" * (sum(COL.values()) + len(COL))
print(header)
print(sep)

results = []

for i, t in enumerate(tickets, 1):
    title = t["title"]
    result = classify_ticket(title, t["description"])
    category = result["category"]
    priority = result["priority"]
    status = "open"

    results.append(
        {
            "title": title,
            "description": t["description"],
            "created_at": t["created_at"],
            "category": category,
            "priority": priority,
            "status": status,
            "tags": result["tags"],
        }
    )

    tags_str = ", ".join(result["tags"]) or "-"
    short_title = title if len(title) <= COL["title"] else title[: COL["title"] - 1] + "…"
    print(
        f"{short_title:<{COL['title']}} "
        f"{category:<{COL['category']}} "
        f"{priority:<{COL['priority']}} "
        f"{status:<{COL['status']}} "
        f"{tags_str}"
    )
    print(f"  [{i}/{len(tickets)}]", end="\r")

print()

out = Path("seed_results.json")
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Resultados guardados en {out} ({len(results)} tickets)")
