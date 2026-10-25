# Are You Drunk Yet? 🍺

A modern web application for calculating Blood Alcohol Content (BAC) with comprehensive observability and monitoring capabilities.

## 🎯 Overview

This application helps users calculate:
- **Number of drinks** needed to reach a target BAC of 0.1%
- **Time to sober** - how long until BAC returns to zero

Built with a unified Flask architecture featuring OpenTelemetry tracing, Prometheus metrics, and Grafana dashboards for complete observability.

⚠️ **Disclaimer**: This tool is for educational and entertainment purposes only. Do not use it to determine fitness to drive or operate machinery.

## 🏗️ Architecture

### Single-Service Design
- **Unified Flask App** - Serves both web UI and API endpoints
- **Same-Origin Requests** - Eliminates CORS issues
- **Simplified Deployment** - Single container with embedded observability

### Observability Stack
- **OpenTelemetry** - Distributed tracing converted to metrics
- **Prometheus** - Metrics collection and storage
- **Grafana** - Real-time dashboards and visualization

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- 4GB+ RAM recommended

### Launch Application
```bash
# Clone and navigate to the project
cd AreYouDrunkYet

# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### Access Services
- **Web Application**: http://localhost
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

## 📊 Features

### Core Functionality
- **BAC Calculation** - Based on Widmark formula
- **Responsive Design** - Works on desktop and mobile
- **Theme Support** - Multiple color themes and dark/light mode
- **Input Validation** - Comprehensive error handling

### Business Intelligence
- **User Demographics** - Weight and gender distribution analysis
- **Usage Patterns** - Peak usage times and calculation frequency
- **Recommendation Insights** - Drink recommendation patterns

### Performance Monitoring
- **Request Tracing** - End-to-end request lifecycle
- **Response Times** - 95th and 50th percentile latencies
- **Error Tracking** - Real-time error rates and types
- **Resource Usage** - Application performance metrics

## 🔧 Technology Stack

### Backend
- **Flask** - Web framework and API server
- **OpenTelemetry** - Distributed tracing instrumentation
- **Prometheus Client** - Metrics collection
- **Gunicorn** - Production WSGI server

### Frontend
- **Bootstrap 5** - UI framework
- **Vanilla JavaScript** - No framework dependencies
- **CSS Custom Properties** - Theme system

### Infrastructure
- **Docker** - Containerization
- **Prometheus** - Metrics storage
- **Grafana** - Visualization platform

## 📈 Metrics & Monitoring

### Custom Business Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `calculations_total` | Counter | Total calculations by gender and result type |
| `calculation_duration_seconds` | Histogram | Time spent on different operations |
| `drinks_recommended` | Histogram | Distribution of drink recommendations |
| `user_weight_kg` | Histogram | User weight distribution patterns |
| `span_duration_seconds` | Histogram | Trace-like timing for operations |

### Default Flask Metrics
- HTTP request rates and response times
- Response status code distribution
- Request size and response size histograms

### Grafana Dashboards

**Are You Drunk Yet - Application Dashboard** includes:
- **Total Calculations** - Usage statistics
- **User Demographics** - Gender and weight distributions  
- **Request Performance** - Response times and rates
- **Business Insights** - Drink recommendation patterns
- **Error Monitoring** - Real-time error tracking
- **Operation Performance** - Individual function timing

## 🧮 BAC Calculation Details

### Widmark Formula
```
BAC = (Alcohol consumed in grams) / (Body weight in grams × r)
```

Where `r` is the Widmark factor:
- **Male**: 0.68
- **Female**: 0.55  
- **Other**: 0.615 (average)

### Assumptions
- **Standard Drink**: 14 grams of alcohol
- **Target BAC**: 0.1% (legal intoxication threshold in many jurisdictions)
- **Metabolism Rate**: 0.015% BAC per hour

## 🐳 Docker Configuration

### Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 80 | Main Flask application |
| `prometheus` | 9090 | Metrics collection server |
| `grafana` | 3000 | Dashboard and visualization |

### Volumes
- `prometheus-data` - Persistent metrics storage
- `grafana-data` - Dashboard and configuration storage

### Health Checks
- Application health endpoint: `/health`
- Automatic container health monitoring
- Prometheus scraping health validation

## Deployment

The app runs as a Docker Swarm stack that Portainer deploys from this repository. GitHub Actions builds the image and pushes it to the GitHub Container Registry (GHCR).

### Image

- Image: `ghcr.io/julian-heidt/are-you-drunk`
- Tags: `latest` (the tag `docker-compose.yml` uses) and `sha-<short commit sha>`. Each build on `master` pushes both. Builds run on pushes to `master` that change `app/` or the workflow file, so pushes that only touch the README or `docker-compose.yml` do not build an image. If several pushes land while a build runs, GitHub keeps only the newest waiting run and skips the ones in between, so an intermediate commit can have no `sha-` tag. `latest` ends on the newest successful build. A commit that changes neither `app/` nor the workflow file builds nothing, and a failed build leaves `latest` on an older commit.
- Workflow: `.github/workflows/build.yml`. Pull requests build the image without pushing it.
- Platform: `linux/amd64` only, which matches the Swarm nodes. The pushed tag is a plain single-platform manifest (provenance attestations are off).

### Portainer stack settings

The stack keeps its existing name in Portainer. Nginx Proxy Manager reaches the app by the Swarm service name `<stack>_app` on `proxy-net`, so renaming or recreating the stack under another name breaks the proxy upstream.

| Setting | Value |
|---|---|
| Build method | Repository |
| Repository URL | `https://github.com/julian-heidt/are-you-drunk` |
| Repository reference | `refs/heads/master` |
| Compose path | `docker-compose.yml` |
| GitOps updates | On |
| Mechanism | Polling |
| Fetch interval | `5m` |
| Force redeployment | On |
| Re-pull image | On |
| Registry | The `ghcr-julian-heidt` registry entry in Portainer, with access granted to the Swarm environment |

