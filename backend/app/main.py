"""
FastAPI Main Application
Entry point for Smart Traffic RL backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.simulation import router as simulation_router
from app.routes.metrics import router as metrics_router
from app.routes.advanced import router as advanced_router
from app.routes.dual_simulation import router as dual_router
from app.routes.evaluation import router as evaluation_router
from app.websocket import ws_router
from app.dual_websocket import dual_ws_router
import uvicorn


# Create FastAPI app
app = FastAPI(
    title="Smart Traffic RL System",
    description="Real-time traffic signal optimization using Reinforcement Learning and SUMO with Dual Simulation Comparison",
    version="3.0.0"
)

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(simulation_router)
app.include_router(metrics_router)
app.include_router(advanced_router)  # Weather, Emergency, Evaluation endpoints
app.include_router(dual_router)       # Dual simulation (Fixed vs RL) endpoints
app.include_router(evaluation_router, prefix="/api/evaluation", tags=["evaluation"]) # Static evaluation
app.include_router(ws_router)
app.include_router(dual_ws_router)    # Dual simulation WebSocket


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Smart Traffic RL System",
        "version": "3.0.0",
        "status": "running",
        "features": [
            "dual_simulation_comparison",
            "weather_awareness", 
            "emergency_priority", 
            "multi_junction_coordination",
            "time_based_rl_policies"
        ],
        "endpoints": {
            "simulation": "/api/simulation",
            "dual": "/api/dual",
            "metrics": "/api/metrics",
            "advanced": "/api/advanced",
            "websocket": "/ws",
            "dual_websocket": "/ws/dual"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "smart-traffic-rl"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
