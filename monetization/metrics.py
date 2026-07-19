"""
Metrics Collector
==================

Collects and aggregates all metrics needed for monetization decisions.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class SystemMetrics:
    uptime_percentage: float = 1.0
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0
    active_agents: int = 0
    total_decisions_made: int = 0
    last_updated: str = ""


@dataclass
class UserMetrics:
    total_users: int = 0
    daily_active_users: int = 0
    weekly_active_users: int = 0
    monthly_active_users: int = 0
    retention_rate_7d: float = 0.0
    retention_rate_30d: float = 0.0
    churn_rate: float = 0.0
    user_satisfaction_score: float = 0.0
    net_promoter_score: float = 0.0
    average_session_duration_minutes: float = 0.0


@dataclass
class GitHubMetrics:
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    closed_issues: int = 0
    contributors: int = 0
    commits_last_30d: int = 0
    pull_requests_merged: int = 0
    used_by_repos: int = 0


@dataclass
class FinancialMetrics:
    monthly_recurring_revenue: float = 0.0
    annual_recurring_revenue: float = 0.0
    customer_acquisition_cost: float = 0.0
    lifetime_value: float = 0.0
    runway_months: float = 0.0
    burn_rate_monthly: float = 0.0


@dataclass
class SupportMetrics:
    open_tickets: int = 0
    avg_resolution_hours: float = 0.0
    satisfaction_score: float = 0.0
    escalation_rate: float = 0.0
    self_service_percentage: float = 0.0


@dataclass
class AllMetrics:
    system: SystemMetrics = field(default_factory=SystemMetrics)
    users: UserMetrics = field(default_factory=UserMetrics)
    github: GitHubMetrics = field(default_factory=GitHubMetrics)
    financial: FinancialMetrics = field(default_factory=FinancialMetrics)
    support: SupportMetrics = field(default_factory=SupportMetrics)
    timestamp: str = ""

    def to_dict(self) -> dict:
        import dataclasses
        return {
            "system": dataclasses.asdict(self.system),
            "users": dataclasses.asdict(self.users),
            "github": dataclasses.asdict(self.github),
            "financial": dataclasses.asdict(self.financial),
            "support": dataclasses.asdict(self.support),
            "timestamp": self.timestamp,
        }


class MetricsCollector:
    """Collects metrics from various sources."""

    def __init__(self, db_path: str = "city_state.db"):
        self.db_path = db_path
        self._last_collection = None
        self._cache_ttl = timedelta(minutes=5)

    def collect_all(self) -> AllMetrics:
        metrics = AllMetrics()
        metrics.timestamp = datetime.utcnow().isoformat()
        self._collect_system_metrics(metrics.system)
        self._collect_user_metrics(metrics.users)
        self._collect_github_metrics(metrics.github)
        self._collect_financial_metrics(metrics.financial)
        self._collect_support_metrics(metrics.support)
        self._last_collection = datetime.utcnow()
        return metrics

    def _collect_system_metrics(self, metrics: SystemMetrics) -> None:
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(*) FROM agents WHERE status = 'active'")
                    metrics.active_agents = cursor.fetchone()[0]
                except Exception:
                    metrics.active_agents = 1
                try:
                    cursor.execute("SELECT COUNT(*) FROM decisions")
                    metrics.total_decisions_made = cursor.fetchone()[0]
                except Exception:
                    metrics.total_decisions_made = 0
                conn.close()
        except Exception:
            pass
        metrics.last_updated = datetime.utcnow().isoformat()

    def _collect_user_metrics(self, metrics: UserMetrics) -> None:
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM user_sessions")
                    metrics.total_users = cursor.fetchone()[0]
                except Exception:
                    metrics.total_users = 0
                try:
                    cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
                    cursor.execute(
                        "SELECT COUNT(DISTINCT user_id) FROM user_sessions WHERE timestamp > ?",
                        (cutoff,)
                    )
                    metrics.daily_active_users = cursor.fetchone()[0]
                except Exception:
                    metrics.daily_active_users = 0
                conn.close()
        except Exception:
            pass

    def _collect_github_metrics(self, metrics: GitHubMetrics) -> None:
        github_token = os.getenv("GITHUB_TOKEN")
        repo_owner = os.getenv("GITHUB_REPO_OWNER")
        repo_name = os.getenv("GITHUB_REPO_NAME")
        if not (github_token and repo_owner and repo_name):
            return
        try:
            import urllib.request
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"token {github_token}")
            req.add_header("Accept", "application/vnd.github.v3+json")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            metrics.stars = data.get("stargazers_count", 0)
            metrics.forks = data.get("forks_count", 0)
            metrics.watchers = data.get("subscribers_count", 0)
            metrics.open_issues = data.get("open_issues_count", 0)
        except Exception:
            pass

    def _collect_financial_metrics(self, metrics: FinancialMetrics) -> None:
        metrics.monthly_recurring_revenue = 0.0
        metrics.annual_recurring_revenue = 0.0

    def _collect_support_metrics(self, metrics: SupportMetrics) -> None:
        metrics.open_tickets = 0
        metrics.avg_resolution_hours = 0.0

    def get_feature_completeness(self) -> float:
        core_features = [
            "agent_registration", "agent_communication", "decision_engine",
            "governance_system", "memory_management", "evolution_engine",
            "user_interface", "api_endpoints", "authentication", "payment_processing",
        ]
        completed = 0
        if os.path.exists("agent_registry.py"): completed += 1
        if os.path.exists("polis_v3.py"): completed += 1
        if os.path.exists("agent_supervisor.py"): completed += 1
        if os.path.exists("ecosystem"): completed += 1
        if os.path.exists("comms"): completed += 1
        if os.path.exists("memory_system"): completed += 1
        if os.path.exists("autonomous_evo_engine.py"): completed += 1
        if os.path.exists("autonomous_polis.py"): completed += 1
        if os.path.exists("city/main.py"): completed += 1
        return min(completed / len(core_features), 1.0)
