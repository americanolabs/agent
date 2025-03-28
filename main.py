import time
import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import asyncio
from src.agent import CdpAgent, CdpAgentClassifier
from models.schemas import *
load_dotenv()

app = FastAPI(
    title="CDP Agent API",
    description="API for interacting with CDP Agent with Knowledge Base",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_KNOWLEDGE = "https://americanolabs-backend.vercel.app/staking"

cdp_agent_classifier = CdpAgentClassifier()
cdp_agent = CdpAgent(url=URL_KNOWLEDGE)

@app.on_event("startup")
async def startup_event():
    """Initialize agent when the API starts."""
    await cdp_agent_classifier.initialize()
    await cdp_agent.initialize()


@app.post("/generate-risk-profile")
async def assess_risk(request: QueryRequestClassifier):
    """
    Endpoint to assess risk profile based on user responses.
    Returns a JSON with risk assessment level.
    """
    try:
        response = await cdp_agent_classifier.process_query(query=request.data)
        parsed_response = json.loads(response)
        
        return JSONResponse(content=parsed_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-protocol")
async def query_agent_sync(request: QueryRequest):
    """
    Synchronous endpoint to query the CDP agent
    """
    try:
        start_time = time.time()
        
        response = await asyncio.wait_for(
            cdp_agent.process_query(query=request.query), timeout=30.0)

        parsed_response = json.loads(response) if isinstance(response, str) else response
        formatted_response = {
            "id_project": str(parsed_response.get("id_project", "")),
            "chain": str(parsed_response.get("chain", ""))
        }

        return JSONResponse(content=formatted_response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "thread_pool_info": {
            "max_workers": cdp_agent.thread_pool._max_workers,
            "active_threads": cdp_agent.thread_pool._work_queue.qsize()
        }
    }
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)