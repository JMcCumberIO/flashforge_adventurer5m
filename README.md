# FlashForge Adventurer 5M Pro Integration for Home Assistant

This project integrates the **FlashForge Adventurer 5M series** (including Pro) 3D printers in LAN mode with Home Assistant, offering comprehensive monitoring and control.

## Features

- **Real-time Printer Monitoring:**
  - Operational status (e.g., Idle, Printing, Paused, Error).
  - Print progress, layer information, and time estimates.
  - Extruder and bed temperatures (current and target).
  - Chamber temperature (if applicable).
  - Current X, Y, Z nozzle positions.
  - List of printable files (available via the "Print File" select entity and "Printable Files Count" sensor attributes).
- **Live Camera Feed:** View the printer's built-in webcam stream.
- **Comprehensive Entity Support:**
  - **Sensors:** Current temperatures, print progress, time estimates, X/Y/Z positions, status codes, and more.
  - **Binary Sensors:** Connection status, errors, door open, light status, printing state, endstops (X, Y, Z, Filament), bed leveling activity, fan status, auto-shutdown status.
  - **Camera:** Live video stream.
  - **Select Entity:** Select a file to print from the printer's storage.
  - **Number Entities:** Control target extruder temperature, target bed temperature, and cooling fan speed (0-255).
  - **Button Entities:** Trigger common actions like Pause Print, Resume Print, Cancel Print, Home Axes, Filament Change, and Start Bed Leveling.
- **Extensive Printer Control via Services:**
  - Full print job management: Start, Pause, Resume, Cancel.
  - Temperature settings for extruder and bed.
  - Cooling fan speed control.
  - Axis movement (absolute and relative jogging).
  - Stepper motor control (enable/disable).
  - Print parameter adjustments (speed and flow rate percentages).
  - File management: List files (output to logs), Delete files.
  - Printer operations: Homing, Bed Leveling, Filament Change, Emergency Stop, Play Beep.
  - EEPROM operations: Save, Read (output to logs), Restore factory settings.
  - **Generic G-code/M-code Sending:** For advanced users to send custom commands directly to the printer.

## Requirements

- **Home Assistant:** Version 2023.10 or later.
- **FlashForge Adventurer 5M Series Printer:** (e.g., Adventurer 5M, Adventurer 5M Pro).
- **Network Connection:** Printer connected to the same LAN as Home Assistant.
- **Network Ports:** Ensure Home Assistant can reach the printer on:
    - TCP port 8898 (HTTP API for status/sensor data).
    - TCP port 8899 (TCP M-Code interface for control commands).
    - Camera stream port (typically 8080 or a URL provided by the printer API).

## Installation

1.  **HACS Installation (Recommended):**
    *   Add this repository as a custom repository in HACS.
    *   Search for "FlashForge Adventurer 5M Pro" under Integrations and install it.
2.  **Manual Installation:**
    *   Clone this repository to your Home Assistant `config/custom_components/flashforge_adventurer5m` directory.
      ```bash
      git clone https://github.com/xombie21/flashforge_adventurer5m.git config/custom_components/flashforge_adventurer5m
      ```
3.  **Restart Home Assistant:** After installation (HACS or manual), restart Home Assistant.

## Configuration

Configure the integration via the Home Assistant UI:

1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **+ Add Integration**.
3.  Search for "FlashForge Adventurer 5M Pro" and select it.
4.  Enter the required details:
    *   **Host:** IP address or hostname of your printer (e.g., `192.168.1.50` or `printer.local`).
    *   **Serial Number:** The serial number of your printer (e.g., `SNAD5Mxxxxxx`). This is usually found on a sticker on the printer or via the printer's information screen.
    *   **Check Code:** The authentication code for your printer, typically found in the printer's network settings or information screen.

### Options

After initial setup, you can adjust polling intervals via the integration's "Configure" option:

*   **Idle Update Interval (seconds):** How often Home Assistant polls the printer when it's idle. Default: 10 seconds (Min: 5, Max: 300).
*   **Printing Update Interval (seconds):** How often Home Assistant polls the printer when it's actively printing. Default: 2 seconds (Min: 1, Max: 15).
    *   *Lower values provide more frequent updates but may increase network traffic and printer/HA load.*

## Supported Entities

This integration provides the following entities:

*   **Sensors:**
    *   Extruder Temperature (current & target)
    *   Bed Temperature (current & target)
    *   Chamber Temperature (current & target, if available)
    *   Print Progress
    *   Print Duration
    *   Estimated Time Remaining
    *   X, Y, Z Nozzle Position
    *   Printer Status (text)
    *   Status Code & Message (from API)
    *   Firmware Version, IP Address, MAC Address
    *   Cumulative Print Time & Filament Used
    *   Fan Speeds (RPM for chamber/cooling, if reported)
    *   TVOC, Remaining Disk Space, Z-Axis Compensation (if reported by API)
    *   Printable Files Count
*   **Binary Sensors:**
    *   Printing Status (is printing/building)
    *   Paused Status
    *   Error Status
    *   Connection Status (to printer API)
    *   Door Open
    *   Light On
    *   Auto Shutdown Enabled
    *   External Fan Active
    *   Internal Fan Active
    *   X, Y, Z Endstop Status
    *   Filament Sensor Status
    *   Bed Leveling Active Status
*   **Camera:**
    *   Live camera feed from the printer.
*   **Select:**
    *   **Print File:** Select a G-code file from the printer's storage to start printing.
*   **Number:**
    *   **Extruder Target Temperature:** Control the target temperature for the extruder.
    *   **Bed Target Temperature:** Control the target temperature for the heated bed.
    *   **Cooling Fan Speed:** Control the part cooling fan speed (0-255).
*   **Button:**
    *   **Pause Print:** Pause the current print.
    *   **Resume Print:** Resume a paused print.
    *   **Cancel Print:** Cancel the ongoing print.
    *   **Home Axes:** Home all printer axes (X, Y, Z).
    *   **Filament Change:** Initiate the filament change procedure (M600).
    *   **Start Bed Leveling:** Start the automatic bed leveling process (G29).

## Services

This integration provides a comprehensive set of services to control your FlashForge Adventurer 5M printer. You can find detailed descriptions and field information in **Developer Tools > Services** by searching for `flashforge_adventurer5m`.

**General Control:**
*   `flashforge_adventurer5m.pause_print`: Pauses the current print.
*   `flashforge_adventurer5m.resume_print`: Resumes a paused print.
*   `flashforge_adventurer5m.cancel_print`: Cancels the current print.
*   `flashforge_adventurer5m.start_print`: Starts printing a specified file.
    *   `file_path` (required): Path to the file on the printer.
*   `flashforge_adventurer5m.toggle_light`: Toggles the printer's LED light.
    *   `state` (required): `true` for on, `false` for off.
*   `flashforge_adventurer5m.emergency_stop`: Immediately halts all printer operations (M112). **Use with extreme caution.**

**Temperature & Fan Control:**
*   `flashforge_adventurer5m.set_extruder_temperature`: Sets extruder target temperature.
    *   `temperature` (required): Target temperature in Celsius.
*   `flashforge_adventurer5m.set_bed_temperature`: Sets bed target temperature.
    *   `temperature` (required): Target temperature in Celsius.
*   `flashforge_adventurer5m.set_fan_speed`: Sets cooling fan speed.
    *   `speed` (required): Speed from 0 (off) to 255 (full).
*   `flashforge_adventurer5m.turn_fan_off`: Turns the cooling fan off.

**Movement & Calibration:**
*   `flashforge_adventurer5m.home_axes`: Homes printer axes.
    *   `x`, `y`, `z` (optional booleans): Specify axes to home; defaults to all if none specified.
*   `flashforge_adventurer5m.move_axis`: Moves axes to absolute coordinates.
    *   `x`, `y`, `z` (optional floats): Target coordinates in mm.
    *   `feedrate` (optional int): Movement speed in mm/minute.
*   `flashforge_adventurer5m.move_relative`: Moves axes by a relative amount.
    *   `x`, `y`, `z` (optional floats): Relative offset in mm.
    *   `feedrate` (optional int): Movement speed in mm/minute.
*   `flashforge_adventurer5m.start_bed_leveling`: Initiates the bed leveling procedure (G29).
*   `flashforge_adventurer5m.filament_change`: Initiates the filament change procedure (M600).

**Printer Settings & Parameters:**
*   `flashforge_adventurer5m.disable_steppers`: Disables stepper motors (M18).
*   `flashforge_adventurer5m.enable_steppers`: Enables stepper motors (M17).
*   `flashforge_adventurer5m.set_speed_percentage`: Sets print speed factor override (M220).
    *   `percentage` (required): Speed percentage.
*   `flashforge_adventurer5m.set_flow_percentage`: Sets extrusion flow rate percentage (M221).
    *   `percentage` (required): Flow percentage.
