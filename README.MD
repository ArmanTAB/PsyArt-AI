cd core
py -3.11 -m uvicorn server:app --reload --port 8000

cd interface
npm install
npm run dev
```

После этого открыть в браузере:
```
http://localhost:5173