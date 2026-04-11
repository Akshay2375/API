import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from get_cutoff import get_eligible_cutoffs

router = APIRouter()

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

@router.post("/get-cutoffs")
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
