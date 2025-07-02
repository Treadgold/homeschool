"""
AI Health Service

This service handles all AI system health monitoring and migration functionality, including:
- Comprehensive health checks for AI components
- Database migration for AI tables
- Migration debug information
- Status monitoring and reporting

Extracted from main.py as part of Phase 2 AI architecture refactoring.
"""

import logging
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from app.models import User


class HealthService:
    """Service for AI system health monitoring and migration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_health_data(self, db: Session) -> Dict[str, Any]:
        """Comprehensive AI system health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        # Enhanced Database Health Check
        try:
            inspector = inspect(db.bind)
            required_tables = {"chat_conversations", "chat_messages", "agent_sessions"}
            existing_tables = set(inspector.get_table_names())
            missing_tables = list(required_tables - existing_tables)
            
            db_status = {
                "status": "healthy" if not missing_tables else "requires_migration",
                "message": "All required tables present." if not missing_tables else f"Missing agent tables: {', '.join(missing_tables)}",
                "details": {
                    "required": sorted(list(required_tables)),
                    "found": sorted(list(existing_tables.intersection(required_tables))),
                    "missing": sorted(missing_tables)
                }
            }
            health_status["checks"]["database"] = db_status
            
            if missing_tables:
                health_status["overall_status"] = "requires_migration"
                
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "error",
                "message": "Failed to inspect database tables.",
                "error": str(e)
            }
            health_status["overall_status"] = "unhealthy"
        
        # AI Provider Health Check (Refactored for LangChain)
        try:
            from app.ai_assistant import ai_manager
            current_config = ai_manager.get_current_model_config()
            
            if current_config and current_config.endpoint_url:
                provider_info = {
                    "status": "healthy",
                    "provider": current_config.provider,
                    "model": current_config.model_name,
                    "endpoint": current_config.endpoint_url
                }
            elif os.getenv("OLLAMA_ENDPOINT"):
                 provider_info = {
                    "status": "healthy",
                    "provider": "Ollama",
                    "model": "Default (not specified in config)",
                    "endpoint": os.getenv("OLLAMA_ENDPOINT")
                }
            else:
                provider_info = {
                    "status": "unavailable",
                    "message": "No AI provider endpoint configured (OLLAMA_ENDPOINT is not set)."
                }
                if health_status["overall_status"] == "healthy":
                    health_status["overall_status"] = "degraded"

            health_status["checks"]["ai_provider"] = provider_info
            
        except Exception as e:
            health_status["checks"]["ai_provider"] = {
                "status": "error",
                "message": "Could not check AI provider status.",
                "error": str(e)
            }
            health_status["overall_status"] = "unhealthy"
        
        # Circuit Breaker Status
        health_status["checks"]["circuit_breaker"] = {
            "status": "monitoring",
            "message": "Circuit breaker pattern active for fault tolerance."
        }
        
        return health_status
    
    async def get_health_check_response(self, db: Session) -> Response:
        """Get health check with proper HTTP status code"""
        health_data = await self.get_health_data(db)
        
        # Determine HTTP status code
        if health_data["overall_status"] == "unhealthy":
            status_code = 503  # Service Unavailable
        elif health_data["overall_status"] == "degraded":
            status_code = 200  # Still OK, but with warnings
        else:
            status_code = 200
        
        import json
        return Response(
            content=json.dumps(health_data), 
            media_type="application/json", 
            status_code=status_code
        )
    
    async def get_health_status_html(self, user: User, db: Session) -> str:
        """HTMX endpoint for health status display"""
        try:
            health_data = await self.get_health_data(db)
            
            if health_data.get("overall_status") == "healthy":
                return ""  # No alert needed
            
            # Show migration alert
            missing_tables = health_data.get("checks", {}).get("database", {}).get("details", {}).get("missing", [])
            return f"""
            <div class="alert alert-warning">
                <h4>⚠️ Database Migration Required</h4>
                <p>The AI agent system requires database updates to function properly.</p>
                <p><strong>Missing tables:</strong> {', '.join(missing_tables)}</p>
                <button class="btn btn-primary" 
                        hx-post="/migrate"
                        hx-target="#health-status"
                        hx-swap="innerHTML">
                    🔧 Run Migration Now
                </button>
            </div>
            """
        except Exception as e:
            return f"""
            <div class="alert alert-error">
                <h4>❌ Health Check Failed</h4>
                <p>Unable to check AI system status: {str(e)}</p>
            </div>
            """
    
    async def run_database_migration(self, user: User, db: Session) -> str:
        """Run database migration for agent tables"""
        try:
            # Verify user is admin
            if not user or not user.is_admin:
                return """
                <div class="alert alert-error">
                    <h4>❌ Access Denied</h4>
                    <p>Admin privileges required to run migrations</p>
                </div>
                """
            
            # Read migration files
            # First run the enum fix migration
            fix_migration_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations", "fix_agent_enum_types.sql")
            main_migration_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations", "add_agent_tables.sql")
            
            migrations_to_run = []
            
            # Add fix migration if it exists
            if os.path.exists(fix_migration_path):
                migrations_to_run.append(("fix_agent_enum_types.sql", fix_migration_path))
            
            # Add main migration
            if os.path.exists(main_migration_path):
                migrations_to_run.append(("add_agent_tables.sql", main_migration_path))
            
            if not migrations_to_run:
                return """
                <div class="alert alert-error">
                    <h4>❌ Migration Files Not Found</h4>
                    <p>No migration files found</p>
                </div>
                """
            
            total_executed = 0
            total_skipped = 0
            
            # Run each migration file
            for migration_name, migration_path in migrations_to_run:
                self.logger.info(f"🔄 Running migration: {migration_name}")
                
                if not os.path.exists(migration_path):
                    return f"""
                    <div class="alert alert-error">
                        <h4>❌ Migration File Not Found</h4>
                        <p>Migration file not found at: {migration_path}</p>
                    </div>
                    """
                
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                
                # Split into individual statements (excluding comments and empty lines)
                statements = self._parse_migration_statements(migration_sql)
                
                # Execute each statement individually for this migration
                executed_statements = 0
                skipped_statements = 0
                
                for i, statement in enumerate(statements):
                    if statement.strip():
                        try:
                            db.execute(text(statement))
                            executed_statements += 1
                            self.logger.info(f"✅ Executed statement {i+1} from {migration_name}: {statement[:50]}...")
                        except Exception as stmt_error:
                            # If it's a "already exists" error, that's okay
                            if "already exists" in str(stmt_error).lower():
                                skipped_statements += 1
                                self.logger.info(f"⏭️ Skipped statement {i+1} from {migration_name} (already exists): {statement[:50]}...")
                                continue
                            else:
                                self.logger.error(f"❌ Failed statement {i+1} from {migration_name}: {str(stmt_error)}")
                                raise stmt_error
                
                total_executed += executed_statements
                total_skipped += skipped_statements
                self.logger.info(f"✅ Completed migration {migration_name}: {executed_statements} executed, {skipped_statements} skipped")
            
            db.commit()
            
            return f"""
            <div class="alert alert-success">
                <h4>✅ Migration Completed</h4>
                <p>Database migration completed successfully! Executed {total_executed} statements, skipped {total_skipped} existing.</p>
            </div>
            """
            
        except Exception as e:
            db.rollback()
            error_msg = str(e)
            self.logger.error(f"❌ Migration failed: {error_msg}")
            self.logger.error(traceback.format_exc())
            
            return f"""
            <div class="alert alert-error">
                <h4>❌ Migration Failed</h4>
                <p>Error: {error_msg}</p>
                <button class="btn btn-primary" 
                        hx-post="/migrate"
                        hx-target="#health-status"
                        hx-swap="innerHTML">
                    🔄 Retry Migration
                </button>
            </div>
            """
    
    def get_migration_debug_info(self, user: User, db: Session) -> Dict[str, Any]:
        """Debug migration info - shows what would happen without running"""
        migration_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations", "add_agent_tables.sql")
        
        debug_info = {
            "user_info": {
                "user_id": user.id if user else None,
                "is_admin": user.is_admin if user else False,
                "email": user.email if user else None
            },
            "migration_file": {
                "path": migration_path,
                "exists": os.path.exists(migration_path),
                "absolute_path": os.path.abspath(migration_path)
            },
            "database_info": {
                "connection_working": True  # If we got here, DB is connected
            }
        }
        
        # Check if migration file exists and is readable
        if os.path.exists(migration_path):
            try:
                with open(migration_path, 'r') as f:
                    content = f.read()
                    debug_info["migration_file"]["size"] = len(content)
                    debug_info["migration_file"]["line_count"] = len(content.split('\n'))
                    debug_info["migration_file"]["readable"] = True
            except Exception as e:
                debug_info["migration_file"]["readable"] = False
                debug_info["migration_file"]["read_error"] = str(e)
        
        # Check what tables already exist
        try:
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('chat_conversations', 'chat_messages', 'agent_sessions')
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            debug_info["database_info"]["existing_agent_tables"] = existing_tables
            debug_info["database_info"]["needs_migration"] = len(existing_tables) < 3
        except Exception as e:
            debug_info["database_info"]["table_check_error"] = str(e)
        
        return debug_info
    
    def _parse_migration_statements(self, migration_sql: str) -> List[str]:
        """Parse migration SQL into individual statements"""
        statements = []
        current_statement = []
        in_function = False
        in_do_block = False
        
        for line in migration_sql.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
            
            # Track if we're inside a DO block
            if line.upper().startswith('DO $$'):
                in_do_block = True
            elif line.upper().startswith('END $$;'):
                in_do_block = False
                current_statement.append(line)
                statements.append('\n'.join(current_statement))
                current_statement = []
                continue
                
            # Track if we're inside a function definition
            if 'CREATE OR REPLACE FUNCTION' in line.upper():
                in_function = True
            elif line.endswith('$$ language \'plpgsql\';') or line.endswith("$$ language 'plpgsql';"):
                in_function = False
                current_statement.append(line)
                statements.append('\n'.join(current_statement))
                current_statement = []
                continue
            
            current_statement.append(line)
            
            # If not in function/DO block and line ends with semicolon, end statement
            if not in_function and not in_do_block and line.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements 