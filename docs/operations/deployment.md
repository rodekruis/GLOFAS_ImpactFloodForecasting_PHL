# Deployment Guide

This guide covers running PhilFlood operationally in production environments.

## Prerequisites

✅ Completed calibration for one or more basins  
✅ Basin configs validated with `philflood validate`  
✅ Access to GloFAS forecast data  
✅ Tested monitoring on historical dates  

## Operational Monitoring

### CLI: Run Monitoring

The primary tool for operational deployment is the `philflood monitor` command.

#### Basic Usage

```bash
# Monitor all basins for today
philflood monitor --basin-dir ops/configs/basins

# Monitor specific basin for specific date
philflood monitor --basin "ops/configs/basins/example_basin.yaml" --date 2025-12-15

# Output as JSON (for integration with early warning systems)
philflood monitor --basin-dir ops/configs/basins --format json --output today.json

# Strict mode (fail if any basin validation fails)
philflood monitor --basin-dir ops/configs/basins --strict
```

#### Output Formats

**CSV Output** (default):
```
basin_name,forecast_date,lead_time_days,impact_prob,impact_threshold,triggered,confidence
example_basin,2026-01-28,3,0.45,500000,False,medium
```

**JSON Output** (for programmatic integration):
```json
{
  "metadata": {
    "run_timestamp": "2026-01-28T12:00:00Z",
    "basins_processed": 1,
    "basins_triggered": 0
  },
  "results": [
    {
      "basin_name": "example_basin",
      "forecast_date": "2026-01-28",
      "lead_time_days": 3,
      "impact_probability": 0.45,
      "impact_threshold": 500000,
      "triggered": false,
      "confidence": "medium"
    }
  ]
}
```

## Scheduled Monitoring

### Windows: Task Scheduler

**Step 1**: Create batch script `run_monitoring.bat`

```batch
@echo off
cd C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL
call venv\Scripts\activate.bat

REM Run monitoring and capture output
philflood monitor ^
    --basin-dir ops\configs\basins ^
    --format json ^
    --output logs\monitoring_%date:~-4,4%%date:~-10,2%%date:~-7,2%.json

REM Log any errors
if errorlevel 1 (
    echo Monitoring failed at %date% %time% >> logs\monitoring_errors.log
    exit /b 1
)

exit /b 0
```

**Step 2**: Schedule task

1. Open Task Scheduler → Create Basic Task
2. Name: "PhilFlood Daily Monitoring"
3. Trigger: Daily at 06:00 AM
4. Action: Start Program → `C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL\run_monitoring.bat`
5. Set user account with sufficient permissions
6. Check "Run whether user is logged in or not"

**Verification**:
```batch
REM Test script manually first
run_monitoring.bat

REM Check output
type logs\monitoring_*.json | find /i "triggered"
```

### Linux/macOS: Cron

**Step 1**: Create script `run_monitoring.sh`

```bash
#!/bin/bash
set -e

REPO_DIR="/opt/philflood"
LOG_DIR="$REPO_DIR/logs"
DATE=$(date +%Y%m%d)

mkdir -p "$LOG_DIR"

# Activate environment
source "$REPO_DIR/venv/bin/activate"

# Run monitoring
philflood monitor \
    --basin-dir "$REPO_DIR/ops/configs/basins" \
    --format json \
    --output "$LOG_DIR/monitoring_$DATE.json" \
    2>&1 | tee -a "$LOG_DIR/monitoring.log"

# Alert if triggered
if grep -q '"triggered": true' "$LOG_DIR/monitoring_$DATE.json"; then
    echo "⚠️ FLOOD TRIGGER ACTIVATED - check logs" >> "$LOG_DIR/alerts.log"
fi

exit 0
```

**Step 2**: Register in crontab

```bash
chmod +x /opt/philflood/run_monitoring.sh

# Edit crontab
crontab -e

# Add line: Run daily at 06:00 UTC
0 6 * * * /opt/philflood/run_monitoring.sh

# Verify cron job
crontab -l
```

## Configuration Validation

Before deployment, validate all basin configurations:

```bash
# Validate all basins
philflood validate --basins ops/configs/basins

# Validate specific basin
philflood validate --basins ops/configs/basins/my_basin.yaml
```

## Performance Tuning

### Memory Usage

Monitoring typically uses 100-150 MB per basin. For batch processing:

```bash
# Process basins sequentially (safe for 4 GB RAM)
philflood monitor --basin-dir ops/configs/basins --sequential

# Process in parallel (faster, higher memory)
philflood monitor --basin-dir ops/configs/basins --parallel --max-workers 4
```

