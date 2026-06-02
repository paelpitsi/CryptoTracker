"""
Router for /api/server/status endpoint.

Health check that verifies server uptime and external API availability.
"""

import time

from fastapi import APIRouter

from cryptotracker.api.frankfurter import frankfurter_client
from cryptotracker.api.coingecko import coingecko_client
from cryptotracker.server.schemas import ExternalAPIStatus, ServerStatusResponse

router = APIRouter(tags=["server"])

# Record server start time at module load
_start_time: float = time.time()


@router.get("/server/status", response_model=ServerStatusResponse)
async def server_status():
    """Check server health and external API availability."""
    uptime = time.time() - _start_time

    # Check external APIs (sequential to avoid overwhelming)
    frankfurter_status = await frankfurter_client.check_health()
    coingecko_status = await coingecko_client.check_health()

    return ServerStatusResponse(
        status="ok",
        version="1.0.0",
        uptime_seconds=round(uptime, 1),
        external_apis=ExternalAPIStatus(
            frankfurter=frankfurter_status,
            coingecko=coingecko_status,
        ),
    )
