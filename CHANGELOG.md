# Changelog

All notable changes to the PhilFlood project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2025-12-29

### Added - Operational Infrastructure

#### Package & Installation
- **setup.py**: Proper Python package setup with pip installability
- **requirements.txt**: Core dependencies for base installation
- **requirements-dev.txt**: Development dependencies (Jupyter, testing tools)
- **requirements-ops.txt**: Minimal operational dependencies

#### Command-Line Interface
- **src/philflood/cli.py**: User-friendly CLI with three main commands:
  - `philflood monitor`: Run trigger monitoring
  - `philflood validate`: Validate basin configurations
  - `philflood calibrate`: Run EVT calibration diagnostics
- Supports JSON and CSV output formats
- Emoji-based visual feedback for better UX
- Batch processing of multiple basins
- Flexible date specification (defaults to today)

#### Configuration Validation
- **src/philflood/ops/validation.py**: Pre-deployment configuration validation
  - Checks required fields and data paths
  - Validates EVT parameters are physically reasonable
  - Detects placeholder values still in use
  - Reports actionable validation issues
- CLI integration: `philflood validate`
- Standalone usage: `python -m philflood.ops.validation config.yaml`

#### Logging Infrastructure
- **src/philflood/ops/logging_config.py**: Structured operational logging
  - Console and file handlers
  - Optional JSON format for log aggregation
  - Per-module loggers with context
  - LoggerAdapter for run-specific metadata
  - Automatic third-party logger silencing

#### Testing
- **tests/test_smoke.py**: Installation verification smoke tests
  - Module import validation
  - Configuration loading tests
  - CLI availability checks
  - Logging functionality tests
- **tests/fixtures/generate_test_data.py**: Synthetic test data generation
  - Historical discharge time series
  - Ensemble forecast data (normal and triggered scenarios)

#### Documentation
- **docs/quickstart.md**: Comprehensive 15-minute setup guide
  - Installation instructions (3 options)
  - First run walkthrough
  - Calibration workflow
  - Troubleshooting common issues
- **docs/deployment.md**: Production deployment guide
  - Local scheduling (Windows Task Scheduler, cron)
  - Docker containerization with Dockerfile and docker-compose
  - Cloud deployment (Azure Functions, AWS Lambda)
  - Monitoring, alerting, and security best practices
- **docs/architecture_improvements.md**: Summary of all changes

### Changed

#### Enhanced Operational Script
- **ops/pipeline/run_monitoring_once.py**: Major improvements
  - JSON output support (in addition to CSV)
  - Robust error handling with --strict mode
  - Logging integration for troubleshooting
  - Exit codes for automation compatibility
  - Output to file or stdout
  - Summary statistics after run

#### Updated README
- **README.md**: Restructured for better user experience
  - Quick start section with installation
  - CLI usage examples
  - Clear project structure visualization
  - Links to new documentation
  - Development and testing instructions

### Backward Compatibility

✅ All existing scripts and workflows remain functional
✅ Configuration file format unchanged
✅ Existing operational scripts work as before
✅ New CLI provides alternative, enhanced interface

---

## [0.0.1] - Pre-release

### Initial Features

- Calibration notebooks for EVT analysis
- Basin configuration system (YAML)
- Extreme value analysis modules (POT-GPD)
- CLIMADA hazard integration
- Impact calculation framework
- Basic operational monitoring script
- Country and basin configuration structure

---

## Upgrade Guide

### From Pre-release to 0.1.0

1. **Install as package** (recommended):
   ```bash
   pip install -e .
   ```

2. **Validate your configs**:
   ```bash
   philflood validate --basin-dir ops/configs/basins
   ```

3. **Try the new CLI**:
   ```bash
   philflood monitor --basin-dir ops/configs/basins --output results.json
   ```

4. **Update automation scripts** (optional):
   - Replace script paths with CLI commands
   - Update output parsing for JSON format
   - Add config validation to deployment pipeline

5. **Run smoke tests**:
   ```bash
   python tests/test_smoke.py
   ```

**No breaking changes** - existing scripts continue to work!

---

## Future Roadmap

### Version 0.2.0 (Planned)
- GloFAS API data fetching implementation
- Complete ensemble processing in monitoring
- Batch calibration for multiple basins
- Email/SMS notification system
- Unit tests for core modules

### Version 0.3.0 (Planned)
- Web dashboard for trigger status
- Historical trigger performance tracking
- API documentation (Sphinx)
- Performance optimization

### Version 1.0.0 (Planned)
- Production-ready release
- Multi-country support
- Full test coverage
- Comprehensive documentation
- Performance benchmarks

---

For detailed technical changes, see [docs/architecture_improvements.md](docs/architecture_improvements.md)
