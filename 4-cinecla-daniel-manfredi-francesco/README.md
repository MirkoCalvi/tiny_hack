# tiny hack

## context

context.md

## install deps

```bash
# Install dependencies
uv sync

# Run server
cd backend && uv run python run.py
```

Backend runs on `http://0.0.0.0:3002`

### Frontend (React App)

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Run dev server
npm run dev
```

Frontend runs on `http://localhost:5173`
