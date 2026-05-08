import logging
import os
from typing import Any, Dict


class OTelHandler(logging.Handler):
    """
    OpenTelemetry logging handler that exports logs to an OTLP collector.
    Defaults:
      - protocol: grpc
      - endpoint: http://localhost:4317 (grpc) / http://localhost:4318 (http)
    """

    def __init__(
        self,
        service_name: str = "api",
        environment: str = "development",
        index_name: str = "python-logs",
        level: int = logging.INFO,
        **kwargs: Any,
    ):
        super().__init__(level)
        self._handler = self._build_handler(
            service_name=service_name,
            environment=environment,
            index_name=index_name,
            **kwargs,
        )

    def _build_handler(
        self,
        service_name: str,
        environment: str,
        index_name: str,
        **kwargs: Any,
    ) -> logging.Handler:
        try:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter as GRPCOTLPLogExporter,
            )
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter as HTTPOTLPLogExporter,
            )
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
            from opentelemetry.sdk.resources import Resource
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "OpenTelemetry dependencies are required for LOGGER_TRANSPORT=otel. "
                "Install: opentelemetry-sdk, "
                "opentelemetry-exporter-otlp-proto-grpc, "
                "opentelemetry-exporter-otlp-proto-http"
            ) from exc

        protocol = str(
            kwargs.get("otlp_protocol")
            or os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL")
            or "grpc"
        ).lower()
        headers = self._parse_headers(
            kwargs.get("otlp_headers") or os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
        )
        if protocol in {"http", "http/protobuf"}:
            endpoint = kwargs.get("otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4318"
            endpoint = self._normalize_http_logs_endpoint(endpoint)
            exporter = HTTPOTLPLogExporter(endpoint=endpoint, headers=headers or None)
        else:
            endpoint = kwargs.get("otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4317"
            insecure = str(kwargs.get("otlp_insecure") or os.getenv("OTEL_EXPORTER_OTLP_INSECURE") or "true").lower()
            exporter = GRPCOTLPLogExporter(
                endpoint=endpoint,
                insecure=insecure in {"1", "true", "yes"},
                headers=headers or None,
            )

        resource_attributes: Dict[str, str] = {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "deployment.environment": environment,
            "logger.index_prefix": index_name,
        }
        resource_attributes.update(
            self._parse_resource_attributes(os.getenv("OTEL_RESOURCE_ATTRIBUTES"))
        )
        resource = Resource.create(resource_attributes)
        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        handler = LoggingHandler(level=self.level, logger_provider=provider)
        self._provider = provider
        return handler

    @staticmethod
    def _parse_headers(raw: Any) -> Dict[str, str]:
        """
        Parse OTEL header formats:
          - "k=v"
          - "k=v,k2=v2"
        """
        if not raw:
            return {}
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
        out: Dict[str, str] = {}
        for part in str(raw).split(","):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k:
                out[k] = v
        return out

    @staticmethod
    def _parse_resource_attributes(raw: Any) -> Dict[str, str]:
        """
        Parse OTEL_RESOURCE_ATTRIBUTES format:
          "key=value,key2=value2"
        """
        return OTelHandler._parse_headers(raw)

    @staticmethod
    def _normalize_http_logs_endpoint(endpoint: str) -> str:
        """
        HTTP OTLP log exporter expects /v1/logs path.
        If user provides only host:port, append /v1/logs.
        """
        ep = (endpoint or "").rstrip("/")
        if ep.endswith("/v1/logs"):
            return ep
        return f"{ep}/v1/logs"

    def emit(self, record: logging.LogRecord) -> None:
        self._handler.emit(record)

    def close(self) -> None:
        try:
            if hasattr(self, "_provider"):
                self._provider.force_flush()
                self._provider.shutdown()
        except Exception:
            pass
        super().close()
