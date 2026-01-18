from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
import pandas as pd
import os
import sys

# Add backend to path to allow sibling imports
sys.path.append(os.getcwd())

from evaluation.evaluate import RLEvaluator
from evaluation.baseline import BaselineEvaluator
from evaluation.compare import PerformanceComparator
from app.config import settings

router = APIRouter()

class ComparisonRequest(BaseModel):
    location: str = "silk_board"
    hour: int = 9  # Default to 9 AM peak
    episodes: int = 1

@router.post("/run")
async def run_comparison(request: ComparisonRequest):
    """
    Run a quick comparison between RL and Fixed-Time for a specific hour.
    """
    try:
        # 1. Define paths
        model_path = settings.MODEL_POLICY_PEAK  # Ensure this matches the hour logic if complex
        if 10 <= request.hour < 17:
             model_path = settings.MODEL_POLICY_OFF_PEAK
        elif request.hour >= 22 or request.hour < 7:
             model_path = settings.MODEL_POLICY_NIGHT
             
        data_path = f"data/{request.location}/{request.location}_arrival_rates.csv"
        
        if not os.path.exists(data_path):
             # Fallback to absolute path or check data dir
             data_path = os.path.join(os.getcwd(), "data", request.location, f"{request.location}_arrival_rates.csv")
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"Model not found: {model_path}")
            
        if not os.path.exists(data_path):
            raise HTTPException(status_code=404, detail=f"Data not found: {data_path}")
            
        print(f"🔬 Starting comparison for Hour {request.hour} at {request.location}")
        
        # 2. Run RL Evaluation
        print("   Running RL Evaluation...")
        rl_evaluator = RLEvaluator(model_path=model_path, verbose=True)
        rl_result = rl_evaluator.evaluate_hour(
            hour=request.hour,
            arrival_rates_csv=data_path,
            n_episodes=request.episodes
        )
        rl_evaluator.close()
        
        # 3. Run Baseline Evaluation
        print("   Running Baseline Evaluation...")
        baseline_evaluator = BaselineEvaluator(verbose=True)
        baseline_result = baseline_evaluator.evaluate_hour(
            hour=request.hour,
            arrival_rates_csv=data_path,
            n_episodes=request.episodes
        )
        # Baseline evaluator doesn't have close() method in the viewed file, but Env does.
        # Assuming we need to close env
        if hasattr(baseline_evaluator, 'env'):
            baseline_evaluator.env.close()
            
        # 4. Compare results
        # Create minimal DFs for the comparator
        rl_df = pd.DataFrame([rl_result])
        baseline_df = pd.DataFrame([baseline_result])
        
        # Save temp files for Comparator (it reads from CSV)
        # OR we can modify comparator to accept DFs. 
        # But Comparator code reads from CSV in __init__.
        # Let's save to temp csvs
        output_dir = "results/temp_compare"
        os.makedirs(output_dir, exist_ok=True)
        
        rl_csv = os.path.join(output_dir, "rl.csv")
        base_csv = os.path.join(output_dir, "base.csv")
        
        rl_df.to_csv(rl_csv, index=False)
        baseline_df.to_csv(base_csv, index=False)
        
        comparator = PerformanceComparator(rl_csv, base_csv)
        comp_df = comparator.calculate_improvements()
        
        # Convert to dict
        result_dict = comp_df.to_dict(orient='records')[0]
        
        return {
            "status": "success",
            "hour": request.hour,
            "metrics": {
                "queue_length": {
                    "rl": result_dict['avg_queue_length_rl'],
                    "fixed": result_dict['avg_queue_length_baseline'],
                    "improvement": result_dict['avg_queue_length_improvement_pct']
                },
                "wait_time": {
                    "rl": result_dict['avg_vehicle_delay_rl'],
                    "fixed": result_dict['avg_vehicle_delay_baseline'],
                    "improvement": result_dict['avg_vehicle_delay_improvement_pct']
                },
                "throughput": {
                    "rl": result_dict['total_throughput_rl'],
                    "fixed": result_dict['total_throughput_baseline'],
                    "improvement": result_dict['total_throughput_improvement_pct']
                }
            }
        }

    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
