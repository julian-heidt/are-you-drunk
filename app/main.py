import logging
import time
import os
from flask import Flask, render_template, request, jsonify
from opentelemetry import trace, metrics
from pythonjsonlogger import jsonlogger
import calculator
import telemetry

# --- Structured Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(otelTraceID)s %(otelSpanID)s %(otelServiceName)s'
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# --- Flask Application Initialization ---
app = Flask(__name__)

# --- OpenTelemetry Setup ---
telemetry.setup(app)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Genders the API accepts, also the only values used as metric labels
ALLOWED_GENDERS = ['male', 'female', 'other']

# Custom business metrics
calculation_counter = meter.create_counter(
    'calculations',
    description='Total calculations performed'
)

calculation_duration = meter.create_histogram(
    'calculation.duration',
    unit='s',
    description='Time spent on calculations'
)

drinks_recommended = meter.create_histogram(
    'drinks.recommended',
    description='Number of drinks recommended',
    explicit_bucket_boundaries_advisory=[0, 1, 2, 3, 5, 10, 15, 20]
)

user_weight_gauge = meter.create_histogram(
    'user.weight',
    unit='kg',
    description='User weights in kg',
    explicit_bucket_boundaries_advisory=[40, 50, 60, 70, 80, 90, 100, 120, 150]
)

span_duration_metric = meter.create_histogram(
    'span.duration',
    unit='s',
    description='Duration of individual operations',
    explicit_bucket_boundaries_advisory=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
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
            if gender not in ALLOWED_GENDERS:
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
                calculation_duration.record(calc_duration, {'operation': 'drinks_to_target'})
                span_duration_metric.record(calc_duration, {'span_name': 'calculate_drinks_to_target', 'status': 'success'})
                calc_span.set_attribute("result.drinks_to_target", drinks_to_target)
            
            with tracer.start_as_current_span("calculate_time_to_sober") as sober_span:
                calc_start = time.time()
                time_to_sober = calculator.calculate_time_to_sober(current_drinks, weight, gender)
                calc_duration = time.time() - calc_start
                calculation_duration.record(calc_duration, {'operation': 'time_to_sober'})
                span_duration_metric.record(calc_duration, {'span_name': 'calculate_time_to_sober', 'status': 'success'})
                sober_span.set_attribute("result.time_to_sober", time_to_sober)
            
            # Record business metrics
            calculation_counter.add(1, {'gender': gender, 'result_type': 'success'})
            drinks_recommended.record(drinks_to_target)
            user_weight_gauge.record(weight)
            
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
            calculation_counter.add(1, {'gender': (gender if gender in ALLOWED_GENDERS else 'invalid') if 'gender' in locals() else 'unknown', 'result_type': 'validation_error'})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            return jsonify({"error": error_msg}), 400
            
        except Exception as e:
            error_msg = "An internal server error occurred"
            logger.error("Calculation error", exc_info=True)
            calculation_counter.add(1, {'gender': (gender if gender in ALLOWED_GENDERS else 'invalid') if 'gender' in locals() else 'unknown', 'result_type': 'server_error'})
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            return jsonify({"error": error_msg}), 500
        
        finally:
            # Record total request duration
            total_duration = time.time() - request_start_time
            calculation_duration.record(total_duration, {'operation': 'total_request'})
            span_duration_metric.record(total_duration, {'span_name': 'total_request', 'status': 'completed'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Log all registered routes for debugging
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
    
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 