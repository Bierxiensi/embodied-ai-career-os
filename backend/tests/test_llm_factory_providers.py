"""LLM Provider 工厂测试：小米 MiMo（xiaomi）分支与 fallback 契约。

覆盖三件事：
  1. xiaomi 的 cache key 会把模型名纳入区分
  2. 缺 key / 缺模型名时，get_llm() 明确降级为 MockClient（而不是静默给出错配置）
  3. 配齐 key + model 后，构建出 OpenAICompatibleClient，且 base_url 指向小米专属端点

⚠️ 本文件为**纯单元测试**，不触网（OpenAICompatibleClient 是懒加载，构造时不建连接）。
"""

import pytest

from app.core.config import settings
from app.llm.factory import _cache_key, _llm_cache, get_llm
from app.llm.providers import MockClient, OpenAICompatibleClient

XIAOMI_DEFAULT_BASE = "https://token-plan-cn.xiaomimimo.com/v1"


@pytest.fixture(autouse=True)
def _clean_llm_cache():
    """每个用例前后清空单例缓存，避免用例间互相污染（也验证"不缓存 fallback"）。"""
    _llm_cache.clear()
    yield
    _llm_cache.clear()


@pytest.fixture
def xiaomi_settings(monkeypatch):
    """把全局 settings 切成 xiaomi，並把 key/model 置空，由具体用例按需覆盖。"""
    monkeypatch.setattr(settings, "llm_provider", "xiaomi")
    monkeypatch.setattr(settings, "xiaomi_api_key", "")
    monkeypatch.setattr(settings, "xiaomi_model", "")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "xiaomi_base_url", XIAOMI_DEFAULT_BASE)
    return settings


def test_xiaomi_cache_key_includes_model(xiaomi_settings, monkeypatch):
    """cache key 必须带模型名，否则换模型会命中旧缓存。"""
    monkeypatch.setattr(settings, "xiaomi_model", "model-a")
    assert _cache_key("xiaomi") == "xiaomi:model-a"

    # 回退到通用 LLM_MODEL 时也要能区分
    monkeypatch.setattr(settings, "xiaomi_model", "")
    monkeypatch.setattr(settings, "llm_model", "model-b")
    assert _cache_key("xiaomi") == "xiaomi:model-b"


def test_xiaomi_without_key_falls_back_to_mock(xiaomi_settings):
    """未配置 key → 明确降级为 MockClient，并给出 warning（不静默）。"""
    with pytest.warns(UserWarning, match="xiaomi"):
        llm = get_llm()

    assert isinstance(llm, MockClient)
    assert llm.model_name == "mock-v1"


def test_xiaomi_without_model_falls_back_to_mock(xiaomi_settings, monkeypatch):
    """有 key 但缺模型名 → 同样降级为 Mock（不允许猜一个默认模型名）。"""
    monkeypatch.setattr(settings, "xiaomi_api_key", "sk-dummy")

    with pytest.warns(UserWarning, match="xiaomi"):
        llm = get_llm()

    assert isinstance(llm, MockClient)


def test_xiaomi_fallback_is_not_cached(xiaomi_settings, monkeypatch):
    """fallback 产出的 Mock 不得进缓存——否则配置修好后无法切回真实 Provider。"""
    with pytest.warns(UserWarning):
        get_llm()
    assert _llm_cache == {}

    # 补上配置后，应能拿到真实客户端
    monkeypatch.setattr(settings, "xiaomi_api_key", "sk-dummy")
    monkeypatch.setattr(settings, "xiaomi_model", "model-a")
    llm = get_llm()
    assert isinstance(llm, OpenAICompatibleClient)
    assert llm.model_name == "model-a"


def test_xiaomi_builds_client_with_dedicated_base_url(xiaomi_settings, monkeypatch):
    """配齐后指向小米专属 Base URL（而不是 OpenAI 官方地址）。"""
    monkeypatch.setattr(settings, "xiaomi_api_key", "sk-dummy")
    monkeypatch.setattr(settings, "xiaomi_model", "model-a")

    llm = get_llm()

    assert isinstance(llm, OpenAICompatibleClient)
    assert not isinstance(llm, MockClient)
    # 通过实际生成的 openai 客户端反查 base_url（懒加载，此处会真正构造 OpenAI 对象但不发请求）
    llm._ensure_client()
    assert str(llm._client.base_url).rstrip("/") == XIAOMI_DEFAULT_BASE
    assert llm.model_name == "model-a"


def test_xiaomi_uses_generic_llm_model_as_fallback(xiaomi_settings, monkeypatch):
    """XIAOMI_MODEL 留空时应回退读 LLM_MODEL，而不是直接报错。"""
    monkeypatch.setattr(settings, "xiaomi_api_key", "sk-dummy")
    monkeypatch.setattr(settings, "llm_model", "model-from-generic")

    llm = get_llm()

    assert isinstance(llm, OpenAICompatibleClient)
    assert llm.model_name == "model-from-generic"


def test_mock_provider_still_works(monkeypatch):
    """回归：显式 mock 仍是正常路径（不得被 xiaomi 分支影响）。"""
    monkeypatch.setattr(settings, "llm_provider", "mock")
    llm = get_llm()
    assert isinstance(llm, MockClient)
