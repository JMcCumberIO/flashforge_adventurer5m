# GitHub Copilot Instructions for FlashForge Adventurer 5M Integration

## Repository Overview

This is a Home Assistant custom integration for the FlashForge Adventurer 5M Pro 3D printer. The integration provides comprehensive monitoring and control capabilities via the printer's network API.

### Architecture

The integration uses two network interfaces:
- **Port 8898 (HTTP API)**: Status polling and sensor data retrieval
- **Port 8899 (TCP M-code)**: Printer control commands (G-code/M-code)

## Key Technologies

- **Platform**: Home Assistant custom component
- **Python Version**: 3.10+
- **Key Dependencies**: aiohttp, Home Assistant core libraries
- **Communication**: HTTP REST API + TCP socket connections

## Code Style and Standards

### Python Guidelines

1. **Formatting**: Use Black formatter for all Python code
2. **Type Hints**: Always include type hints for function parameters and return values
3. **Documentation**: Write clear docstrings for all functions and classes
4. **Imports**: Follow standard import ordering (standard library, third-party, local)

Example:
```python
from typing import Optional

async def fetch_data(self, timeout: int = 10) -> Optional[dict[str, Any]]:
    """Fetch printer data from HTTP API.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary containing printer data, or None on error
    """
```

### File Organization

- `__init__.py`: Integration setup and service registration
- `coordinator.py`: Data fetching and command execution
- `const.py`: Constants and configuration values
- `config_flow.py`: Configuration UI flow
- `sensor.py`: Sensor entity definitions
- `binary_sensor.py`: Binary sensor entities
- `camera.py`: Camera feed entity
- `flashforge_tcp.py`: TCP connection handling

## Development Workflow

### Testing Requirements

**IMPORTANT**: This integration requires a physical printer for testing. All test files are git-ignored for security.

1. **Never commit**:
   - Real printer credentials
   - Network configuration details
   - Captured printer responses
   - Personal test data

2. **Always use**:
   - Mock data for tests
   - Development printer only
   - Local test configuration

3. **Testing commands**:
   ```bash
   python scripts/run_test_suite.py --config quick
   python scripts/run_test_suite.py --config full
   python scripts/analyze_coverage.py
   ```

### Security Guidelines

- No real credentials in code or tests
- Use constants from `const.py` for API keys and paths
- Review all changes for sensitive data leaks
- Follow security guidelines in CONTRIBUTING.md

## Common Patterns

### Adding a New Sensor

1. Define constants in `const.py`:
   ```python
   API_ATTR_NEW_SENSOR = "new_sensor_key"
   NAME_NEW_SENSOR = "New Sensor"
   ICON_NEW_SENSOR = "mdi:icon-name"
   ```

2. Add sensor description in `sensor.py` or `binary_sensor.py`
3. Update coordinator if new data fetching is required
4. Add appropriate unit of measurement and device class

### Adding a New Service

1. Define service constant in `__init__.py`
2. Create service handler function
3. Add schema validation using voluptuous
4. Register service in `async_setup_entry`
5. Implement method in coordinator if needed
6. Update `services.yaml` with service definition

### TCP Command Pattern

Use the `_send_tcp_command` helper in coordinator:
```python
command = f"~M104 S{temperature}\\r\\n"
action = f"SET EXTRUDER TEMPERATURE to {temperature}°C"
success, response = await self._send_tcp_command(command, action)
return success
```

## Error Handling

- Use structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Implement retry logic for network operations (see `MAX_RETRIES`, `RETRY_DELAY`)
- Validate API responses using `_validate_response` pattern
- Return meaningful error states to Home Assistant

## Common Issues and Solutions

### Connection Problems
- Verify both ports 8898 and 8899 are accessible
- Check firewall rules
- Validate printer is in LAN mode

### Temperature/Status Not Updating
- Check scan intervals configuration
- Verify API response structure matches expected format
- Review coordinator update cycle

### Command Failures
- Ensure proper M-code syntax with `~` prefix and `\r\n` suffix
- Check response parsing logic
- Verify TCP connection is established

## Documentation References

- [CONTRIBUTING.md](../CONTRIBUTING.md): Full contribution guidelines
- [README.md](../README.md): User-facing documentation
- [REVIEW_CHANGES.md](../REVIEW_CHANGES.md): Recent code review improvements
- [COVERAGE.md](../COVERAGE.md): Test coverage verification

## Making Changes

When modifying this integration:

1. **Check existing issues** before starting work
2. **Write tests first** when adding new features
3. **Update documentation** (README, docstrings, comments)
4. **Run linters and tests** before committing
5. **Keep changes focused** - one feature/fix per PR
6. **Review for security** - no credentials, safe for CI/CD

## Integration-Specific Notes

### Scan Intervals
- Default interval: 10 seconds (idle state)
- Printing interval: 2 seconds (active printing)
- Configurable via integration options

### State Management
- Coordinator manages shared state across entities
- Use `coordinator.data` dictionary for sensor values
- Update cycle fetches: API status, TCP position, endstops, bed leveling

### Entity Categories
Recent update reorganized entities for better UX:
- Diagnostic entities are visible on main device panel
- Configuration entities appear in separate section
- Priority given to frequently monitored states

## Questions?

For detailed information:
- Review existing code and tests
- Check closed issues for similar problems
- Consult CONTRIBUTING.md for development setup
- Open an issue for clarification if needed
