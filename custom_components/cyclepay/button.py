"""Implementation of an HA button."""
from __future__ import annotations

import asyncio
import logging

from homeassistant import core
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_platform import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pylaundry import Laundry
from pylaundry import LaundryMachine
from pylaundry import MachineType

from .const import DOMAIN

log = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the button platform."""

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    coordinator_data: Laundry = coordinator.data
    async_add_entities(
        (
            PayButton(
                coordinator=coordinator,
                machine_id=machine.id_,
            )
            for machine in coordinator_data.machines.values()
            if isinstance(machine, LaundryMachine)
        ),
        True,
    )


class PayButton(ButtonEntity, CoordinatorEntity):  # type: ignore
    """Integration Button Entity."""

    coordinator: DataUpdateCoordinator
    _attr_icon = "mdi:currency-usd"

    def __init__(self, coordinator: DataUpdateCoordinator, machine_id: str):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator=coordinator)

        self._machine_id = machine_id

        self.laundry: Laundry = coordinator.data
        machine: LaundryMachine = self.laundry.machines[machine_id]

        self._machine_type: MachineType = machine.type

        machine_type_str = str(machine.type.value).title()

        self._attr_unique_id = f"{machine_id}_pay"
        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, machine_id)},
        }

        self._attr_name = f"{machine_type_str} {machine.number}: Pay"

        self.update_device_data()

    async def async_press(self) -> None:
        """Handle the button press."""

        await self.laundry.async_vend(self._machine_id)

        await asyncio.sleep(5)

        await self.coordinator.async_refresh()

    @callback  # type: ignore
    def update_device_data(self) -> None:
        """Update the entity when new data comes from the REST API."""
