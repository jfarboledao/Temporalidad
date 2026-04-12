# Temporalidad

Proyecto dividido en dos partes:

- `backend`: API en FastAPI
- `frontend`: interfaz en React con Vite

## Requisitos

- Python 3.11 o superior
- Node.js 18 o superior
- `pip` y `npm`

## Estructura

```text
backend/
  app/
    main.py
  requirements.txt
frontend/
  src/
  package.json
```

## Iniciar el backend

Desde la raíz del proyecto:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

El backend queda disponible en:

- `http://127.0.0.1:8000`
- Documentación interactiva: `http://127.0.0.1:8000/docs`

Endpoints disponibles:

- `GET /`
- `GET /items/{item_id}`

## Iniciar el frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

El frontend normalmente queda disponible en:

- `http://localhost:5173`

## Notas

- Si cambias el backend, revisa si el frontend necesita apuntar a la URL correcta de la API.
- El frontend actual es la plantilla de Vite/React, así que puedes reemplazar `src/App.jsx` por la interfaz real del proyecto.
