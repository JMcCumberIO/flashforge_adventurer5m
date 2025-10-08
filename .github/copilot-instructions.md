# GitHub Copilot Instructions

## Project Overview

This is a **Home Assistant custom integration** for the FlashForge Adventurer 5M Pro 3D printer. The integration provides local network communication with the printer via:
- **HTTP API** (port 8898) - for status polling and sensor data
- **TCP M-code interface** (port 8899) - for printer control operations
- **MJPEG stream** (port 8080) - for camera feed

## Technology Stack

- **Python 3.11+** - Primary language
- **Home Assistant** - Integration framework
- **asyncio** - Asynchronous I/O operations
- **aiohttp** - HTTP client for API calls
- **voluptuous** - Schema validation for services

## Code Style and Standards

### Python Code
- Follow **Black** code formatting (no configuration needed, use defaults)
- Use **type hints** for all function parameters and return values
- Write **comprehensive docstrings** for all classes and functions
- Follow Home Assistant's [integration development guidelines](https://developers.home-assistant.io/)
- Use `_LOGGER` for logging (already imported in most modules)
- Prefer f-strings for string formatting

### Naming Conventions
- Constants: `UPPER_SNAKE_CASE` (defined in `const.py`)
- Functions/methods: `snake_case`
- Classes: `PascalCase`
- Private methods: `_leading_underscore`
- Service names: `snake_case`

### Import Organization
1. Standard library imports
2. Third-party library imports
3. Home Assistant imports
4. Local imports (from `.const`, `.coordinator`, etc.)

## Architecture

### Key Components

1. **`__init__.py`** - Entry point, service registration, and setup
2. **`coordinator.py`** - Data update coordinator, TCP communication
3. **`config_flow.py`** - Configuration UI flow
4. **`const.py`** - Constants and configuration keys
5. **`flashforge_tcp.py`** - Low-level TCP communication
6. **Platform files**:
   - `sensor.py` - Temperature, progress, position sensors
   - `binary_sensor.py` - Status indicators (door, lights, endstops, etc.)
   - `camera.py` - Camera feed
   - `button.py` - One-click actions
   - `number.py` - Numeric controls
   - `select.py` - Dropdown selections

### Data Flow
1. Coordinator fetches data via HTTP API (`/detail` endpoint)
2. Coordinator parses JSON response and updates entities
3. TCP commands are sent for control operations (M-codes)
4. Services expose functionality to Home Assistant users

## Security Requirements

### Critical Rules
- **NEVER commit real printer credentials** (IP addresses, serial numbers, check codes)
- **NEVER include sensitive data in code or tests**
- Use mock data for all examples and tests
- All test files should be in `.gitignore`

### Test Data Location
- Test scripts are in `scripts/` directory (not committed)
- Test data should use placeholder values like:
  - IP: `192.168.1.50` or `printer.local`
  - Serial: `SERIAL12345`
  - Check Code: `CHECKCODE123`

## Testing Guidelines

### Important Notes
- This integration requires a **physical printer** for testing
- Tests are **local development only** and not committed to the repository
- The test infrastructure is documented in `CONTRIBUTING.md`

### Running Tests
```bash
# Setup test environment (local only)
python scripts/setup_test_env.py --printer-ip YOUR_PRINTER_IP --serial YOUR_SERIAL --code YOUR_CODE

# Run quick tests
python scripts/run_test_suite.py --config quick

# Run full tests
python scripts/run_test_suite.py --config full
```

### When Adding New Features
- Document expected behavior in docstrings
- Consider adding unit tests (if test infrastructure exists)
- Test manually with a physical printer when possible
- Update `services.yaml` for new services
- Update `README.md` with new features

## Common Patterns

### Adding a New Service

1. Define service constant in `__init__.py`:
```python
SERVICE_MY_NEW_SERVICE = "my_new_service"
```

2. Define service schema if needed:
```python
SERVICE_MY_NEW_SERVICE_SCHEMA = vol.Schema({
    vol.Required("parameter"): vol.Coerce(int),
})
```

3. Create service handler:
```python
async def handle_my_new_service(call: ServiceCall):
    coordinator: FlashforgeDataUpdateCoordinator = hass.data[DOMAIN][call.data["entity_id"]]
    await coordinator.my_new_service(call.data["parameter"])
```

4. Register service in `async_setup_entry`:
```python
hass.services.async_register(
    DOMAIN, 
    SERVICE_MY_NEW_SERVICE, 
    handle_my_new_service,
    schema=SERVICE_MY_NEW_SERVICE_SCHEMA
)
```

5. Add to `services.yaml`:
```yaml
my_new_service:
  name: My New Service
  description: Description of what this service does
  fields:
    parameter:
      name: Parameter
      description: Parameter description
      required: true
      selector:
        number:
          min: 0
          max: 100
```

6. Implement coordinator method:
```python
async def my_new_service(self, parameter: int) -> bool:
    """Docstring explaining what this does."""
    return await self._send_tcp_command(f"~M123 P{parameter}")
```

### Adding a New Sensor

1. Add constants to `const.py`:
```python
API_ATTR_MY_SENSOR = "my_sensor_key"
NAME_MY_SENSOR = "My Sensor Name"
ICON_MY_SENSOR = "mdi:icon-name"
```

2. Add sensor description in appropriate platform file (e.g., `sensor.py`):
```python
FlashforgeSensorEntityDescription(
    key=API_ATTR_MY_SENSOR,
    name=NAME_MY_SENSOR,
    icon=ICON_MY_SENSOR,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
)
```

3. Update data fetching in `coordinator.py` if needed

### TCP Communication

Use the centralized helper method:
```python
await self._send_tcp_command("~M114")  # Returns response string
```

For commands that modify printer state, return `bool`:
```python
async def my_command(self) -> bool:
    response = await self._send_tcp_command("~M106 S255")
    return response is not None
```

## Error Handling

- Catch specific exceptions when possible
- Log errors with appropriate severity:
  - `_LOGGER.error()` - For errors that affect functionality
  - `_LOGGER.warning()` - For recoverable issues
  - `_LOGGER.debug()` - For detailed debugging info
- Always include `exc_info=True` for exception logging:
```python
except Exception as e:
    _LOGGER.error("Failed to do something: %s", e, exc_info=True)
```

## Documentation

### Update These Files When Making Changes
- **`README.md`** - User-facing documentation for new features
- **`CONTRIBUTING.md`** - Development guidelines if workflow changes
- **`services.yaml`** - Service definitions for Home Assistant UI
- **Docstrings** - All new functions and classes

### Docstring Format
```python
async def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ValueError: If param2 is negative
    """
```

## Pull Request Guidelines

1. Keep changes focused and minimal
2. Update documentation for user-facing changes
3. Follow the PR template
4. Ensure no sensitive data is included
5. Self-review changes before submitting
6. Test locally with a physical printer when possible

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Quality Scale](https://www.home-assistant.io/docs/quality_scale/)
- [Project CONTRIBUTING.md](../CONTRIBUTING.md)
- [Project README.md](../README.md)

## Questions?

If you're unsure about something:
1. Check existing code for patterns
2. Review `CONTRIBUTING.md` and `README.md`
3. Look at similar Home Assistant integrations
4. When in doubt, ask for clarification in issues/PRs
