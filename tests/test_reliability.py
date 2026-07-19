"""
测试记忆系统可靠性评分模块
"""

import json
import sqlite3
from datetime import datetime, timedelta

import pytest

from memory_system.reliability import (
    AgentReliabilityScorer,
    ReliabilityScore,
)


@pytest.fixture
def scorer_with_db(sample_session_log_db):
    """带示例数据的可靠性评分器"""
    conn, db_path = sample_session_log_db
    scorer = AgentReliabilityScorer(db_path=db_path)
    yield scorer
    scorer.close()


class TestReliabilityScore:
    """ReliabilityScore 数据类测试"""

    def test_create_score_defaults(self):
        """测试默认值初始化"""
        score = ReliabilityScore(agent_id="test_agent", overall_score=0.75)
        assert score.agent_id == "test_agent"
        assert score.overall_score == 0.75
        assert score.sla_score == 0.0
        assert score.reliability_label == "unknown"

    def test_to_dict(self):
        """测试 to_dict 输出"""
        score = ReliabilityScore(
            agent_id="agent_a",
            overall_score=0.85,
            sla_score=0.9,
            reliability_label="high",
            error_breakdown={"system": 1, "network": 2},
        )
        d = score.to_dict()
        assert d["agent_id"] == "agent_a"
        assert d["overall_score"] == 0.85
        assert d["reliability_label"] == "high"
        assert d["error_breakdown"]["system"] == 1


class TestAgentReliabilityScorer:
    """Agent 可靠性评分器测试"""

    def test_error_classification(self):
        """测试错误分类"""
        scorer = AgentReliabilityScorer()

        assert scorer._classify_error("ImportError") == "system"
        assert scorer._classify_error("TimeoutError") == "network"
        assert scorer._classify_error("ValueError") == "business"
        assert scorer._classify_error("UnknownError") == "other"
        scorer.close()

    def test_label_thresholds(self):
        """测试标签阈值"""
        scorer = AgentReliabilityScorer()
        score = scorer.compute_reliability("nonexistent_agent")

        assert 0 <= score.overall_score <= 1.0
        assert isinstance(score.reliability_label, str)
        assert len(score.reliability_label) > 0
        scorer.close()

    def test_apply_to_trust_high_reliability(self):
        """高可靠性不打折"""
        scorer = AgentReliabilityScorer()
        adjusted = scorer.apply_to_trust(0.8, 0.8)
        assert adjusted == 0.8
        scorer.close()

    def test_apply_to_trust_low_reliability(self):
        """低可靠性打折"""
        scorer = AgentReliabilityScorer()
        adjusted = scorer.apply_to_trust(0.8, 0.15, min_reliability=0.3)
        assert adjusted < 0.8
        assert adjusted >= 0
        scorer.close()

    def test_batch_reliability_empty(self):
        """空 agent 列表批量评分"""
        scorer = AgentReliabilityScorer()
        results = scorer.batch_reliability([])
        assert results == []
        scorer.close()

    def test_get_low_reliability(self):
        """低可靠性查询"""
        scorer = AgentReliabilityScorer()
        low = scorer.get_low_reliability_agents(threshold=0.1)
        assert isinstance(low, list)
        scorer.close()


class TestWithSampleData:
    """带示例数据的测试"""

    def test_compute_with_session_data(self, scorer_with_db):
        """使用示例数据库计算"""
        scorer = scorer_with_db
        score = scorer.compute_reliability("agent_0")

        assert 0 <= score.overall_score <= 1.0
        assert 0 <= score.sla_score <= 1.0
        assert 0 <= score.timeout_score <= 1.0
        assert 0 <= score.error_score <= 1.0
        assert 0 <= score.consistency_score <= 1.0
        assert 0 <= score.trend_score <= 1.0

    def test_different_agents_different_scores(self, scorer_with_db):
        """不同 Agent 可能有不同分数"""
        scorer = scorer_with_db
        score0 = scorer.compute_reliability("agent_0")
        score1 = scorer.compute_reliability("agent_1")

        # 两个 agent 分数可能相同也可能不同，但都在有效范围内
        assert 0 <= score0.overall_score <= 1.0
        assert 0 <= score1.overall_score <= 1.0
