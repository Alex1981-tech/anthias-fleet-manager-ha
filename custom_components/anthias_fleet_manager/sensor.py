"""Sensor platform for Anthias Fleet Manager."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnthiasCoordinator


@dataclass(kw_only=True, frozen=True)
class AnthiasSensorEntityDescription(SensorEntityDescription):
    """Describes an Anthias sensor entity."""

    value_fn: Callable[[dict[str, Any]], float | str | None]


def _cpu_temp(info: dict) -> float | None:
    val = info.get("cpu_temp")
    if val is not None:
        return round(float(val), 1)
    return None


def _cpu_usage(info: dict) -> float | None:
    val = info.get("cpu_usage")
    if val is not None:
        return round(float(val), 1)
    return None


def _memory_percent(info: dict) -> float | None:
    mem = info.get("memory", {})
    total = mem.get("total")
    used = mem.get("used")
    if total and used:
        return round(float(used) / float(total) * 100, 1)
    return None


def _disk_free_gb(info: dict) -> float | None:
    disk = info.get("disk_usage", {})
    free = disk.get("free_gb")
    if free is not None:
        return round(float(free), 1)
    return None


def _uptime_hours(info: dict) -> float | None:
    uptime = info.get("uptime", {})
    days = uptime.get("days", 0)
    hours = uptime.get("hours", 0)
    if days is not None and hours is not None:
        return round(float(days) * 24 + float(hours), 1)
    return None


def _ip_address(info: dict) -> str | None:
    ips = info.get("ip_addresses", [])
    if ips:
        # Strip http:// prefix if present
        ip = str(ips[0])
        for prefix in ("http://", "https://"):
            if ip.startswith(prefix):
                ip = ip[len(prefix):]
        return ip.rstrip("/")
    return None


def _mac_address(info: dict) -> str | None:
    return info.get("mac_address")


SENSOR_DESCRIPTIONS: tuple[AnthiasSensorEntityDescription, ...] = (
    AnthiasSensorEntityDescription(
        key="cpu_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_cpu_temp,
    ),
    AnthiasSensorEntityDescription(
        key="cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:cpu-64-bit",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_cpu_usage,
    ),
    AnthiasSensorEntityDescription(
        key="memory_usage",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_memory_percent,
    ),
    AnthiasSensorEntityDescription(
        key="disk_free",
        native_unit_of_measurement="GB",
        icon="mdi:harddisk",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_disk_free_gb,
    ),
    AnthiasSensorEntityDescription(
        key="uptime",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-outline",
        value_fn=_uptime_hours,
    ),
    AnthiasSensorEntityDescription(
        key="ip_address",
        icon="mdi:ip-network",
        value_fn=_ip_address,
    ),
    AnthiasSensorEntityDescription(
        key="mac_address",
        icon="mdi:ethernet",
        value_fn=_mac_address,
    ),
)


@dataclass(kw_only=True, frozen=True)
class AnthiasScheduleSensorDescription(SensorEntityDescription):
    """Describes an Anthias schedule sensor entity."""

    value_fn: Callable[[dict[str, Any]], float | str | None]
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _active_schedule_slot(player: dict) -> str | None:
    status = player.get("schedule_status", {})
    active = status.get("active_slot")
    if active and isinstance(active, dict):
        return active.get("name", "Unknown")
    return None


def _active_slot_extra_attrs(player: dict) -> dict[str, Any]:
    slots = player.get("schedule_slots", [])
    status = player.get("schedule_status", {})
    active = status.get("active_slot") or {}
    return {
        "slot_names": [s.get("name", "") for s in slots],
        "slot_types": [s.get("slot_type", "") for s in slots],
        "active_slot_id": active.get("id"),
        "active_slot_type": active.get("slot_type"),
    }


def _schedule_slot_count(player: dict) -> int:
    return len(player.get("schedule_slots", []))


SCHEDULE_SENSOR_DESCRIPTIONS: tuple[AnthiasScheduleSensorDescription, ...] = (
    AnthiasScheduleSensorDescription(
        key="active_schedule_slot",
        icon="mdi:calendar-clock",
        value_fn=_active_schedule_slot,
        extra_attrs_fn=_active_slot_extra_attrs,
    ),
    AnthiasScheduleSensorDescription(
        key="schedule_slot_count",
        icon="mdi:calendar-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_schedule_slot_count,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: AnthiasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        AnthiasPlayerSensor(coordinator, player_id, desc)
        for player_id in coordinator.data
        for desc in SENSOR_DESCRIPTIONS
    ]
    entities.extend(
        AnthiasScheduleSensor(coordinator, player_id, desc)
        for player_id in coordinator.data
        for desc in SCHEDULE_SENSOR_DESCRIPTIONS
    )
    async_add_entities(entities)


class AnthiasPlayerSensor(CoordinatorEntity[AnthiasCoordinator], SensorEntity):
    """Sensor entity for a player metric."""

    entity_description: AnthiasSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnthiasCoordinator,
        player_id: str,
        description: AnthiasSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._player_id = player_id
        self.entity_description = description
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_{description.key}"
        self._attr_name = f"{player['name']} {description.key.replace('_', ' ').title()}"

    @property
    def device_info(self):
        player = self.coordinator.data.get(self._player_id, {})
        info = player.get("info", {})
        return {
            "identifiers": {(DOMAIN, self._player_id)},
            "name": player.get("name", self._player_id),
            "manufacturer": "Anthias",
            "model": info.get("device_model", "Anthias Player"),
            "sw_version": info.get("anthias_version"),
        }

    @property
    def native_value(self) -> float | str | None:
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        info = player.get("info", {})
        return self.entity_description.value_fn(info)

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        player = self.coordinator.data.get(self._player_id)
        return player is not None and player.get("is_online", False)


class AnthiasScheduleSensor(CoordinatorEntity[AnthiasCoordinator], SensorEntity):
    """Sensor entity for schedule data (uses player dict, not info)."""

    entity_description: AnthiasScheduleSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnthiasCoordinator,
        player_id: str,
        description: AnthiasScheduleSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._player_id = player_id
        self.entity_description = description
        player = coordinator.data[player_id]
        self._attr_unique_id = f"{player_id}_{description.key}"
        self._attr_name = (
            f"{player['name']} {description.key.replace('_', ' ').title()}"
        )

    @property
    def device_info(self):
        player = self.coordinator.data.get(self._player_id, {})
        info = player.get("info", {})
        return {
            "identifiers": {(DOMAIN, self._player_id)},
            "name": player.get("name", self._player_id),
            "manufacturer": "Anthias",
            "model": info.get("device_model", "Anthias Player"),
            "sw_version": info.get("anthias_version"),
        }

    @property
    def native_value(self) -> float | str | None:
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        return self.entity_description.value_fn(player)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.extra_attrs_fn is None:
            return None
        player = self.coordinator.data.get(self._player_id)
        if player is None:
            return None
        return self.entity_description.extra_attrs_fn(player)

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        player = self.coordinator.data.get(self._player_id)
        return player is not None and player.get("is_online", False)
