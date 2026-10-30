import glob
import os

from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics

METRICS_PORT = 9200


def on_starting(server):
    """Create the multiprocess metrics directory and remove files from a previous run."""
    multiproc_dir = os.environ['PROMETHEUS_MULTIPROC_DIR']
    os.makedirs(multiproc_dir, exist_ok=True)
    for path in glob.glob(os.path.join(multiproc_dir, '*.db')):
        os.remove(path)


def when_ready(server):
    """Serve the combined metrics of all workers from the master process."""
    GunicornPrometheusMetrics.start_http_server_when_ready(METRICS_PORT)


def child_exit(server, worker):
    """Drop the live gauge files of a worker that exited."""
    GunicornPrometheusMetrics.mark_process_dead_on_child_exit(worker.pid)
