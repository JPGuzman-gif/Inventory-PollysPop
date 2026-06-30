# Inventory-PollysPop

Inventory and production tracking for PollysPop soda — raw ingredients, recipes, batches, and stock movements.

## Backend

Postgres + SQLAlchemy models live in `backend/`. See `backend/db/SCHEMA.md` for the database design.

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m db.init_db
```
