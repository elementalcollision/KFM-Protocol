import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME as OTEL_SERVICE_NAME # Use OTEL constant

# Use OTLP Http Exporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Import settings from the correct location for this service
from api_gateway_service.core.config import settings

logger = logging.getLogger(__name__)

def configure_tracing():
    """Configures OpenTelemetry tracing for the service."""

    if not settings.OTEL_TRACE_ENABLED:
        logger.info("OpenTelemetry tracing is disabled.")
        return None

    try:
        # Create a Resource with service attributes
        resource = Resource.create({
            OTEL_SERVICE_NAME: settings.SERVICE_NAME, # Use OTEL_SERVICE_NAME
            "service.version": settings.PROJECT_VERSION, # Use settings.PROJECT_VERSION if available
            "deployment.environment": settings.APP_ENV, # Use settings.APP_ENV
        })

        # Create a TracerProvider
        tracer_provider = TracerProvider(resource=resource)

        # Configure the OTLP/HTTP Exporter
        # Endpoint should be configurable via settings or environment variable
        otlp_endpoint = settings.OTLP_ENDPOINT or "http://jaeger-collector.kfm-observability.svc.cluster.local:4318/v1/traces"
        logger.info(f"Configuring OTLP exporter to endpoint: {otlp_endpoint}")
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            # Optional: Add headers for authentication if needed
            # headers={"Authorization": f"Bearer {settings.OTLP_AUTH_TOKEN}"} 
        )

        # Use BatchSpanProcessor for performance
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Optional: Add ConsoleSpanExporter for debugging locally
        # console_exporter = ConsoleSpanExporter()
        # tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

        # Set the global TracerProvider
        trace.set_tracer_provider(tracer_provider)
        
        logger.info(f"OpenTelemetry tracing configured for service: {settings.SERVICE_NAME} sending to {otlp_endpoint}")
        return tracer_provider

    except Exception as e:
        logger.error(f"Failed to configure OpenTelemetry tracing: {e}", exc_info=True)
        return None

# Helper to get a tracer instance easily
def get_tracer(name: str):
    return trace.get_tracer(name) 