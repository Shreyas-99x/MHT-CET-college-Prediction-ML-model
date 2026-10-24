"""
FastAPI backend server for MHT CET College Predictor.
Wraps the existing predictor_model.py engine and serves the redesigned frontend.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import math
import numpy as np
import pandas as pd

from predictor_model import MhtCetPredictor, TOP_20_MAHARASHTRA_COLLEGES

app = FastAPI(title="MHT CET College Predictor API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Initialize predictor engine
predictor = MhtCetPredictor()


def sanitize_for_json(obj):
    """Recursively converts NaN and infinity values to None so JSON serialization succeeds."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, 'item'):  # numpy scalar
        val = obj.item()
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val
    return obj


def clean_dataframe_records(df: pd.DataFrame):
    """Safely converts a DataFrame to a list of dicts with no NaN/inf values."""
    if df is None or df.empty:
        return []
    clean_df = df.copy()
    clean_df = clean_df.replace([np.inf, -np.inf], np.nan)
    clean_df = clean_df.where(pd.notnull(clean_df), None)
    records = clean_df.to_dict(orient="records")
    return sanitize_for_json(records)


class PredictRequest(BaseModel):
    percentile: float = 92.5
    rank: Optional[int] = None
    category_group: str = "OPEN"
    specific_category: Optional[str] = None
    gender_quota: str = "All"
    university_quota: str = "All"
    cap_round: str = "ALL"
    districts: list = ["ALL"]
    branches: list = ["ALL"]
    top_20_only: bool = False
    prioritize_top_20: bool = True
    min_probability: float = 0.0


class TrendRequest(BaseModel):
    college_code: int
    course: str
    category: str = "OPEN"


@app.get("/api/options")
async def get_options():
    """Returns filter dropdown options for the frontend."""
    try:
        opts = predictor.get_filter_options()
        return {"success": True, "options": opts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/predict")
async def predict(req: PredictRequest):
    """Runs the prediction engine and returns college recommendations."""
    try:
        df_results, calc_pct, calc_rank = predictor.predict_colleges(
            percentile=req.percentile,
            rank=req.rank,
            category_group=req.category_group,
            specific_category=req.specific_category,
            gender_quota=req.gender_quota,
            university_quota=req.university_quota,
            branches=req.branches,
            districts=req.districts,
            cap_round=req.cap_round,
            min_probability=req.min_probability,
            top_20_only=req.top_20_only,
            prioritize_top_20=req.prioritize_top_20,
        )

        predictions = clean_dataframe_records(df_results)

        # Also fetch Top 20 showcase data
        df_top20 = predictor.get_top_20_analytics(
            percentile=req.percentile,
            category_group=req.category_group
        )
        top_20_showcase = clean_dataframe_records(df_top20)

        return {
            "success": True,
            "predictions": predictions,
            "top_20_showcase": top_20_showcase,
            "calculated_percentile": calc_pct,
            "calculated_rank": calc_rank,
            "total_results": len(predictions),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/top20")
async def get_top20_list():
    """Returns the static Top 20 colleges list."""
    return {"success": True, "colleges": TOP_20_MAHARASHTRA_COLLEGES}


@app.post("/api/trend")
async def get_trend(req: TrendRequest):
    """Returns historical cutoff trend data for a specific college+course+category."""
    try:
        df = predictor.get_college_trend(req.college_code, req.course, req.category)
        return {"success": True, "data": clean_dataframe_records(df)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/rank")
async def convert_percentile(percentile: float = 92.5):
    """Convert percentile to rank and vice versa."""
    rank = predictor.convert_percentile_to_rank(percentile)
    return {"success": True, "percentile": percentile, "rank": rank}


@app.get("/api/stats")
async def get_stats():
    """Returns database statistics for the hero section."""
    try:
        opts = predictor.get_filter_options()
        # Get actual college count from database
        try:
            with predictor._get_connection() as conn:
                res = conn.execute("SELECT COUNT(DISTINCT [College Code]) FROM cutoffs").fetchone()
                total_colleges = res[0] if res else 500
        except Exception:
            total_colleges = 500
        return {
            "success": True,
            "total_colleges": total_colleges,
            "total_branches": len(opts.get("courses", [])),
            "total_districts": len(opts.get("districts", [])),
            "data_years": "2023–2025",
            "top_20_count": 20,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# Serve static frontend files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{path:path}")
    async def serve_static(path: str):
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
