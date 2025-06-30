"""
Pydantic schemas for AI System Health Monitoring
Defines models for health checks, status reporting, and system diagnostics
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Overall health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    REQUIRES_MIGRATION = "requires_migration"
    UNKNOWN = "unknown"


class ComponentStatus(str, Enum):
    """Individual component status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    REQUIRES_MIGRATION = "requires_migration"


class MigrationStatus(str, Enum):
    """Database migration status"""
    UP_TO_DATE = "up_to_date"
    MIGRATION_REQUIRED = "migration_required"
    MIGRATION_IN_PROGRESS = "migration_in_progress"
    MIGRATION_FAILED = "migration_failed"


# Component Health Models
class DatabaseHealth(BaseModel):
    """Database connectivity and schema health"""
    status: ComponentStatus = Field(..., description="Database component status")
    connection_test: bool = Field(..., description="Whether database connection is working")
    missing_tables: List[str] = Field(default_factory=list, description="List of missing required tables")
    migration_status: MigrationStatus = Field(..., description="Current migration status")
    last_migration: Optional[datetime] = Field(None, description="When last migration was run")
    error_message: Optional[str] = Field(None, description="Error message if database issues")


class AIProviderHealth(BaseModel):
    """AI provider connectivity and performance"""
    status: ComponentStatus = Field(..., description="AI provider status")
    provider_name: str = Field(..., description="Name of the AI provider")
    model_name: Optional[str] = Field(None, description="Currently active model")
    model_loaded: bool = Field(False, description="Whether model is loaded and ready")
    response_time: Optional[float] = Field(None, description="Average response time in seconds")
    queue_size: Optional[int] = Field(None, description="Current request queue size")
    error_rate: Optional[float] = Field(None, description="Error rate percentage")
    last_successful_request: Optional[datetime] = Field(None, description="When last successful request was made")
    error_message: Optional[str] = Field(None, description="Current error message if any")


class AgentHealth(BaseModel):
    """AI agent system health"""
    status: ComponentStatus = Field(..., description="Agent system status")
    active_agents: int = Field(0, description="Number of currently active agents")
    total_sessions: int = Field(0, description="Total number of chat sessions")
    active_sessions: int = Field(0, description="Number of active chat sessions")
    average_response_time: Optional[float] = Field(None, description="Average agent response time")
    successful_interactions: int = Field(0, description="Number of successful interactions")
    failed_interactions: int = Field(0, description="Number of failed interactions")
    last_activity: Optional[datetime] = Field(None, description="When last agent activity occurred")


class CircuitBreakerHealth(BaseModel):
    """Circuit breaker pattern health monitoring"""
    status: ComponentStatus = Field(..., description="Circuit breaker status")
    state: str = Field(..., description="Current circuit breaker state (CLOSED/OPEN/HALF_OPEN)")
    failure_count: int = Field(0, description="Current failure count")
    last_failure: Optional[datetime] = Field(None, description="When last failure occurred")
    next_attempt: Optional[datetime] = Field(None, description="When next attempt will be made")


# Tool and Integration Health
class ToolsHealth(BaseModel):
    """AI tools system health"""
    status: ComponentStatus = Field(..., description="Tools system status")
    registered_tools: int = Field(0, description="Number of registered tools")
    tools_used_last_hour: int = Field(0, description="Tools executions in last hour")
    successful_executions: int = Field(0, description="Successful tool executions")
    failed_executions: int = Field(0, description="Failed tool executions")
    average_execution_time: Optional[float] = Field(None, description="Average tool execution time")


class EventIntegrationHealth(BaseModel):
    """Event creation integration health"""
    status: ComponentStatus = Field(..., description="Event integration status")
    events_created_via_ai: int = Field(0, description="Events created through AI in last 24h")
    successful_creations: int = Field(0, description="Successful event creations")
    failed_creations: int = Field(0, description="Failed event creations")
    draft_conversion_rate: Optional[float] = Field(None, description="Draft to event conversion rate")