### Processing Speed

- **Single basin**: ~5 seconds (network dependent)
- **10 basins**: ~1 minute
- **50 basins**: ~5 minutes

Speed is primarily limited by GloFAS data download time.

## Production Checklist

Before going live:

- [ ] Calibration completed and validated for all basins
- [ ] All basin configs validated with `philflood validate`
- [ ] GloFAS data access credentials configured
- [ ] Scheduled monitoring tested on historical dates
- [ ] Log rotation configured (prevent disk fill)
- [ ] Alert notifications tested (email, SMS, etc.)
- [ ] Backup strategy documented (config + logs)
- [ ] Team trained on alert interpretation and response
- [ ] Documentation updated for local team

## Docker Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements-ops.txt .
COPY setup.py .
COPY src/ src/
COPY ops/ ops/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-ops.txt
RUN pip install --no-cache-dir -e .

# Create logs directory
RUN mkdir -p /app/logs

# Set entrypoint
ENTRYPOINT ["philflood"]
CMD ["monitor", "--basin-dir", "ops/configs/basins"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  philflood-monitor:
    build: .
    container_name: philflood
    volumes:
      - ./ops/configs:/app/ops/configs:ro
      - ./logs:/app/logs
      - ./data:/app/data:ro  # GloFAS data volume
    environment:
      - TZ=Asia/Manila
      - LOG_LEVEL=INFO
    restart: unless-stopped
    # Run daily at 06:00
    command: sh -c "while true; do sleep 6h && philflood monitor --basin-dir ops/configs/basins --output logs/monitoring_\$$(date +%Y%m%d).json; done"

  # Optional: Add notification service
  # notifier:
  #   image: appropriate/curl
  #   depends_on:
  #     - philflood-monitor
  #   volumes:
  #     - ./logs:/logs:ro
```

### Build and Run

```bash
# Build image
docker build -t philflood:latest .

# Run container
docker-compose up -d

# Check logs
docker-compose logs -f philflood-monitor

# Stop
docker-compose down
```

---

## Cloud Deployment

### Azure Functions (Serverless)

**Architecture:** Timer-triggered Azure Function runs monitoring daily

**Step 1:** Create `function_app.py`:

```python
import azure.functions as func
import logging
from datetime import date
from pathlib import Path

app = func.FunctionApp()

@app.schedule(schedule="0 0 6 * * *", arg_name="timer", 
              run_on_startup=False, use_monitor=False)
def daily_monitoring(timer: func.TimerRequest) -> None:
    """Run daily flood monitoring."""
    logging.info("Starting PhilFlood monitoring")
    
    from philflood.ops.monitoring import run_monitoring
    from philflood.config import load_basin_config
    
    basin_configs = Path("ops/configs/basins").glob("*.yaml")
    results = []
    
    for config_path in basin_configs:
        cfg = load_basin_config(config_path)
        decision = run_monitoring(cfg, date.today())
        results.append(decision.to_dict())
        
        if decision.triggered:
            logging.warning(f"TRIGGER: {decision.basin_id}")
            # Send alert (integrate with Logic Apps, Email, Teams)
    
    # Store results in Azure Blob Storage
    # upload_to_blob(results)
```

**Step 2:** Deploy:

```bash
# Install Azure Functions Core Tools
# https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local

# Initialize
func init PhilFloodFunction --python
cd PhilFloodFunction

# Deploy
func azure functionapp publish <FunctionAppName>
```

### AWS Lambda (Serverless)

**Architecture:** EventBridge (CloudWatch Events) triggers Lambda daily

**Step 1:** Create `lambda_handler.py`:

```python
import json
from datetime import date
from pathlib import Path
import boto3

def lambda_handler(event, context):
    """Lambda function for daily monitoring."""
    from philflood.ops.monitoring import run_monitoring
    from philflood.config import load_basin_config
    
    s3 = boto3.client('s3')
    bucket_name = "philflood-results"
    
    results = []
    basin_configs = Path("/tmp/configs/basins").glob("*.yaml")  # Download from S3
    
    for config_path in basin_configs:
        cfg = load_basin_config(config_path)
        decision = run_monitoring(cfg, date.today())
        results.append(decision.to_dict())
        
        if decision.triggered:
            # Send SNS notification
            sns = boto3.client('sns')
            sns.publish(
                TopicArn='arn:aws:sns:region:account:philflood-alerts',
                Subject=f'Flood Trigger: {decision.basin_id}',
                Message=json.dumps(decision.to_dict(), indent=2)
            )
    
    # Save results to S3
    s3.put_object(
        Bucket=bucket_name,
        Key=f'results/monitoring_{date.today().isoformat()}.json',
        Body=json.dumps(results)
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Processed {len(results)} basins')
    }
```

**Step 2:** Package and deploy:

```bash
# Install dependencies to package
pip install -r requirements-ops.txt -t package/
cp -r src/ package/
cd package && zip -r ../deployment.zip . && cd ..

# Deploy with AWS CLI
aws lambda create-function \
    --function-name PhilFloodMonitoring \
    --runtime python3.10 \
    --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
    --handler lambda_handler.lambda_handler \
    --zip-file fileb://deployment.zip \
    --timeout 300 \
    --memory-size 512

# Add CloudWatch Events trigger (daily at 06:00 UTC)
aws events put-rule --schedule-expression "cron(0 6 * * ? *)" --name DailyPhilFloodRule
aws events put-targets --rule DailyPhilFloodRule --targets "Id"="1","Arn"="arn:aws:lambda:region:account:function:PhilFloodMonitoring"
```

---

## Monitoring & Alerting

### Log Management

**Centralized logging with Azure Application Insights:**

```python
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=<your-key>'
))
```

**Or AWS CloudWatch:**

```python
import watchtower
import logging

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler())
```

### Email Notifications

Add to monitoring script:

```python
import smtplib
from email.mime.text import MIMEText

