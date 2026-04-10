import sqlite3
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers import chat
from app.core.config import settings
from get_cutoff import get_eligible_cutoffs


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A production-ready AI chatbot API that converts natural language queries "
        "about Maharashtra engineering colleges into SQL, executes them against a "
        "PostgreSQL database, and returns human-readable answers powered by Gemini. "
        "It also includes an engine for predicting college admission cutoffs."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


def get_db():
    conn = sqlite3.connect("CETrankDB.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        conn.close()


class CutoffRequest(BaseModel):
    user_gender: str
    user_category: str
    user_minority_list: List[str]
    user_home_university: str
    division: List[str] | None = None
    city: List[str] | None = None
    percentile_cet: float = 0.0
    percentile_ai: float = 0.0
    is_tech: bool
    is_civil: bool
    is_mechanical: bool
    is_electrical: bool
    is_electronic: bool
    is_other: bool
    is_ews: bool = False


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.post("/api/v1/get-cutoffs", tags=["Cutoffs"])
async def read_cutoffs(request: CutoffRequest, cursor: sqlite3.Cursor = Depends(get_db)):
    if request.is_ews and request.user_category.upper() != "OPEN":
        raise HTTPException(status_code=400, detail="EWS not applicable to the selected Category")

    try:
        min_pct_cet = max(0.0, request.percentile_cet - 10.0)
        max_pct_cet = min(100.0, request.percentile_cet + 10.0)
        min_pct_ai = max(0.0, request.percentile_ai - 10.0)
        max_pct_ai = min(100.0, request.percentile_ai + 10.0)

        results = get_eligible_cutoffs(
            cursor=cursor,
            user_category=request.user_category,
            user_minority_list=request.user_minority_list,
            user_home_university=request.user_home_university,
            gender=request.user_gender,
            cities=request.city,
            divisions=request.division,
            min_percentile_cet=min_pct_cet,
            max_percentile_cet=max_pct_cet,
            min_percentile_ai=min_pct_ai,
            max_percentile_ai=max_pct_ai,
            is_tech=request.is_tech,
            is_civil=request.is_civil,
            is_mechanical=request.is_mechanical,
            is_electrical=request.is_electrical,
            is_electronic=request.is_electronic,
            is_other=request.is_other,
            is_ews=request.is_ews
        )

        output = []
        for row in results:
            row_dict = dict(row)
            if row_dict.get("reservation_category") == "LEWS":
                row_dict["reservation_category"] = "EWS"
            elif row_dict.get("reservation_category") == "LAI":
                row_dict["reservation_category"] = "AI"
            output.append(row_dict)
        
        if output:
            print(output[0])
            
        user_details = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        user_details["calculated_bounds"] = {
            "min_percentile_cet": min_pct_cet,
            "max_percentile_cet": max_pct_cet,
            "min_percentile_ai": min_pct_ai,
            "max_percentile_ai": max_pct_ai,
        }

        return {
            "user_details": user_details,
            "count": len(output),
            "results": output
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/v1/metadata", tags=["Metadata"])
async def get_metadata(cursor: sqlite3.Cursor = Depends(get_db)):
    try:
        cursor.execute("SELECT DISTINCT city FROM colleges WHERE city IS NOT NULL ORDER BY city")
        cities = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT division FROM colleges WHERE division IS NOT NULL ORDER BY division")
        divisions = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT home_university FROM colleges WHERE home_university IS NOT NULL ORDER BY home_university")
        universities = [row[0] for row in cursor.fetchall()]

        return {
            "cities": cities,
            "divisions": divisions,
            "universities": universities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)



