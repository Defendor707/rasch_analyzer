from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI(title="Rasch Analyzer Backend", version="0.1.0")


@app.get("/health", tags=["health"]) 
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)


@app.post("/v1/analysis/finalize", tags=["analysis"]) 
def finalize_analysis() -> JSONResponse:
    # Placeholder endpoint: wired later to real logic
    return JSONResponse({"detail": "Not implemented"}, status_code=status.HTTP_501_NOT_IMPLEMENTED)


