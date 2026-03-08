import pydantic
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc import trace_exporter
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class TracingConfig(pydantic.BaseModel):
    endpoint: str
    enabled: bool = False


def setup_tracing(service_name: str, cfg: TracingConfig) -> None:
    if not cfg.enabled:
        log.debug("tracing disabled", service_name=service_name)
        return

    provider = sdk_trace.TracerProvider(
        resource=Resource.create({"service.name": service_name}),
    )
    provider.add_span_processor(
        BatchSpanProcessor(trace_exporter.OTLPSpanExporter(endpoint=cfg.endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)

    PsycopgInstrumentor().instrument()

    log.debug(
        "tracing setup complete",
        service_name=service_name,
        endpoint=cfg.endpoint,
    )
