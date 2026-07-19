"""
🧪 城邦生态扩展包 - 完整集成测试
=================================

测试覆盖：
1. 环境系统 - 区域管理、资源生成消耗、再生、生态熵
2. 时间系统 - 时钟推进、季节、时段、日历
3. 事件系统 - 概率触发、影响应用、冷却
4. 互锁协议 - 事件发布订阅、因果链接、反馈回路
5. 一键套件 - 集成运行、统计、关闭

运行方式：
    cd <polis_root>
    python ecosystem/test_all.py
"""

# 修复项目根目录的 inspect.py 遮蔽标准库问题
import sys as _sys
_StdLib = r"C:\Users\dfhai\AppData\Local\Programs\Python\Python313\Lib"
if _StdLib not in _sys.path:
    _sys.path.insert(0, _StdLib)
import os
import sys
import time
import tempfile
import unittest
import logging
from pathlib import Path

# 让 import 找到本包
HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))

# 配置日志
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('ecosystem.test')


def get_test_data_dir() -> str:
    """使用临时目录避免污染真实数据"""
    tmp = Path(tempfile.gettempdir()) / f"polis_ecosystem_test_{int(time.time())}"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "state").mkdir(exist_ok=True)
    return str(tmp)


class TestEnvironment(unittest.TestCase):
    """环境系统测试"""

    def setUp(self):
        self.data_dir = get_test_data_dir()
        from ecosystem.environment import create_default_environment
        self.env = create_default_environment(self.data_dir)

    def tearDown(self):
        try:
            self.env.db.close()
        except Exception:
            pass

    def test_default_regions_created(self):
        """默认区域应该被创建"""
        regions = self.env.list_regions()
        self.assertGreaterEqual(len(regions), 3, "应该至少创建 3 个默认区域")

    def test_resources_initialized(self):
        """资源应该被初始化"""
        for r in self.env.list_regions():
            resources = self.env.get_all_resources(r.region_id)
            for rt in ["energy", "materials", "food", "water"]:
                self.assertIn(rt, resources, f"{r.region_id} 应该初始化 {rt}")
                self.assertGreater(resources[rt], 0, f"{rt} 应该 > 0")

    def test_consume_success(self):
        """成功消耗资源"""
        from ecosystem.environment import ResourceType
        success, remaining = self.env.consume(
            "central_plains", "agent_test", ResourceType.ENERGY, 5.0, "test"
        )
        self.assertTrue(success)
        self.assertGreater(remaining, 0)

    def test_consume_failure_insufficient(self):
        """资源不足时消耗失败"""
        from ecosystem.environment import ResourceType
        success, _ = self.env.consume(
            "central_plains", "agent_test", ResourceType.ENERGY, 99999.0, "test"
        )
        self.assertFalse(success)

    def test_harvest(self):
        """收获资源"""
        from ecosystem.environment import ResourceType
        region_id = "central_plains"
        before = self.env.get_resource(region_id, ResourceType.ENERGY)
        new_val = self.env.harvest(region_id, "agent_test", ResourceType.ENERGY, 10.0, "harvest")
        self.assertGreater(new_val, before)

    def test_regenerate(self):
        """资源再生"""
        from ecosystem.environment import ResourceType
        region_id = "central_plains"
        self.env.consume(region_id, "test", ResourceType.FOOD, 30.0, "test")
        before = self.env.get_resource(region_id, ResourceType.FOOD)
        self.env.regenerate(region_id, dt_seconds=10.0)
        after = self.env.get_resource(region_id, ResourceType.FOOD)
        self.assertGreater(after, before, "再生后应该增加")

    def test_entropy_calculation(self):
        """生态熵计算"""
        entropy = self.env.calculate_entropy()
        self.assertGreaterEqual(entropy, 0.0)
        self.assertLessEqual(entropy, 1.0)

    def test_population_capacity(self):
        """人口容量限制"""
        region_id = "central_plains"
        region = self.env.get_region(region_id)
        success, _ = self.env.add_population(region_id, region.max_population + 100)
        self.assertFalse(success)

    def test_season_effects(self):
        """季节对资源的影响"""
        from ecosystem.environment import Season
        # 先触发一次春季（确保不是默认状态）
        self.env.set_season(Season.SPRING)
        mult_spring = self.env.get_season_multiplier("food")
        # 切换到冬季
        self.env.set_season(Season.WINTER)
        mult_winter = self.env.get_season_multiplier("food")
        # 春 food=1.2, 冬 food=0.6
        self.assertLess(mult_winter, mult_spring, f"冬季食物({mult_winter})应该比春季({mult_spring})少")


class TestTemporal(unittest.TestCase):
    """时间系统测试"""

    def setUp(self):
        self.data_dir = get_test_data_dir()
        from ecosystem.temporal import create_default_temporal
        self.t = create_default_temporal(self.data_dir)

    def tearDown(self):
        try:
            self.t.db.close()
        except Exception:
            pass

    def test_default_calendar(self):
        """默认日历已初始化"""
        entries = self.t.list_calendar()
        self.assertGreater(len(entries), 0, "默认日历应该非空")

    def test_clock_advancement(self):
        """时钟推进"""
        before = self.t.get_clock()["world_day"]
        self.t.advance(24)
        after = self.t.get_clock()["world_day"]
        self.assertEqual(after, before + 1)

    def test_year_rollover(self):
        """跨年"""
        before = self.t.get_clock()["world_year"]
        self.t.advance(24 * 360)
        after = self.t.get_clock()["world_year"]
        self.assertEqual(after, before + 1)

    def test_time_of_day(self):
        """时段识别"""
        from ecosystem.temporal import TimeOfDay
        for h in [6, 9, 13, 16, 19, 22]:
            self.t.db.update_clock(hour=h)
            tod = self.t.get_time_of_day()
            self.assertIsInstance(tod, TimeOfDay)

    def test_season(self):
        """季节识别"""
        for day, expected in [(1, "spring"), (100, "summer"),
                              (200, "autumn"), (300, "winter")]:
            self.t.db.update_clock(day_of_year=day)
            self.assertEqual(self.t.get_season(), expected)


