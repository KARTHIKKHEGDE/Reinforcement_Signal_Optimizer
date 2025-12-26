"""
FastAPI Main Application
Entry point for Smart Traffic RL backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import simulation, metrics
from app.websocket import ws_router
import uvicorn


# Create FastAPI app
app = FastAPI(
    title="Smart Traffic RL System",
    description="Real-time traffic signal optimization using Reinforcement Learning and SUMO",
    version="1.0.0"
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
app.include_router(simulation.router)
app.include_router(metrics.router)
app.include_router(ws_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Smart Traffic RL System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "simulation": "/api/simulation",
            "metrics": "/api/metrics",
            "websocket": "/ws"
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
