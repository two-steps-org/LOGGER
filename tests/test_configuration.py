"""Tests for twosteps_logger.configuration."""
import pytest
from twosteps_logger.configuration import (
    LoggerConfiguration,
    ElasticLoggerConfig,
    get_logger_configuration,
)


class TestLoggerConfigurationDefaults:
    def test_default_hosts(self):
        cfg = LoggerConfiguration()
        assert cfg.hosts == [{"scheme": "http", "host": "localhost", "port": 9200}]

    def test_default_index_name(self):
        assert LoggerConfiguration().index_name == "python-logs"

    def test_default_index_pattern(self):
        assert LoggerConfiguration().index_pattern == "python-logs-{month}"

    def test_default_service_name(self):
        assert LoggerConfiguration().service_name == "api"

    def test_default_environment(self):
        assert LoggerConfiguration().environment == "development"

    def test_default_flush_interval(self):
        assert LoggerConfiguration().flush_interval == 1.0

    def test_default_bulk_size(self):
        assert LoggerConfiguration().bulk_size == 100

    def test_default_use_ssl_false(self):
        assert LoggerConfiguration().use_ssl is False

    def test_alias_elastic_logger_config(self):
        assert ElasticLoggerConfig is LoggerConfiguration


class TestToConnectionParams:
    def test_basic_params_include_hosts(self):
        cfg = LoggerConfiguration()
        params = cfg.to_connection_params()
        assert "hosts" in params
        assert params["hosts"][0]["scheme"] == "http"

    def test_basic_auth_included_when_credentials_set(self):
        cfg = LoggerConfiguration(username="admin", password="secret")
        params = cfg.to_connection_params()
        assert params["basic_auth"] == ("admin", "secret")

    def test_basic_auth_absent_without_credentials(self):
        cfg = LoggerConfiguration()
        params = cfg.to_connection_params()
        assert "basic_auth" not in params

    def test_api_key_included_when_set(self):
        cfg = LoggerConfiguration(api_key="mykey")
        params = cfg.to_connection_params()
        assert params["api_key"] == "mykey"

    def test_cloud_id_included_when_set(self):
        cfg = LoggerConfiguration(cloud_id="cluster:abc")
        params = cfg.to_connection_params()
        assert params["cloud_id"] == "cluster:abc"

    def test_scheme_added_if_missing(self):
        cfg = LoggerConfiguration(hosts=[{"host": "myhost", "port": 9200}])
        params = cfg.to_connection_params()
        assert params["hosts"][0]["scheme"] == "http"

    def test_scheme_preserved_if_present(self):
        cfg = LoggerConfiguration(hosts=[{"scheme": "https", "host": "myhost", "port": 9200}])
        params = cfg.to_connection_params()
        assert params["hosts"][0]["scheme"] == "https"

    def test_empty_hosts_falls_back_to_localhost(self):
        cfg = LoggerConfiguration(hosts=[])
        params = cfg.to_connection_params()
        assert params["hosts"] == [{"scheme": "http", "host": "localhost", "port": 9200}]


class TestGetLoggerConfiguration:
    def test_returns_logger_configuration_instance(self):
        cfg = get_logger_configuration()
        assert isinstance(cfg, LoggerConfiguration)

    def test_index_prefix_alias(self):
        cfg = get_logger_configuration(index_prefix="myapp")
        assert cfg.index_name == "myapp"

    def test_service_alias(self):
        cfg = get_logger_configuration(service="my-service")
        assert cfg.service_name == "my-service"

    def test_elastic_hosts_alias(self):
        hosts = [{"scheme": "http", "host": "eshost", "port": 9200}]
        cfg = get_logger_configuration(elastic_hosts=hosts)
        assert cfg.hosts == hosts

    def test_auto_generates_index_pattern_from_index_name(self):
        cfg = get_logger_configuration(index_prefix="benchmark")
        assert cfg.index_pattern == "benchmark-{month}"

    def test_explicit_index_pattern_not_overridden(self):
        cfg = get_logger_configuration(index_prefix="benchmark", index_pattern="benchmark-custom")
        assert cfg.index_pattern == "benchmark-custom"

    def test_environment_override(self):
        cfg = get_logger_configuration(environment="production")
        assert cfg.environment == "production"

    def test_flush_interval_override(self):
        cfg = get_logger_configuration(flush_interval=5.0)
        assert cfg.flush_interval == 5.0

    def test_bulk_size_override(self):
        cfg = get_logger_configuration(bulk_size=50)
        assert cfg.bulk_size == 50

    def test_unknown_keys_ignored(self):
        cfg = get_logger_configuration(nonexistent_key="value")
        assert isinstance(cfg, LoggerConfiguration)