def send_trigger_alert(decision):
    """Send email when trigger activates."""
    msg = MIMEText(f"""
    Flood Trigger Activated!
    
    Basin: {decision.basin_id}
    Date: {decision.issue_date}
    Probability: {decision.probability_exceed:.1%}
    Expected affected: {decision.expected_people:,.0f}
    """)
    
    msg['Subject'] = f'[ALERT] Flood Trigger: {decision.basin_id}'
    msg['From'] = 'philflood@example.org'
    msg['To'] = 'operations@example.org'
    
    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login(USER, PASSWORD)
        server.send_message(msg)
```

### Health Checks

Create `ops/scripts/health_check.py`:

```python
#!/usr/bin/env python3
"""Health check script for monitoring."""

import sys
from pathlib import Path
from philflood.ops.validation import validate_all_basins

def health_check():
    """Verify system health."""
    issues = []
    
    # Check basin configs
    results = validate_all_basins("ops/configs/basins")
    for basin, basin_issues in results.items():
        if basin_issues:
            issues.extend(basin_issues)
    
    # Check data paths exist
    # Check forecast data freshness
    # etc.
    
    if issues:
        print("❌ Health check FAILED")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    
    print("✓ Health check PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(health_check())
```

---

## Security Considerations

### 1. Secure Configuration

- **Never commit secrets to git**: Use environment variables for credentials
- **Use secret management**: Azure Key Vault, AWS Secrets Manager

```python
# Example with environment variables
import os
GLOFAS_API_KEY = os.getenv("GLOFAS_API_KEY")
```

### 2. Access Control

- Restrict file permissions: `chmod 600 ops/configs/*.yaml`
- Use principle of least privilege for service accounts

### 3. Data Protection

- Encrypt data at rest (especially if storing people affected data)
- Use HTTPS for all external API calls
- Audit logging for all trigger decisions

### 4. Backup Strategy

```bash
# Automated backup script
#!/bin/bash
tar -czf backups/configs_$(date +%Y%m%d).tar.gz ops/configs/
tar -czf backups/logs_$(date +%Y%m%d).tar.gz logs/

# Keep last 30 days
find backups/ -name "*.tar.gz" -mtime +30 -delete
```

---

## Troubleshooting

### Container won't start
```bash
docker-compose logs philflood-monitor
# Check: file permissions, volume mounts, environment variables
```

### Monitoring runs but no output
```bash
# Check logs
tail -f logs/monitoring.log

# Verify basin configs
philflood validate --basin-dir ops/configs/basins

# Test individually
philflood monitor --basins ops/configs/basins/example_basin.yaml
```

### High memory usage
- Reduce number of ensemble members processed
- Process basins sequentially instead of parallel
- Increase Docker container memory limit

---

## Production Checklist

- [ ] All basins calibrated and validated
- [ ] Basin configs stored in version control
- [ ] Data paths configured correctly
- [ ] Logging infrastructure set up
- [ ] Monitoring scheduled (cron/Task Scheduler/cloud)
- [ ] Alerting configured (email/SMS/Teams)
- [ ] Backup strategy implemented
- [ ] Health checks running
- [ ] Documentation updated
- [ ] Team trained on operations

---

**Need help?** See [Getting Started Guide](../getting-started/quickstart.md) or contact the IBF team.
