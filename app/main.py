import logging
import time
import os
from flask import Flask, render_template, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from pythonjsonlogger import jsonlogger
import calculator

# --- Structured Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# --- Flask Application Initialization ---
app = Flask(__name__)

# --- OpenTelemetry Setup ---
tracer_provider = TracerProvider(
    resource=Resource.create({SERVICE_NAME: os.environ.get('OTEL_SERVICE_NAME', 'are-you-drunk')})
)

# Export spans over OTLP/HTTP only when a collector endpoint is configured
if os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'):
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    logger.info("OTLP trace export enabled")

trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# Instrument Flask automatically
FlaskInstrumentor().instrument_app(app)

# --- Prometheus Metrics Setup ---
# Under gunicorn, PROMETHEUS_MULTIPROC_DIR is set and gunicorn.conf.py serves the
# metrics of all workers on port 9200. Without it (python main.py), the app serves /metrics itself.
if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
    prometheus_metrics = GunicornPrometheusMetrics(app)
    logger.info("Prometheus metrics served on port 9200 by the gunicorn master")
else:
    prometheus_metrics = PrometheusMetrics(app, path='/metrics')
    logger.info("Prometheus metrics endpoint available at /metrics")

# Custom business metrics
calculation_counter = Counter(
    'calculations_total', 
    'Total calculations performed', 
    ['gender', 'result_type']
)

calculation_duration = Histogram(
    'calculation_duration_seconds', 
    'Time spent on calculations', 
    ['operation']
)

drinks_recommended = Histogram(
    'drinks_recommended', 
    'Number of drinks recommended', 
    buckets=[0, 1, 2, 3, 5, 10, 15, 20]
)

user_weight_gauge = Histogram(
    'user_weight_kg', 
    'User weights in kg', 
    buckets=[40, 50, 60, 70, 80, 90, 100, 120, 150]
)

span_duration_metric = Histogram(
    'span_duration_seconds',
    'Duration of individual operations',
    ['span_name', 'status'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

logger.info("Application initialized with observability")

# --- Frontend Routes ---
@app.route('/')
def index():
    """Serve the main web application"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests"""
    return '', 204

# --- Health Check ---
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "are-you-drunk-yet"}), 200

@app.route('/test')
def test():
    """Simple test endpoint to generate metrics"""
    return jsonify({"message": "Test endpoint", "timestamp": time.time()}), 200

# --- API Endpoints ---
@app.route('/api/calculate', methods=['POST'])
def calculate_api():
    """Calculate BAC and provide recommendations"""
    request_start_time = time.time()
    
    with tracer.start_as_current_span("calculate_request") as span:
        try:
            # Parse request data
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
                
            weight = float(data.get('weight', 0))
            gender = data.get('gender', '')
            current_drinks = int(data.get('current_drinks', 0))
            
            # Validate input
            if weight <= 0:
                return jsonify({"error": "Weight must be greater than 0"}), 400
            if gender not in ['male', 'female', 'other']:
                return jsonify({"error": "Invalid gender"}), 400
            if current_drinks < 0:
                return jsonify({"error": "Current drinks cannot be negative"}), 400
            
            # Add span attributes
            span.set_attribute("user.weight", weight)
            span.set_attribute("user.gender", gender)
            span.set_attribute("user.current_drinks", current_drinks)
            
            logger.info("Received calculation request", extra={
                'weight': weight, 
                'gender': gender, 
                'current_drinks': current_drinks
            })
            
            # Business logic with timing and tracing
            with tracer.start_as_current_span("calculate_drinks_to_target") as calc_span:
                calc_start = time.time()
                drinks_to_target = calculator.calculate_drinks_to_target_bac(weight, gender, current_drinks)
                calc_duration = time.time() - calc_start
                calculation_duration.labels(operation='drinks_to_target').observe(calc_duration)
                span_duration_metric.labels(span_name='calculate_drinks_to_target', status='success').observe(calc_duration)
                calc_span.set_attribute("result.drinks_to_target", drinks_to_target)
            
            with tracer.start_as_current_span("calculate_time_to_sober") as sober_span:
                calc_start = time.time()
                time_to_sober = calculator.calculate_time_to_sober(current_drinks, weight, gender)
                calc_duration = time.time() - calc_start
                calculation_duration.labels(operation='time_to_sober').observe(calc_duration)
                span_duration_metric.labels(span_name='calculate_time_to_sober', status='success').observe(calc_duration)
                sober_span.set_attribute("result.time_to_sober", time_to_sober)
            
            # Record business metrics
            calculation_counter.labels(gender=gender, result_type='success').inc()
            drinks_recommended.observe(drinks_to_target)
            user_weight_gauge.observe(weight)
            
            # Add results to main span
            span.set_attribute("result.drinks_to_target", drinks_to_target)
            span.set_attribute("result.time_to_sober", time_to_sober)
            
            response_data = {
                'drinks_to_reach_target': drinks_to_target,
                'time_to_sober': time_to_sober
            }
            
            logger.info("Calculation successful", extra={'result': response_data})
            return jsonify(response_data)
            
        except ValueError as e:
            error_msg = f"Invalid input data: {str(e)}"
            logger.error(error_msg)
            calculation_counter.labels(gender=gender if 'gender' in locals() else 'unknown', result_type='validation_error').inc()
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            return jsonify({"error": error_msg}), 400
            
        except Exception as e:
            error_msg = "An internal server error occurred"
            logger.error("Calculation error", exc_info=True)
            calculation_counter.labels(gender=gender if 'gender' in locals() else 'unknown', result_type='server_error').inc()
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            return jsonify({"error": error_msg}), 500
        
        finally:
            # Record total request duration
            total_duration = time.time() - request_start_time
            calculation_duration.labels(operation='total_request').observe(total_duration)
            span_duration_metric.labels(span_name='total_request', status='completed').observe(total_duration)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Log all registered routes for debugging
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
    
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 