# Comprehensive Health Response
class SystemHealth(BaseModel):
    """Complete system health status"""
    overall_status: HealthStatus = Field(..., description="Overall system health status")
    timestamp: datetime = Field(..., description="When health check was performed")
    uptime: Optional[float] = Field(None, description="System uptime in seconds")
    version: Optional[str] = Field(None, description="System version")
    
    # Component health
    database: DatabaseHealth = Field(..., description="Database health status")
    ai_provider: AIProviderHealth = Field(..., description="AI provider health status")
    agents: AgentHealth = Field(..., description="Agent system health status")
    circuit_breaker: CircuitBreakerHealth = Field(..., description="Circuit breaker health status")
    tools: ToolsHealth = Field(..., description="Tools system health status")
    event_integration: EventIntegrationHealth = Field(..., description="Event integration health status")
    
    # Summary metrics
    critical_issues: List[str] = Field(default_factory=list, description="List of critical issues")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")


# Migration Models
class MigrationInfo(BaseModel):
    """Database migration information"""
    migration_name: str = Field(..., description="Name of the migration")
    description: str = Field(..., description="Description of what migration does")
    required: bool = Field(..., description="Whether this migration is required")
    estimated_time: Optional[str] = Field(None, description="Estimated time to complete")
    risks: List[str] = Field(default_factory=list, description="Potential risks")


class MigrationPlan(BaseModel):
    """Migration execution plan"""
    migrations_needed: List[MigrationInfo] = Field(..., description="List of required migrations")
    total_migrations: int = Field(..., description="Total number of migrations to run")
    estimated_total_time: Optional[str] = Field(None, description="Total estimated time")
    backup_recommended: bool = Field(True, description="Whether backup is recommended")
    risks: List[str] = Field(default_factory=list, description="Overall risks")


class MigrationResult(BaseModel):
    """Result of migration execution"""
    success: bool = Field(..., description="Whether migration succeeded")
    migrations_executed: List[str] = Field(..., description="List of executed migrations")
    migrations_skipped: List[str] = Field(default_factory=list, description="List of skipped migrations")
    execution_time: float = Field(..., description="Total execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if migration failed")
    rollback_available: bool = Field(False, description="Whether rollback is available")


# Performance Metrics
class PerformanceMetrics(BaseModel):
    """System performance metrics"""
    timestamp: datetime = Field(..., description="When metrics were collected")
    
    # Response times
    average_chat_response_time: Optional[float] = Field(None, description="Average chat response time")
    average_tool_execution_time: Optional[float] = Field(None, description="Average tool execution time")
    average_event_creation_time: Optional[float] = Field(None, description="Average event creation time")
    
    # Throughput
    requests_per_minute: Optional[float] = Field(None, description="Requests processed per minute")
    successful_requests_per_minute: Optional[float] = Field(None, description="Successful requests per minute")
    
    # Resource usage
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")
    
    # Error rates
    overall_error_rate: Optional[float] = Field(None, description="Overall error rate percentage")
    ai_provider_error_rate: Optional[float] = Field(None, description="AI provider error rate percentage")
    tool_error_rate: Optional[float] = Field(None, description="Tool execution error rate percentage")


# Diagnostic Models
class DiagnosticInfo(BaseModel):
    """Diagnostic information for troubleshooting"""
    component: str = Field(..., description="Component being diagnosed")
    checks_performed: List[str] = Field(..., description="List of diagnostic checks performed")
    results: Dict[str, Any] = Field(..., description="Diagnostic results")
    suggestions: List[str] = Field(default_factory=list, description="Suggested fixes")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Additional debug information")


class HealthSummary(BaseModel):
    """Simplified health summary for quick checks"""
    status: HealthStatus = Field(..., description="Overall status")
    critical_issues_count: int = Field(0, description="Number of critical issues")
    warnings_count: int = Field(0, description="Number of warnings")
    ai_available: bool = Field(False, description="Whether AI system is available")
    database_available: bool = Field(False, description="Whether database is available")
    last_check: datetime = Field(..., description="When last health check was performed")
    next_check: Optional[datetime] = Field(None, description="When next automatic check is scheduled") 