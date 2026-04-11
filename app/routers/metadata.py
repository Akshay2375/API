import sqlite3
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

def get_db():
    conn = sqlite3.connect("CETrankDB.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        conn.close()

@router.get("/metadata")
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
