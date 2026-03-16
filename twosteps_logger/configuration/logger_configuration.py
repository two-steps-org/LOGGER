from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LoggerConfiguration:
    hosts: List[Dict[str, Any]] = field(
        default_factory=lambda: [{"scheme": "http", "host": "localhost", "port": 9200}]
    )
    index_name: str = "benchmark"
    index_pattern: str = "benchmark-{month}"
    use_ssl: bool = False
    verify_certs: bool = True
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    cloud_id: Optional[str] = None
    service_name: str = "benchmark"
    project_name: Optional[str] = None
    environment: Optional[str] = "development"
    flush_interval: float = 1.0
    bulk_size: int = 100

    def to_connection_params(self) -> Dict[str, Any]:
        hosts: List[Dict[str, Any]] = []
        for host in self.hosts or []:
            if isinstance(host, dict) and "scheme" not in host:
                hosts.append({**host, "scheme": "https" if self.use_ssl else "http"})
            else:
                hosts.append(host)
        params: Dict[str, Any] = {
            "hosts": hosts or [{"scheme": "http", "host": "localhost", "port": 9200}],
            "verify_certs": self.verify_certs,
        }
        if self.username and self.password:
            params["basic_auth"] = (self.username, self.password)
        if self.api_key:
            params["api_key"] = self.api_key
        if self.cloud_id:
            params["cloud_id"] = self.cloud_id
        return params


ElasticLoggerConfig = LoggerConfiguration

