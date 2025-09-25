"""
Admin endpoints for database management and system health.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from app.db import DatabaseFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/db", tags=["Admin"])


@router.get('/init')
async def db_init_confirmation():
    """Show confirmation page before wiping database"""
    from app.config import Config

    db_type, db_uri, db_name = Config.get_db_params()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Database Reset Confirmation</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .danger {{ color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .buttons {{ margin: 30px 0; text-align: center; }}
            .btn {{ padding: 12px 30px; margin: 0 10px; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: bold; }}
            .btn-danger {{ background-color: #dc3545; color: white; }}
            .btn-secondary {{ background-color: #6c757d; color: white; }}
            .btn:hover {{ opacity: 0.8; }}
            .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>⚠️ Database Reset Confirmation</h1>

        <div class="danger">
            <h3>🚨 WARNING: DESTRUCTIVE OPERATION</h3>
            <p><strong>This action will permanently delete ALL data in your {db_type} database!</strong></p>
        </div>

        <div class="warning">
            <h4>What will happen:</h4>
            <ul>
                <li>All indices/collections will be deleted</li>
                <li>All stored data will be lost forever</li>
                <li>Database will be reinitialized with correct mappings</li>
                <li>This operation cannot be undone</li>
            </ul>
        </div>

        <div class="info">
            <p><strong>Database:</strong> {db_type}</p>
            <p><strong>Database Name:</strong> {db_name}</p>
        </div>

        <div class="buttons">
            <form method="post" action="/api/db/init/confirmed" style="display: inline;">
                <button type="submit" class="btn btn-danger"
                        onclick="return confirm('Are you absolutely sure? This will delete ALL data!')">
                    YES - Delete All Data
                </button>
            </form>
            <a href="/api/db/report" class="btn btn-secondary">
               Cancel - Show Status Instead
            </a>
        </div>

        <p><em>Tip: Use <a href="/api/db/report">GET /api/db/report</a> to check database status before proceeding.</em></p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.post('/init/confirmed')
async def db_init_confirmed():
    """Complete wipe and reinitialize database with correct mappings"""
    try:
        db_instance = DatabaseFactory.get_instance()

        # Call the wipe and reinit method
        success = await db_instance.core.wipe_and_reinit()

        if success:
            return {
                "status": "success",
                "message": "Database wiped and reinitialized successfully"
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Database reinitialization failed"
                }
            )

    except Exception as e:
        logger.error(f"Database init failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Database init failed: {str(e)}"
            }
        )


@router.get('/report')
async def db_report():
    """Get database status report including mapping validation"""
    try:
        db_instance = DatabaseFactory.get_instance()

        # Get database report
        report = await db_instance.core.get_status_report()

        # Extract database type and put it first
        database_type = report.pop("database", "unknown")

        return {
            "database": database_type,
            "report": report
        }

    except Exception as e:
        logger.error(f"Database report failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Database report failed: {str(e)}"
            }
        )