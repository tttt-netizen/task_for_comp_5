# Lead Backend

Folders used by app code:
- `core`
- `landings`
- `shared`
- `alembic`

Stack used:
- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2 
- Alembic
- Redis 
- JWT (HS256)

## Start (Docker, main mode)
```bash
docker compose up --build -d  
```

## Start 2nd Variant (without Docker, alternative)
Requirements:
- Python 3.11+
- PostgreSQL running and reachable
- Redis running and reachable

Commands:
```bash
python -m pip install -e .
python main.py check
python main.py init
python main.py landings
python main.py core
python main.py worker
```
Run the last three commands in separate terminals coz this is different services

## Main commands
Run commands inside `core` container:

```bash
# create affiliate with id=300 (also prints token by default)
docker compose exec core python main.py add-affiliate --id 300 --name "Affiliate 300"

# show all affiliates from DB
docker compose exec core python main.py list-affiliates

# show all offers from DB
docker compose exec core python main.py list-offers

# check PostgreSQL + Redis connection status
docker compose exec core python main.py check

# generate JWT token for affiliate 300
docker compose exec core python main.py token --affiliate-id 300

# call GET /leads grouped by date (token is auto-generated from affiliate-id)
docker compose exec core python main.py leads --affiliate-id 300 --group date

# call GET /leads grouped by offer
docker compose exec core python main.py leads --affiliate-id 300 --group offer

# send 100000 random POST /lead requests
docker compose exec core python main.py loadtest --affiliate-id 300 --count 100 --concurrency 200 --progress-step 10

# send loadtest with ~20% intentional duplicates and progress each 1000 requests
docker compose exec core python main.py loadtest --affiliate-id 300 --count 100 --concurrency 200 --dup-percent 20 --progress-step 10
```

Manual token API:
```bash
curl -X POST "http://localhost:8001/auth/token" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: issue-token-secret" \
  -d '{"affiliate_id": 300}'
```

Manual POST /lead API:
```bash
curl -X POST "http://localhost:8000/lead" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "name": "Oleksii",
    "phone": "+380982342123",
    "country": "UA",
    "offer_id": 1,
    "affiliate_id": 300
  }'
```
## OTHER
- `init` service auto-runs migrations and seed.
- JWT payload is `{"id": affiliate_id}`.
- `POST /lead` requires body `affiliate_id` to match JWT `id`.
- Main business APIs:
  - `POST /lead` on `landings` (`http://localhost:8000/lead`)
  - `GET /leads` on `core` (`http://localhost:8001/leads`)
- `add-affiliate` prints token automatically (use `--no-token` to disable).
- Swagger:
  - `http://localhost:8000/docs`
  - `http://localhost:8001/docs`
