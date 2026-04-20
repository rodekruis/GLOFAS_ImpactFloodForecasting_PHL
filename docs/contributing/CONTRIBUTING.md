# Contributing Guide

Welcome! We appreciate your interest in improving PhilFlood. This guide covers development setup, code standards, and the PR process.

## Development Setup

### Prerequisites

- Python **3.10+** (recommended **3.11**)
- Git
- conda or mamba

### Set Up Development Environment

```bash
# Clone repository
git clone https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL.git
cd GLOFAS_ImpactFloodForecasting_PHL

# Create conda environment
mamba create -n philflood-dev -c conda-forge python=3.11 -y
mamba activate philflood-dev

# Install dependencies
mamba install -c conda-forge -y \
  numpy pandas xarray netcdf4 cftime \
  geopandas rasterio shapely pyproj pyogrio \
  scipy pyyaml python-dateutil jupyter

# Install PhilFlood in editable mode with dev extras
pip install -e ".[dev]"

# Verify installation
python -c "import philflood; print(philflood.__version__)"
```

## Code Style & Standards

### Python Style Guide

We follow **PEP 8** with these specific practices:

- **Line length**: 88 characters (enforced by Black)
- **Imports**: Organized by isort (stdlib, third-party, local)
- **Docstrings**: Google-style for public functions

**Example function**:
```python
def fit_gpd_to_pot(
    discharge: pd.Series,
    threshold_m3s: float,
    r: str = "5D",
) -> POTResult:
    """Fit a GPD to peaks over threshold from a discharge time series.

    Args:
        discharge: Hourly or daily discharge (m³/s).
        threshold_m3s: POT threshold value (m³/s).
        r: Minimum separation between independent peaks (pandas offset).

    Returns:
        POTResult with fitted GPD parameters (xi, sigma, lam) and
        the extracted exceedances.

    Raises:
        ValueError: If fewer than 10 exceedances are found.
    """
    # Implementation...
```

### Code Quality Tools

**Format code automatically**:
```bash
# Format with Black
black src/ tests/ calibration/scripts/

# Sort imports with isort
isort src/ tests/ calibration/scripts/
```

**Lint and type check**:
```bash
# Check with Pylint
pylint src/philflood

# Type check with mypy
mypy src/philflood --ignore-missing-imports
```

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/issue-description
```

### 2. Make Atomic Commits

Keep commits focused and logically distinct:

```bash
# ✅ Good
git commit -m "Add POT threshold validation in evt_pot.py"
git commit -m "Update docstring for fit_gpd_to_pot()"

# ❌ Avoid
git commit -m "Fix calibration, update docs, refactor utils"
```

**Commit message format**:
```
[TYPE] Brief description (max 50 chars)

Optional detailed explanation if needed.
Reference issue: #123
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`

### 3. Add Tests for Your Changes

See [TESTING.md](TESTING.md) for details. Minimum requirements:

```python
# tests/test_your_feature.py
import pytest
from philflood.your_module import your_function

def test_your_function_basic():
    """Test basic functionality."""
    result = your_function(input_data)
    assert result is not None
    
def test_your_function_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        your_function(invalid_input)
```

Run tests locally:
```bash
pytest tests/test_your_feature.py -v
```

### 4. Update Documentation

If you add new modules, functions, or change behavior:

- [ ] Add/update docstrings in code (Google-style)
- [ ] Update relevant markdown docs in `docs/`
- [ ] Update README.md if architecture changes
- [ ] Update CHANGELOG.md with your change

Example markdown update:

```markdown
## New Feature: Custom Threshold Selection

Added `select_threshold_interactively()` in `src/philflood/calibration/`.

**Usage**:
\`\`\`python
from philflood.calibration import select_threshold_interactively
threshold = select_threshold_interactively(discharge_data)
\`\`\`

See [Notebook 1 Calibration Guide](../user-guides/notebook01-calibration-guide.md) for details.
```

## Pull Request Process

### Before Creating PR

1. **Run full test suite locally**:
   ```bash
   pytest tests/ -v
   ```

2. **Format code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

3. **Verify no lint errors**:
   ```bash
   pylint src/philflood --fail-under=8.0
   ```

4. **Update CHANGELOG.md** (unreleased section)

### Creating the PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub** with:
   - **Title**: Clear, descriptive (e.g., "Add custom threshold selection UI")
   - **Description**: Include:
     - What problem does this solve?
     - How does it work?
     - Any breaking changes?
     - References to related issues (#123)
   - **Checklist** (copy-paste template below)

**PR Template**:
```markdown
## Description
Brief description of changes.

## Problem
What issue does this solve? (link to issue: #123)

## Solution
How does this PR address the problem?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Breaking change

## Checklist
- [ ] Code follows PEP 8 style guidelines
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] All tests pass locally (`pytest tests/`)
- [ ] No new warnings from linter
```

### Review Process

- **Maintainers will review** within 3-5 business days
- **Request changes** if needed (don't take it personally!)
- **Respond to feedback** promptly
- Once approved, maintainer will merge

## Types of Contributions

### 1. Bug Fixes
- Report issue first (check if already reported)
- Create PR with:
  - Minimal code change
  - Test demonstrating the bug
  - Test verifying the fix

### 2. New Features
- **Discuss first**: Create issue describing feature
- Ensure it aligns with project goals
- Follow architecture patterns (see [ARCHITECTURE.md](../technical/ARCHITECTURE.md))

### 3. Documentation Improvements
- Clarifying existing docs
- Adding examples
- Fixing outdated information

Submit as PR directly without issue approval needed!

### 4. Performance Improvements
- Include before/after benchmarks
- Don't sacrifice readability  
- Add test verifying the improvement

### 5. Calibration Improvements
- New basin configurations: submit YAML in `ops/configs/basins/`
- Calibration refinements: update notebook + document in PR
- EVT parameter improvements: include statistical justification

## Architecture Conventions

When adding new modules:

1. **Layer placement**: 
   - External APIs → `adapters/`
   - Business logic → `domain/` or `models/`
   - Configuration → `config/`
   - Workflows → `pipelines/`

2. **Dependency direction**:
   ```
   pipelines/ → models/ → adapters/, domain/ → config/
   ↑                                              ↓
   └──────────────── utils/ ─────────────────────┘
   ```
   Lower layers don't import from higher layers.

3. **Testing**:
   - Mock external dependencies (adapters)
   - Test domain logic independently
   - Integration tests in `tests/`

## Getting Help

- **Questions about contribution process?** Comment on the issue or PR
- **Code review feedback unclear?** Ask for clarification
- **Need design input?** Start a discussion issue first
- **Want to discuss a feature?** Open an issue with `discussion` label

## Code of Conduct

- Be respectful and inclusive
- Welcome diverse perspectives
- Constructive feedback only
- No discrimination or harassment

Report violations to [maintainers email]

---

## Useful Resources

- [ARCHITECTURE.md](../technical/ARCHITECTURE.md) - Module organization
- [TESTING.md](TESTING.md) - Testing procedures
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Conventional Commits](https://www.conventionalcommits.org/)

Thank you for contributing! 🙏
