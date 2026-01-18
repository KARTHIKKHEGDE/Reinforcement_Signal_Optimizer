# How to Run the Project

## 1. Start Backend (Traffic Logic Core)
Open a terminal, navigate to the `backend` folder, and run the server:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

*Server will start at: http://localhost:8000*

## 2. Start Frontend (Control Dashboard)
Open a **new** terminal, navigate to the `frontend` folder, and start the UI:

```bash
cd frontend
npm run dev
```

*Dashboard will open at: http://localhost:3000*
