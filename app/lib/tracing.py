import pydantic_settings as settings
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc import trace_exporter
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.lib import config

log: structlog.stdlib.BoundLogger = structlog.get_logger()

_setup_done = False


class TracingConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="TRACING_")

    endpoint: str = "localhost:4317"
    enabled: bool = False


def setup_tracing(service_name: str, cfg: TracingConfig) -> None:
    global _setup_done
    if not cfg.enabled:
        log.debug("tracing disabled", service_name=service_name)
        return
    if _setup_done:
        return

    provider = sdk_trace.TracerProvider(
        resource=Resource.create({"service.name": service_name}),
    )
    provider.add_span_processor(
        BatchSpanProcessor(trace_exporter.OTLPSpanExporter(endpoint=cfg.endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)

    PsycopgInstrumentor().instrument()
    _setup_done = True

    log.debug(
        "tracing setup complete",
        service_name=service_name,
        endpoint=cfg.endpoint,
    )


def flush_tracing() -> None:
    provider = trace.get_tracer_provider()
    force_flush = getattr(provider, "force_flush", None)
    if callable(force_flush):
        force_flush()
