"""Binary sensor API entity."""
from __future__ import annotations

import logging

from homeassistant import core
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
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
    discovery_info: DiscoveryInfoType | None = None,  # pylint: disable=unused-argument
) -> None:
    """Set up entities using the binary sensor platform from this config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    coordinator_data: Laundry = coordinator.data
    async_add_entities(
        (
            MachineInUseSensor(
                coordinator=coordinator,
                machine_id=machine.id_,
            )
            for machine in coordinator_data.machines.values()
            if isinstance(machine, LaundryMachine)
        ),
        True,
    )


class MachineInUseSensor(BinarySensorEntity, CoordinatorEntity):  # type: ignore
    """Sensor showing whether a machine is in use."""

    def __init__(self, coordinator: DataUpdateCoordinator, machine_id: str):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator=coordinator)

        self._attr_entity_registry_visible_default = False

        self._machine_id = machine_id

        self.laundry: Laundry = coordinator.data
        machine: LaundryMachine = self.laundry.machines.get(machine_id)

        self._machine_type: MachineType = machine.type

        machine_type_str = str(machine.type.value).title()

        self._attr_unique_id = f"{self.laundry.profile.user_id}_{machine_id}_running"
        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, machine_id)},
        }

        self._attr_extra_state_attributes = {
            "machine_type": machine_type_str,
            "base_price": f"${machine.base_price:0,.2f}",
        }

        self._attr_name = f"{machine_type_str} {machine.number}: Running"

        self._attr_device_class = BinarySensorDeviceClass.RUNNING

        self.update_device_data()

    def update_device_data(self) -> None:
        """Update the entity when coordinator is updated."""

        machine: LaundryMachine = self.laundry.machines.get(self._machine_id)

        self._attr_is_on = machine.busy if machine.online else None

        self._attr_extra_state_attributes.update(
            {"minutes_remaining": machine.minutes_remaining}
        )

        if self._machine_type in [MachineType.WASHER, MachineType.DRYER]:

            icon_prefix = (
                "washing-machine"
                if self._machine_type == MachineType.WASHER
                else "tumble-dryer"
            )

            if not machine.online:
                self._attr_icon = f"mdi:{icon_prefix}-alert"
            elif self._attr_is_on:
                self._attr_icon = f"mdi:{icon_prefix}"
            else:
                self._attr_icon = f"mdi:{icon_prefix}-off"

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()

        self.update_device_data()

    @callback  # type: ignore
    def _handle_coordinator_update(self) -> None:
        """Update the entity with new REST API data."""

        self.update_device_data()

        self.async_write_ha_state()