With Force redeployment and Re-pull image on, Portainer resolves `latest` to a digest every interval and Swarm rolls the service only when the digest changed. A Git change to `docker-compose.yml` redeploys the stack on the next poll.

### GitHub side

- Package visibility: private. The repository is public, but GHCR creates the package private by default and it stays private.
- Portainer pulls with the registry entry named `ghcr-julian-heidt`, stored under Registries in Portainer. It is a Custom registry with URL `ghcr.io`, authentication on and username `julian-heidt`. The password is a classic personal access token named `portainer-ghcr-pull` with only the `read:packages` scope. The token lives only in Portainer, never in this repository or in an Actions secret.
- Portainer needs no Git credential for this stack, because the repository is public.
- The token's expiry date is tracked outside this repository. If the token expires or is revoked, new images stop deploying. Depending on whether Portainer's registry login fails first and on which node runs the task, this shows as an Error status on the stack in Portainer, as failed tasks in `docker service ps <stack>_app`, or as no visible change while the service keeps running the old image. To confirm, compare the running digest from `docker service inspect` with the newest `sha-` tag in GHCR. Running tasks keep running on the image they have. If a node is lost or its image is pruned while the token is expired, the replacement task cannot pull the private image, and the app stays down until the token works again.
- No Actions secrets are needed. The workflow pushes with the built-in `GITHUB_TOKEN`.

### Rollout safety

`docker-compose.yml` sets `update_config` with `order: start-first`, `failure_action: rollback` and `monitor: 180s`. Swarm keeps the old task running until the new one is healthy. A task that never passes its healthcheck stays in the starting state and fails on its own; a task that turns healthy and then crashes inside the 180 second monitor window also counts as a failure. Either way Swarm rolls back to the previous image without manual action. The 180 seconds cover the healthcheck's worst case of 15 seconds `start_period` plus three checks of 30 seconds `interval` and 10 seconds `timeout` (135 seconds). That the monitor window catches health failures is an inference from Swarm behaviour, not a sentence in Docker's docs.

### Rollback

Swarm rolls back a failed rollout on its own. When a bad build passes its healthcheck and still has to go, recover in this order.

1. Pin the previous build. Change `image:` in `docker-compose.yml` to `ghcr.io/julian-heidt/are-you-drunk:sha-<good>`, commit to `master`, and let Portainer's polling redeploy it. Pick a commit whose build ran, because a commit skipped by the concurrency queue has no `sha-` tag. Revert the pin once a fixed `latest` exists.
2. Re-run the Build run for the `<good>` commit from step 1 in the Actions tab, meaning the last run whose image worked and not simply the newest green run. The re-run rebuilds that commit and republishes it as `latest` with no token needed. The rebuild can differ from the original image when the build cache or an unpinned dependency changed, so use step 1 when a dependency is the suspected cause.
3. Retag `latest` from a workstation that is logged in to `ghcr.io` with a token that has `write:packages`, which the Portainer pull token does not have:

```bash
docker buildx imagetools create -t ghcr.io/julian-heidt/are-you-drunk:latest ghcr.io/julian-heidt/are-you-drunk:sha-<good>
```

A direct `docker service update` on a manager does not last. While Force redeployment is on, the next poll undoes it.

## 🔍 API Endpoints

### Web Routes
- `GET /` - Main application interface
- `GET /favicon.ico` - Favicon handler
- `GET /health` - Health check endpoint

### API Routes
- `POST /api/calculate` - BAC calculation endpoint

#### Calculate BAC Request
```json
{
  "weight": 70.0,
  "gender": "male",
  "current_drinks": 2
}
```

#### Calculate BAC Response
```json
{
  "drinks_to_reach_target": 3.2,
  "time_to_sober": 4.5
}
```

## 📁 Project Structure

```
AreYouDrunkYet/
├── app/                                    # Main application
│   ├── main.py                            # Flask app with observability
│   ├── calculator.py                      # BAC calculation logic
│   ├── requirements.txt                   # Python dependencies
│   ├── Dockerfile                         # Container configuration
│   ├── static/                           # Frontend assets
│   │   ├── css/style.css                 # Themes and styling
│   │   └── js/script.js                  # Application logic
│   └── templates/                        # HTML templates
│       └── index.html                    # Main application page
├── grafana/                              # Dashboard configuration
│   └── provisioning/
│       ├── datasources/
│       │   └── datasources.yaml         # Prometheus connection
│       └── dashboards/
│           ├── dashboards.yaml           # Dashboard provider
│           └── are-you-drunk-yet-dashboard.json
├── docker-compose.yml                    # Service orchestration
├── prometheus.yml                        # Metrics collection config
└── README.md                            # This file
```

## 🛠️ Development

### Local Development
```bash
# Install dependencies
cd app
pip install -r requirements.txt

# Run Flask development server
python main.py

# Access application at http://localhost:5000
```

### Adding New Metrics
```python
from prometheus_client import Counter, Histogram

# Define custom metric
my_metric = Counter('my_metric_total', 'Description', ['label1', 'label2'])

# Record metric
my_metric.labels(label1='value1', label2='value2').inc()
```

### Viewing Metrics
- **Raw metrics**: http://localhost/metrics
- **Prometheus UI**: http://localhost:9090
- **Grafana dashboards**: http://localhost:3000

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment mode |
| `PORT` | `5000` | Application port |

### Prometheus Configuration
- **Scrape interval**: 5 seconds for app metrics
- **Retention**: Default Prometheus retention policy
- **Targets**: Automatic service discovery via Docker

### Grafana Configuration
- **Auto-provisioning**: Datasources and dashboards
- **Default user**: admin/admin
- **Data source**: Prometheus (automatic)

## 🚨 Troubleshooting

### Common Issues

**Application not accessible**
```bash
# Check container status
docker-compose ps

# View application logs
docker-compose logs app

# Restart services
docker-compose restart
```

**Metrics not appearing**
```bash
# Check Prometheus targets
# Go to http://localhost:9090/targets

# Verify metrics endpoint
curl http://localhost/metrics

# Check Prometheus configuration
docker-compose logs prometheus
```

**Grafana dashboard not loading**
```bash
# Check Grafana logs
docker-compose logs grafana

# Verify dashboard provisioning
docker exec grafana ls -la /etc/grafana/provisioning/dashboards/
```

### Performance Tuning

**High memory usage**
```yaml
# In docker-compose.yml, add memory limits
services:
  app:
    mem_limit: 512m
  prometheus:
    mem_limit: 1g
  grafana:
    mem_limit: 256m
```

**Slow response times**
```yaml
# Scale application workers
services:
  app:
    environment:
      - GUNICORN_WORKERS=8
```

## 📝 License

This project is for educational purposes. Please drink responsibly and never drink and drive.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all metrics are properly instrumented
5. Update documentation
6. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review container logs
3. Verify metric collection in Prometheus
4. Check Grafana dashboard configuration

---

**Remember**: This tool is for entertainment only. Always drink responsibly! 🍻 