*   `flashforge_adventurer5m.save_settings_to_eeprom`: Saves current settings to EEPROM (M500).
*   `flashforge_adventurer5m.read_settings_from_eeprom`: Reads settings from EEPROM and logs them (M501).
*   `flashforge_adventurer5m.restore_factory_settings`: Restores factory defaults (M502). **Use with extreme caution.**

**File Management & Diagnostics:**
*   `flashforge_adventurer5m.delete_file`: Deletes a file from printer storage.
    *   `file_path` (required): Path of the file to delete.
*   `flashforge_adventurer5m.list_files`: Lists files on printer storage (output to logs via M20).
*   `flashforge_adventurer5m.report_firmware_capabilities`: Logs printer firmware capabilities (M115).
*   `flashforge_adventurer5m.play_beep`: Plays a beep sound.
    *   `pitch` (required): Frequency in Hz.
    *   `duration` (required): Duration in milliseconds.
*   `flashforge_adventurer5m.send_gcode`: Sends a raw G-code/M-code command.
    *   `gcode` (required): The full command string (e.g., `~M115\\r\\n`). **Use with caution.**

## Troubleshooting

If you encounter issues with the camera feed, such as:
`Error getting new camera image from 3D Printer: Server disconnected without sending a response.`
Ensure that:
- The `cameraStreamUrl` provided by the printer (if any) is correct.
- If `cameraStreamUrl` is not available, the fallback URL (e.g., `http://YOUR_PRINTER_IP:8080/?action=stream`) is accessible. Test this URL in a web browser.
- Home Assistant and the printer are on the same network, and necessary ports (e.g., 8080) are not blocked by firewalls.
- Check Home Assistant logs (**Settings > System > Logs**) for related error messages.

If control commands (services) are not working:
- Verify the printer's IP address is correct in the integration configuration.
- Ensure your firewall allows Home Assistant to make outgoing TCP connections to the printer on port 8899 (for M-code commands) and port 8898 (for HTTP status).
- Check Home Assistant logs for errors from the `flashforge_adventurer5m` integration when calling a service.

## Development and Testing Notes
(This section remains largely the same as it's for contributors)

### Important Note
This integration's test suite is designed for local development only and requires access to a physical FlashForge Adventurer 5M Pro printer. To protect printer credentials and ensure safe testing practices, all test files are excluded from the git repository.
Note: This integration communicates with the printer using two main network ports: TCP port 8898 for the HTTP API (status, sensor data) and TCP port 8899 for the M-code command interface (printer controls).

### Local Development Setup
1. **Clone and Setup**
   ```bash
   git clone https://github.com/yourusername/flashforge_adventurer5m
   cd flashforge_adventurer5m
   python scripts/setup_test_env.py --printer-ip YOUR_PRINTER_IP --serial YOUR_SERIAL --code YOUR_CODE
   ```
2. **Install Dependencies**
   ```bash
   pip install -r requirements_test.txt
   ```
3. **Test Documentation**
   ```bash
   cat tests/README.md  # Review testing guidelines
   ```

### Test Data and Security
The test suite uses mock data to protect sensitive information:
- Test data files are git-ignored by default
- Credentials are stored in local configuration only
- Mock data generators are provided for test cases

**Never include in repository:**
- Real printer credentials
- Captured printer responses
- Network configuration details
- Personal test data

### Running Tests
1. **Quick Tests**
   ```bash
   python scripts/run_test_suite.py --config quick
   ```
2. **Generate Mock Data**
   ```bash
   python scripts/generate_test_data.py
   ```
3. **Full Test Suite**
   ```bash
   python scripts/run_test_suite.py --config full
   ```

### Testing Guidelines
1. **Use Mock Data**
   - Generate mock data using provided scripts
   - Never use real printer data in tests
   - Follow data structure guidelines
2. **Local Testing Only**
   - Use development printer only
   - Run in safe environment
   - Monitor printer state
3. **Security First**
   - Keep credentials private
   - Use example data in documentation
   - Follow secure development practices

For detailed testing instructions, see [Local Testing Guide](tests/README.md).

### Testing Disclaimer
The test suite is provided for development purposes only:
- Always test with a development printer
- Never test against production printers
- Use caution when running tests that modify printer state
- Be aware that some tests may affect printer operation

## Contributing
Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow security guidelines
4. Submit a pull request

## License
This project is licensed under the MIT License. See the LICENSE file for details.
