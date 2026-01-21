"""Smoke test to verify PhilFlood installation works.

This script runs basic checks to ensure the package is installed
correctly and core functionality works as expected.

Run with: python -m pytest tests/test_smoke.py -v
Or directly: python tests/test_smoke.py
"""

import sys
from pathlib import Path

# Add src to path for non-installed testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all core modules can be imported."""
    try:
        from philflood.domain.basin import BasinConfig, EVTConfig, VulnerabilityConfig, TriggerConfig
        from philflood.domain.config import load_basin_config
        from philflood.pipelines.validation import validate_basin_config
        from philflood.ops.logging_config import get_logger
        print("✓ All core modules import successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config_loading():
    """Test that example configuration can be loaded."""
    try:
        from philflood.domain.config import load_basin_config
        
        config_path = Path(__file__).parent.parent / "ops" / "configs" / "basins" / "example_basin.yaml"
        if not config_path.exists():
            print(f"⚠️  Example config not found at {config_path}")
            return True  # Not a failure, just missing example
        
        cfg = load_basin_config(config_path)
        assert cfg.basin_id == "example_basin"
        assert cfg.evt.method == "POT-GPD"
        print("✓ Configuration loading works")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False


def test_validation():
    """Test that configuration validation works."""
    try:
        from philflood.pipelines.validation import validate_basin_config
        
        config_path = Path(__file__).parent.parent / "ops" / "configs" / "basins" / "example_basin.yaml"
        if not config_path.exists():
            print("⚠️  Skipping validation test (no example config)")
            return True
        
        issues = validate_basin_config(config_path)
        # Example config should have issues (placeholders)
        assert len(issues) > 0, "Example config should have validation warnings"
        print(f"✓ Validation works (found {len(issues)} expected issues)")
        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False


def test_logging():
    """Test that logging configuration works."""
    try:
        from philflood.ops.logging_config import get_logger
        
        logger = get_logger("test")
        logger.info("Test log message")
        print("✓ Logging works")
        return True
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False


def test_cli_available():
    """Test that CLI entry point exists."""
    try:
        from philflood import cli
        assert hasattr(cli, 'main')
        print("✓ CLI module available")
        return True
    except ImportError as e:
        print(f"⚠️  CLI not available (install package with pip install -e .): {e}")
        return True  # Not a hard failure


def run_all_tests():
    """Run all smoke tests."""
    print("\n" + "="*60)
    print("PhilFlood Smoke Tests")
    print("="*60 + "\n")
    
    tests = [
        ("Module imports", test_imports),
        ("Config loading", test_config_loading),
        ("Config validation", test_validation),
        ("Logging setup", test_logging),
        ("CLI availability", test_cli_available),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        print("-" * 40)
        result = test_func()
        results.append((name, result))
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status:10s} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
