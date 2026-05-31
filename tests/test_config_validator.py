"""
配置验证器单元测试
"""
import os
import pytest
from utils.config_validator import ConfigValidator


class TestConfigValidator:
    """测试配置验证器"""

    def test_validate_missing_required_env(self, monkeypatch):
        """缺少 TENCENT_API_KEY 时应返回失败"""
        monkeypatch.delenv("TENCENT_API_KEY", raising=False)
        valid, issues = ConfigValidator.validate_envs(exit_on_error=False)
        assert valid is False
        assert len(issues) > 0

    def test_validate_with_key_present(self, monkeypatch):
        """有 TENCENT_API_KEY 时应通过"""
        monkeypatch.setenv("TENCENT_API_KEY", "sk-test-key-12345")
        valid, issues = ConfigValidator.validate_envs(exit_on_error=False)
        assert valid is True
        assert len(issues) == 0

    def test_validate_invalid_key_format(self, monkeypatch):
        """格式不正确的 API Key 应提示警告"""
        monkeypatch.setenv("TENCENT_API_KEY", "not-sk-prefix")
        valid, issues = ConfigValidator.validate_envs(exit_on_error=False)
        # 不会失败，但会有提示
        assert valid is True

    def test_validate_with_optional_envs(self, monkeypatch):
        """可选环境变量配置完整的情况"""
        monkeypatch.setenv("TENCENT_API_KEY", "sk-test-key")
        monkeypatch.setenv("TENCENT_API_BASE", "https://custom.api.example.com/v1")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        valid, issues = ConfigValidator.validate_envs(exit_on_error=False)
        assert valid is True

    def test_print_config_summary_no_error(self, monkeypatch):
        """print_config_summary 不应抛出异常"""
        monkeypatch.setenv("TENCENT_API_KEY", "sk-test-key")
        # This should not raise
        ConfigValidator.print_config_summary()


class TestValidateConfigFunction:
    """测试便捷函数"""

    def test_validate_config_success(self, monkeypatch):
        monkeypatch.setenv("TENCENT_API_KEY", "sk-test-key")
        from utils.config_validator import validate_config
        result = validate_config(exit_on_error=False)
        assert result is True

    def test_validate_config_failure(self, monkeypatch):
        monkeypatch.delenv("TENCENT_API_KEY", raising=False)
        from utils.config_validator import validate_config
        result = validate_config(exit_on_error=False)
        assert result is False