class TestEvents(unittest.TestCase):
    """事件系统测试"""

    def setUp(self):
        self.data_dir = get_test_data_dir()
        from ecosystem.events import create_default_events
        self.es = create_default_events(self.data_dir)

    def tearDown(self):
        try:
            self.es.db.close()
        except Exception:
            pass

    def test_tick_triggers(self):
        """tick 触发事件"""
        triggered = self.es.tick(current_season="spring", current_entropy=0.3)
        self.assertGreaterEqual(len(triggered), 0)
        self.assertLessEqual(len(triggered), self.es.max_events_per_tick)

    def test_event_recording(self):
        """事件被记录"""
        initial = len(self.es.list_events(limit=100))
        self.es.tick(current_season="spring", current_entropy=0.5)
        after = len(self.es.list_events(limit=100))
        self.assertGreaterEqual(after, initial)

    def test_high_entropy_triggers(self):
        """高熵测试"""
        for _ in range(5):
            self.es.tick(current_season="winter", current_entropy=0.9)
        events = self.es.list_events(limit=20)
        self.assertGreater(len(events), 0)


class TestInterlocks(unittest.TestCase):
    """互锁协议测试"""

    def setUp(self):
        from ecosystem.interlocks import InterlockBus, InterlockEvent
        self.bus = InterlockBus()
        self.received = []
        self.bus.subscribe("test.event", lambda e: self.received.append(e))

    def test_publish_subscribe(self):
        """发布订阅"""
        from ecosystem.interlocks import InterlockEvent
        ev = InterlockEvent(
            event_id="t1",
            event_type="test.event",
            source_system="test",
            data={"foo": "bar"}
        )
        self.bus.publish(ev)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0].data["foo"], "bar")

    def test_causal_link(self):
        self.bus.register_causal_link({"name": "test_link", "weight": 1.0})
        stats = self.bus.get_stats()
        self.assertEqual(stats["causal_links"], 1)

    def test_feedback_loop(self):
        self.bus.register_feedback_loop({"name": "test_loop", "loop_type": "positive"})
        stats = self.bus.get_stats()
        self.assertEqual(stats["feedback_loops"], 1)


class TestEcosystemSuite(unittest.TestCase):
    """完整套件集成测试"""

    def setUp(self):
        self.data_dir = get_test_data_dir()
        from ecosystem import create_ecosystem_suite
        self.suite = create_ecosystem_suite(self.data_dir)

    def tearDown(self):
        self.suite.close()

    def test_suite_initialization(self):
        self.assertIsNotNone(self.suite.environment)
        self.assertIsNotNone(self.suite.temporal)
        self.assertIsNotNone(self.suite.events)
        self.assertIsNotNone(self.suite.bus)

    def test_tick_runs(self):
        result = self.suite.tick()
        self.assertIn("world_day", result)
        self.assertIn("season", result)
        self.assertIn("entropy", result)
        self.assertIn("events_triggered", result)

    def test_run_multiple_days(self):
        results = self.suite.run(days=10)
        self.assertEqual(len(results), 10)
        first_day = results[0]["world_day"]
        last_day = results[-1]["world_day"]
        self.assertGreater(last_day, first_day)

    def test_get_stats(self):
        stats = self.suite.get_stats()
        self.assertIn("regions", stats)
        self.assertIn("ecosystem_entropy", stats)
        self.assertIn("bus_stats", stats)


class TestDatabaseIsolation(unittest.TestCase):
    """数据库隔离测试"""

    def test_no_modify_existing_db(self):
        from pathlib import Path
        if (HERE / "city_state_data" / "ecosystem" / "state" / "snapshots").exists():
            snapshots = list((HERE / "city_state_data" / "ecosystem" / "state" / "snapshots").glob("gen_*.json"))
            self.assertGreater(len(snapshots), 0, "原有快照应保留")

    def test_new_dbs_in_state_dir(self):
        from ecosystem import create_ecosystem_suite
        data_dir = get_test_data_dir()
        suite = create_ecosystem_suite(data_dir)
        try:
            state_dir = Path(data_dir) / "state"
            self.assertTrue((state_dir / "environment.db").exists())
            self.assertTrue((state_dir / "temporal.db").exists())
            self.assertTrue((state_dir / "events.db").exists())
        finally:
            suite.close()


def main():
    print("=" * 60)
    print("城邦生态扩展包 - 集成测试")
    print("=" * 60)
    print(f"测试数据目录: {get_test_data_dir()}\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestEnvironment, TestTemporal, TestEvents,
                TestInterlocks, TestEcosystemSuite, TestDatabaseIsolation]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("OK 所有测试通过")
    else:
        print(f"FAIL {len(result.failures)} 失败, {len(result.errors)} 错误")
    print("=" * 60)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
