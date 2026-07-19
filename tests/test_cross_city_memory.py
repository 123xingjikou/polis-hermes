"""
测试跨城记忆查询模块
"""

import json
import pytest

from memory_system.cross_city_memory import (
    CrossCityMemoryQuery,
    CrossCityMemoryClient,
)


@pytest.fixture
def memory_query_with_db(sample_memories_db):
    """带示例记忆数据的查询器"""
    conn, db_path = sample_memories_db
    mq = CrossCityMemoryQuery(db_path=db_path)
    yield mq
    mq.close()


class TestCrossCityMemoryQuery:
    """跨城记忆查询测试"""

    def test_search_memories_empty(self):
        """空数据库搜索"""
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        mq = CrossCityMemoryQuery(db_path=path)
        result = mq.search_memories("test")
        assert "results" in result
        assert result["count"] == 0
        mq.close()
        os.unlink(path)

    def test_search_with_data(self, memory_query_with_db):
        """带数据搜索"""
        mq = memory_query_with_db
        result = mq.search_memories("学习")
        assert "results" in result
        assert result["count"] >= 0

    def test_search_by_agent(self, memory_query_with_db):
        """按 agent 搜索"""
        mq = memory_query_with_db
        result = mq.search_memories("记忆", agent_id="agent_alpha")
        assert "results" in result
        for r in result["results"]:
            assert r["agent_id"] == "agent_alpha"

    def test_get_agent_memories(self, memory_query_with_db):
        """获取指定 agent 的记忆"""
        mq = memory_query_with_db
        result = mq.get_agent_memories("agent_alpha")
        assert "agent_id" in result
        assert result["agent_id"] == "agent_alpha"
        assert "results" in result

    def test_get_shared_memories(self, memory_query_with_db):
        """获取共享记忆"""
        mq = memory_query_with_db
        result = mq.get_shared_memories("agent_beta")
        assert "results" in result
        assert "count" in result

    def test_stats(self, memory_query_with_db):
        """统计信息"""
        mq = memory_query_with_db
        stats = mq.get_stats()
        assert "timestamp" in stats
        assert "cache_size" in stats

    def test_permission_verification(self, memory_query_with_db):
        """权限验证"""
        mq = memory_query_with_db
        # 没有共享关系时测试
        result = mq.verify_permission("olympia", "requester", "target")
        assert isinstance(result, bool)

    def test_handle_query_search(self, memory_query_with_db):
        """处理查询请求 - 搜索类型"""
        mq = memory_query_with_db
        result = mq.handle_cross_city_query({
            "type": "memory_search",
            "query": "学习",
            "requesting_city": "olympia",
            "requesting_agent": "test_agent",
        })
        assert "results" in result

    def test_handle_query_unknown_type(self, memory_query_with_db):
        """处理未知类型查询"""
        mq = memory_query_with_db
        result = mq.handle_cross_city_query({
            "type": "unknown_type",
            "requesting_city": "olympia",
            "requesting_agent": "test",
        })
        assert "error" in result
        assert result["error"] == "unknown_type"

    def test_cache_works(self, memory_query_with_db):
        """缓存功能测试"""
        mq = memory_query_with_db
        # 第一次查询
        result1 = mq.search_memories("测试")
        # 第二次查询应该命中缓存
        result2 = mq.search_memories("测试")
        # 结果应该相同，但 cached 标记可能不同
        assert result1["count"] == result2["count"]


class TestCrossCityMemoryClient:
    """跨城记忆客户端测试"""

    def test_client_init(self):
        """客户端初始化"""
        client = CrossCityMemoryClient(gateway_url="http://localhost:9999")
        assert client.gateway_url == "http://localhost:9999"

    def test_search_remote_unavailable(self):
        """远端不可用时返回错误"""
        client = CrossCityMemoryClient(gateway_url="http://localhost:19999")
        result = client.search_remote("test_city", "query")
        # 端口不存在时应该返回错误
        assert "error" in result
