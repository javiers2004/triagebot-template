"""Insert seed_results.json into the SQLite database."""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from app import db

src = Path("seed_results.json")
if not src.exists():
    print("No se encuentra seed_results.json. Ejecuta primero: python seed.py")
    sys.exit(1)

tickets = json.loads(src.read_text(encoding="utf-8"))
db.init_db()

for i, t in enumerate(tickets, 1):
    db.create_ticket(
        title=t["title"],
        description=t["description"],
        category=t["category"],
        priority=t["priority"],
        tags=t["tags"],
    )
    print(f"[{i}/{len(tickets)}] {t['title'][:60]}")

print(f"\n{len(tickets)} tickets insertados en la base de datos.")
