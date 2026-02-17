# Anthias Fleet Manager for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Release](https://img.shields.io/github/v/release/Alex1981-tech/anthias-fleet-manager-ha)](https://github.com/Alex1981-tech/anthias-fleet-manager-ha/releases)

Home Assistant integration for [Anthias Fleet Manager](https://github.com/Alex1981-tech/Anthias-fleet-manager) — monitor and control your Anthias digital signage players directly from Home Assistant.

## Features

### Entities (per player)

| Platform | Entity | Description |
|----------|--------|-------------|
| Binary Sensor | Online Status | Player connectivity (online/offline) |
| Sensor | CPU Temperature | CPU temperature in Celsius |
| Sensor | CPU Usage | CPU usage percentage |
| Sensor | Memory Usage | Memory usage percentage |
| Sensor | Disk Free | Free disk space in GB |
| Sensor | Uptime | Uptime in hours |
| Sensor | IP Address | Player IP address |
| Sensor | MAC Address | Player MAC address |
| Sensor | Active Schedule Slot | Currently active schedule slot name |
| Sensor | Schedule Slot Count | Number of schedule slots |
| Switch | Display (CEC) | TV power control via HDMI-CEC |
| Media Player | Media Player | Current content, next/prev, on/off |
| Camera | Screenshot | Live screenshot from player display |
| Button | Reboot | Reboot the player |
| Button | Shutdown | Shutdown the player |

### Services (for automations)

| Service | Description |
|---------|-------------|
| `anthias_fleet_manager.deploy_content` | Deploy media from FM library to player |
| `anthias_fleet_manager.create_asset` | Create a URL asset on player |
| `anthias_fleet_manager.delete_asset` | Delete an asset from player |
| `anthias_fleet_manager.toggle_asset` | Enable/disable an asset |
| `anthias_fleet_manager.create_schedule_slot` | Create a schedule slot |
| `anthias_fleet_manager.delete_schedule_slot` | Delete a schedule slot |
| `anthias_fleet_manager.add_slot_item` | Add asset to schedule slot |
| `anthias_fleet_manager.remove_slot_item` | Remove item from schedule slot |
| `anthias_fleet_manager.trigger_update` | Trigger player software update |

## Screenshots

<!-- Screenshots will be added after deployment -->
<!-- ![Device Page](docs/screenshots/device-page.png) -->
<!-- ![Media Player Card](docs/screenshots/media-player-card.png) -->
<!-- ![Services](docs/screenshots/services.png) -->
<!-- ![Config Flow](docs/screenshots/config-flow.png) -->

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/Alex1981-tech/anthias-fleet-manager-ha` as **Integration**
4. Search for "Anthias Fleet Manager" and install
5. Restart Home Assistant

### Manual

1. Download the latest release from [GitHub](https://github.com/Alex1981-tech/anthias-fleet-manager-ha/releases)
2. Copy the `custom_components/anthias_fleet_manager` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Anthias Fleet Manager"
3. Enter your Fleet Manager URL (e.g., `http://192.168.1.100:9000`)
4. Enter your username and password
5. Click **Submit**

The integration will automatically discover all players registered with your Fleet Manager and create entities for each one.

## Automation Examples

### Emergency Message on All Players

```yaml
automation:
  - alias: "Emergency message on all players"
    trigger:
      - platform: state
        entity_id: binary_sensor.fire_alarm
        to: "on"
    action:
      - service: anthias_fleet_manager.create_asset
        data:
          player_id: "your-player-uuid"
          name: "Emergency Alert"
          uri: "https://your-server.com/emergency.html"
          duration: 30
          mimetype: "webpage"
```

### Nightly Reboot

```yaml
automation:
  - alias: "Nightly player reboot"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.lobby_display_reboot
```

### Turn Off Display After Hours

```yaml
automation:
  - alias: "Turn off display at closing time"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.lobby_display_display
```

## Requirements

- Anthias Fleet Manager v1.4.0 or later
- Home Assistant 2024.1 or later
- Network access from Home Assistant to Fleet Manager

## License

MIT
