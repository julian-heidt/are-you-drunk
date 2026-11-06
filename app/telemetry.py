import os
import socket

# The Flask instrumentation reads these when it is imported, so they need defaults first.
os.environ.setdefault('OTEL_SEMCONV_STABILITY_OPT_IN', 'http')
os.environ.setdefault('OTEL_PYTHON_LOG_CORRELATION', 'true')

from opentelemetry import metrics, trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor


def setup(app):
    """Create the tracer and meter providers for this process and instrument Flask and logging.

    Call once per gunicorn worker, so each worker gets its own service.instance.id.
    """
    resource = Resource.create({
        'service.name': os.environ.get('OTEL_SERVICE_NAME', 'are-you-drunk'),
        'service.version': os.environ.get('GIT_SHA', 'dev')[:12],
        'service.instance.id': f'{socket.gethostname()}-{os.getpid()}',
    })

    if os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'):
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        span_processor = BatchSpanProcessor(OTLPSpanExporter())
        metric_exporter = OTLPMetricExporter()
    else:
        span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
        metric_exporter = ConsoleMetricExporter()

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(metric_exporter)],
    )
    metrics.set_meter_provider(meter_provider)

    LoggingInstrumentor().instrument(set_logging_format=False, inject_trace_context=True)
    FlaskInstrumentor().instrument_app(app)
