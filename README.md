# FlashForge Adventurer 5M Pro Integration

This project integrates the **FlashForge Adventurer 5M** 3D printer in LAN mode with Home Assistant.

## Features

- **Monitor Printer Status (via HTTP API on port 8898):**
  - View real-time operational status (e.g., Idle, Printing, Paused).
  - Track print progress, layer information, and time estimates.
  - Monitor extruder and bed temperatures (current and target).
  - View firmware version, IP/MAC address, and other diagnostic details.
  - Get current X, Y, Z nozzle positions (in mm).
  - List printable files available on the printer (via the "Printable Files Count" sensor's attributes).
  - Binary sensor states for:
    - Connection
    - Error
    - Door Open
    - Light On (actual light)
    - Auto Shutdown Enabled
    - External Fan Active
    - Internal Fan Active
    - X Endstop
    - Y Endstop
    - Z Endstop
    - Filament Sensor
    - Bed Leveling Active
  - Many diagnostic and configuration sensors (like Connection, Error, Fans, Endstops, Bed Leveling) are now directly visible on the main device panel in Home Assistant for easier access.
- **View Camera Feed**
  - Access live camera feed from the printer's webcam.
- **Control Printer Operations (primarily via TCP M-codes on port 8899):**
  - Start new print jobs by specifying the file path on the printer (`start_print`).
  - Pause active print jobs (`pause_print`).
  - Resume paused print jobs (`resume_print`).
  - Cancel ongoing print jobs (`cancel_print`).
  - Toggle the printer's built-in LED light (`toggle_light`).
  - Set target temperatures for the extruder and heated bed (`set_extruder_temperature`, `set_bed_temperature`).
  - Control the part cooling fan speed, including turning it off (`set_fan_speed`, `turn_fan_off`).
  - Move individual axes for jogging/manual positioning (`move_axis`).
  - Enable/Disable stepper motors (`enable_steppers`, `disable_steppers`).
  - Set print speed percentage (`set_speed_percentage`).
  - Delete files from printer storage (`delete_file`).


## Requirements

- **Home Assistant** 2023.10 or later
- **FlashForge Adventurer 5M Pro 3D Printer**
    - Testing has been completed in "LAN-Only" mode. 
- **Network Connection** to the printer
- Ensure Home Assistant can reach the printer on TCP port 8898 (for status/sensor data) and TCP port 8899 (for control commands). The camera stream uses port 8080 or a URL provided by the printer.

## Installation

1. **Clone the Repository**

   Clone this repository to your Home Assistant `config/custom_components` directory:

   ```bash
   git clone https://github.com/xombie21/flashforge_adventurer5m.git
   ```

2. **Configure Integration**

   This integration is configured via the Home Assistant UI after installation.

   a. **Using Home Assistant UI**
      - Navigate to `Settings` > `Devices & Services` > `Add Integration`.
      - Search for `FlashForge Adventurer 5M Pro`.
      - Enter the required details:
        - **Host**: IP address or hostname of your printer (e.g., 192.168.1.50).
        - **Serial Number**: Serial number of your printer (often includes an 'SN' prefix, which should be included if displayed by your printer).
        - **Check Code**: Authentication code for your printer.

3. **Restart Home Assistant**

   Restart Home Assistant to apply the changes.

### Sensor Update Intervals
This integration allows you to configure two sensor update intervals via the integration's "Configure" option in Home Assistant (under Settings > Devices & Services):

*   **Scan Interval:** The standard update interval for fetching data from the printer when it is idle or in a non-printing state. Default is 10 seconds.
*   **Printing Scan Interval:** A faster update interval used when the printer is actively printing (e.g., status is BUILDING, PRINTING, RUNNING). This allows for more real-time monitoring of progress, temperatures, etc., during a print. Default is 2 seconds.

Adjust these values based on your needs and network performance. Faster updates provide more current data but can increase network traffic and load on Home Assistant and the printer.

## Usage

After installation, the FlashForge Adventurer 5M Pro integration will appear in the Home Assistant UI. You can manage your 3D printer through the available entities, including sensors and camera feed.

- **Monitor Status:** Check the printer's current status, temperature readings, and more.
- **Camera Feed:** View a live stream from the printer's webcam directly within Home Assistant.

### Printer Controls

You can control your Flashforge Adventurer 5M Pro using various services provided by this integration. Call these services from your automations or the Developer Tools > Services UI. Most control commands are sent via TCP to port 8899, while status is polled via HTTP on port 8898.

**Light Control:**
*   `flashforge_adventurer5m.toggle_light`
    *   **Toggle Light:** Toggles the printer's chamber light.
    *   **Parameters:**
        *   `state` (boolean, required): `true` to turn on, `false` to turn off.

**Print Job Management:**
*   `flashforge_adventurer5m.start_print`
    *   **Start Print:** Starts printing a specified file from the printer's storage. The path should match those reported by the "Printable Files Count" sensor's attributes (e.g., `/data/yourfile.gcode`).
    *   **Parameters:**
        *   `file_path` (string, required): Path to the G-code file on the printer (e.g., `/data/yourfile.gcode`).
*   `flashforge_adventurer5m.pause_print`
    *   **Pause Print:** Pauses the current print job.
*   `flashforge_adventurer5m.resume_print`
    *   **Resume Print:** Resumes a paused print job.
*   `flashforge_adventurer5m.cancel_print`
    *   **Cancel Print:** Cancels the ongoing print job.

**Temperature Control:**
*   `flashforge_adventurer5m.set_extruder_temperature`
    *   **Set Extruder Temperature:** Sets the target temperature for the extruder.
    *   **Parameters:**
        *   `temperature` (integer, required): Target temperature in Celsius. (Selector: number, min: 0, max: 300, unit: °C)
*   `flashforge_adventurer5m.set_bed_temperature`
    *   **Set Bed Temperature:** Sets the target temperature for the heated bed.
    *   **Parameters:**
        *   `temperature` (integer, required): Target temperature in Celsius. (Selector: number, min: 0, max: 120, unit: °C)

**Fan Control:**
*   `flashforge_adventurer5m.set_fan_speed`
    *   **Set Fan Speed:** Sets the speed of the part cooling fan.
    *   **Parameters:**
        *   `speed` (integer, required): Fan speed from 0 (off) to 255 (full speed). (Selector: number, min: 0, max: 255)
*   `flashforge_adventurer5m.turn_fan_off`
    *   **Turn Fan Off:** Turns the part cooling fan off.

**Axis Movement (Jogging):**
*   `flashforge_adventurer5m.move_axis`
    *   **Move Axis:** Moves one or more axes to specified absolute coordinates. Use with caution.
    *   **Parameters (all optional, but at least one axis must be provided):**
        *   `x` (float, optional): Target X-axis coordinate in mm. (Selector: number, min: 0, max: 220, unit: mm)
        *   `y` (float, optional): Target Y-axis coordinate in mm. (Selector: number, min: 0, max: 220, unit: mm)
        *   `z` (float, optional): Target Z-axis coordinate in mm. (Selector: number, min: 0, max: 220, unit: mm)
        *   `feedrate` (integer, optional): Speed of movement in mm/minute. (Selector: number, min: 100, max: 6000, unit: mm/min)
*   `flashforge_adventurer5m.move_relative`
    *   **Move Relative:** Moves printer axes by a relative amount. Specify at least one axis. Printer returns to absolute G-code mode afterwards.
    *   **Parameters (all optional, but at least one axis must be provided):**
        *   `x` (float, optional): Relative move for X-axis (mm). Positive or negative. Example: `10.0`.
        *   `y` (float, optional): Relative move for Y-axis (mm). Positive or negative. Example: `-5.5`.
        *   `z` (float, optional): Relative move for Z-axis (mm). Positive or negative. Example: `1.0`.
        *   `feedrate` (integer, optional): Speed for this relative move (mm/min). Optional. Uses printer default if not set. Example: `1500`. (Selector: number, min: 100, max: 6000, unit: mm/min)

**Stepper Motor Control:**
*   `flashforge_adventurer5m.disable_steppers`
    *   **Disable Stepper Motors:** Disables all stepper motors on the printer (M18). This allows manual movement of axes but they will re-engage on the next motion command. No parameters.
*   `flashforge_adventurer5m.enable_steppers`
    *   **Enable Stepper Motors:** Enables all stepper motors on the printer (M17). Stepper motors are typically enabled automatically when a motion command is sent. No parameters.

**Print Parameter Control:**
*   `flashforge_adventurer5m.set_speed_percentage`
    *   **Set Speed Percentage:** Sets the printer's speed factor override (feedrate percentage via M220).
    *   **Parameters:**
        *   `percentage` (integer, required): Speed percentage (e.g., 100 for normal, 150 for 150%). Valid range typically 10-500. (Selector: number, min: 10, max: 500, unit: "%")
*   `flashforge_adventurer5m.set_flow_percentage`
    *   **Set Flow Percentage:** Sets the printer's extrusion flow rate percentage (M221 S<percentage>).
    *   **Parameters:**
        *   `percentage` (integer, required): Flow percentage (e.g., 100 for normal). Typical range 50-200. (Selector: number, min: 50, max: 200, unit: "%")

**File Management:**
*   `flashforge_adventurer5m.delete_file`
    *   **Delete File:** Deletes a specified file from the printer's storage. The file path should be relative to the user directory (e.g., 'my_model.gcode') or an absolute path like '/data/user/my_model.gcode'.
    *   **Parameters:**
        *   `file_path` (string, required): The path of the file to delete. Examples: `'test.gcode'`, `'/data/user/test.gcode'`. (Selector: text)
*   `flashforge_adventurer5m.list_files`
    *   **List Files:** Lists files on the printer's storage (via M20). The full list is logged at DEBUG level by the integration, a summary may be logged at INFO level. No parameters.

**Homing and Leveling:**
*   `flashforge_adventurer5m.home_axes`
    *   **Home Axes:** Homes one or more axes (G28). If no axes are specified, all axes are homed.
    *   **Parameters (all optional):**
        *   `x` (boolean, optional): Home X-axis. Set to `true` to include X-axis in homing.
        *   `y` (boolean, optional): Home Y-axis. Set to `true` to include Y-axis in homing.
        *   `z` (boolean, optional): Home Z-axis. Set to `true` to include Z-axis in homing.
*   `flashforge_adventurer5m.start_bed_leveling`
    *   **Start Bed Leveling:** Initiates the automatic bed leveling procedure (via G29). Behavior can vary based on printer firmware. No parameters.

**Printer Operations:**
*   `flashforge_adventurer5m.filament_change`
    *   **Filament Change:** Initiates the filament change procedure (M600). Behavior depends on printer firmware. No parameters.
*   `flashforge_adventurer5m.emergency_stop`
    *   **Emergency Stop:** Immediately halts all printer operations (M112). Use with extreme caution. No parameters.
*   `flashforge_adventurer5m.play_beep`
    *   **Play Beep:** Plays a beep sound on the printer (via M300).
    *   **Parameters:**
        *   `pitch` (integer, required): Frequency of the beep in Hz. Example: `1000`. (Selector: number, min: 0, max: 10000, unit: Hz)
        *   `duration` (integer, required): Duration of the beep in milliseconds. Example: `500`. (Selector: number, min: 0, max: 10000, unit: ms)

**Settings Management:**
*   `flashforge_adventurer5m.save_settings_to_eeprom`
    *   **Save Settings to EEPROM:** Saves current settings to printer's EEPROM (via M500). No parameters.
*   `flashforge_adventurer5m.restore_factory_settings`
    *   **Restore Factory Settings:** Restores printer to factory default settings (M502). Use with extreme caution; this may erase calibration. No parameters.
*   `flashforge_adventurer5m.read_settings_from_eeprom`
    *   **Read Settings from EEPROM:** Reads current settings from EEPROM (via M501) and logs them. The full output is logged at DEBUG level, a summary may be logged at INFO level. No parameters.

**Diagnostics:**
*   `flashforge_adventurer5m.report_firmware_capabilities`
    *   **Report Firmware Capabilities:** Requests and logs the printer's firmware version and capabilities (via M115). The full report is logged at DEBUG level, a summary may be logged at INFO level. No parameters.

## Troubleshooting

If you encounter issues with the camera feed, such as:

`Error getting new camera image from 3D Printer: Server disconnected without sending a response.`

Ensure that:

**Stream URL Configuration:**

- The cameraStreamUrl provided by the printer is correct.
- If cameraStreamUrl is not available, the fallback URL (http://YOUR_PRINTER_IP:8080/?action=stream) is accessible.

**Network Configuration:**

- Home Assistant and the printer are on the same network segment.
- Necessary ports (e.g., 8080) are open and not blocked by firewalls.

**Stream Accessibility:**
Test the stream URL using a web browser:

- Enter the stream URL, for example: `http://192.168.1.50:8080/?action=stream`

**Home Assistant Logs:**

- Check Settings > System > Logs for any related error messages.
- Ensure that the integration is fetching data correctly without errors.

**Control Command Issues:**
If services like toggling the light, pausing/resuming prints, setting temperatures, etc., are not working:
- Verify that your printer's IP address is correctly configured in the integration.
- Ensure your firewall allows Home Assistant to make outgoing TCP connections to your printer on port 8899 (for M-code commands) in addition to port 8898 (for status).
- Check the Home Assistant logs for any error messages from the `flashforge_adventurer5m` integration when you call a service.

## Development and Testing

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
