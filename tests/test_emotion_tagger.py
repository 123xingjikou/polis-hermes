"""
测试情感标签模块
"""

import pytest
from hypothesis import given, strategies as st

from memory_system.emotion_tagger import EmotionTagger


class TestEmotionTagger:
    """情感标签器测试"""

    def test_tagger_initialization(self):
        """初始化"""
        tagger = EmotionTagger()
        assert tagger is not None

    def test_tag_positive_text(self):
        """正面文本识别"""
        tagger = EmotionTagger()
        result = tagger.tag("今天真开心，学习了新知识，收获满满！")
        assert result is not None
        assert isinstance(result, dict)

    def test_tag_negative_text(self):
        """负面文本识别"""
        tagger = EmotionTagger()
        result = tagger.tag("这个方案失败了，很失望，需要重新来过。")
        assert result is not None
        assert isinstance(result, dict)

    def test_tag_neutral_text(self):
        """中性文本"""
        tagger = EmotionTagger()
        result = tagger.tag("系统当前状态正常，等待下一个任务。")
        assert result is not None
        assert isinstance(result, dict)

    def test_tag_empty_text(self):
        """空文本处理"""
        tagger = EmotionTagger()
        result = tagger.tag("")
        assert result is not None

    def test_batch_tagging(self):
        """批量标注"""
        tagger = EmotionTagger()
        texts = [
            "今天天气真好",
            "任务失败了很遗憾",
            "继续努力学习",
        ]
        results = tagger.batch_tag(texts)
        assert len(results) == len(texts)
        for r in results:
            assert isinstance(r, dict)

    def test_emotion_categories(self):
        """情感分类完整性"""
        tagger = EmotionTagger()
        result = tagger.tag("测试文本")

        # 结果应该包含基本情感维度
        assert any(k in result for k in ['joy', 'sadness', 'anger', 'fear',
                                          'surprise', 'disgust', 'trust',
                                          'anticipation'])


class TestHypothesisGenerated:
    """使用 Hypothesis 进行属性测试"""

    @given(text=st.text(min_size=0, max_size=500))
    def test_any_text_returns_dict(self, text):
        """任意文本都返回 dict（不会崩溃）"""
        tagger = EmotionTagger()
        result = tagger.tag(text)
        assert isinstance(result, dict)

    @given(texts=st.lists(st.text(min_size=1, max_size=200), min_size=0, max_size=20))
    def test_batch_any_texts(self, texts):
        """批量处理任意文本列表"""
        tagger = EmotionTagger()
        results = tagger.batch_tag(texts)
        assert len(results) == len(texts)
