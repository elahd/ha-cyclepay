"""Binary sensor API entity."""
from __future__ import annotations

import logging

from homeassistant import core
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import Event
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_platform import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pylaundry import Laundry
from pylaundry import LaundryMachine
from pylaundry import LaundryProfile
from pylaundry import MachineType

from .const import DOMAIN
from .const import EVENT_VEND_BEGIN

log = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,  # pylint: disable=unused-argument
) -> None:
    """Set up entities using the binary sensor platform from this config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    #
    # Minutes Remaining Sensor
    #

    coordinator_data: Laundry = coordinator.data
    async_add_entities(
        (
            MachineMinutesRemainingSensor(
                coordinator=coordinator, machine_id=machine.id_, hass=hass
            )
            for machine in coordinator_data.machines.values()
            if isinstance(machine, LaundryMachine)
        ),
        True,
    )

    #
    # Card Balance Sensor
    #

    async_add_entities(
        (
            [
                CardBalanceSensor(
                    coordinator=coordinator,
                    username=entry.data["username"],
                    config_id=entry.entry_id,
                )
            ]
        ),
        True,
    )

    #
    # Available Washers
    #

    async_add_entities(
        (
            AvailableMachines(
                coordinator=coordinator,
                config_id=entry.entry_id,
                machine_type=machine_type,
                time_offset=time_offset,
            )
            for machine_type in MachineType
            if machine_type != MachineType.UNKNOWN
            for time_offset in [0, 15, 30, 45, 60]
        ),
        True,
    )


class MachineMinutesRemainingSensor(SensorEntity, CoordinatorEntity):  # type: ignore
    """Sensor showing whether a machine is in use."""

    # Not using duration class. Formatting is ugly ("17:00" vs "17 min")
    # _attr_device_class = SensorDeviceClass.DURATION
    # _attr_native_unit_of_measurement = homeassistant.const.TIME_MINUTES

    def __init__(
        self, coordinator: DataUpdateCoordinator, machine_id: str, hass: HomeAssistant
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator=coordinator)

        self._machine_id = machine_id

        self.laundry: Laundry = coordinator.data
        self.machine: LaundryMachine = self.laundry.machines[machine_id]

        self._machine_type: MachineType = self.machine.type

        machine_type_str = str(self.machine.type.value).title()

        self._attr_unique_id = (
            f"{self.laundry.profile.user_id}_{machine_id}_minutes_remaining"
        )
        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, machine_id)},
            "name": f"{machine_type_str} {self.machine.number}",
            "suggested_area": "Laundry Room",
        }

        self._attr_extra_state_attributes = {
            "machine_type": machine_type_str,
            "base_price": f"${self.machine.base_price:0,.2f}",
            "running": None,
        }

        self._attr_name = f"{machine_type_str} {self.machine.number}: Minutes Remaining"

        hass.bus.async_listen(EVENT_VEND_BEGIN, self._trigger_vending_state)

        self.update_device_data()

    def update_device_data(self) -> None:
        """Update the entity when coordinator is updated."""

        self._attr_native_unit_of_measurement = "min"

        machine: LaundryMachine = self.laundry.machines.get(self._machine_id)

        if machine.online:
            self._attr_native_value = (
                machine.minutes_remaining if machine.minutes_remaining else 0
            )
        else:
            self._attr_native_value = None

        self._attr_extra_state_attributes.update({"running": machine.busy})

        if self._machine_type in [MachineType.WASHER, MachineType.DRYER]:

            icon_prefix = (
                "washing-machine"
                if self._machine_type == MachineType.WASHER
                else "tumble-dryer"
            )

            if not machine.online:
                self._attr_icon = f"mdi:{icon_prefix}-alert"
            elif self._attr_native_value > 0:
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

    @callback  # type: ignore
    def _trigger_vending_state(self, event: Event) -> None:

        if event.data.get("machine_id") != self._machine_id:
            return None

        self._attr_native_unit_of_measurement = ""
        self._attr_native_value = "Vending"

        self.async_write_ha_state()


class CardBalanceSensor(SensorEntity, CoordinatorEntity):  # type: ignore
    """Sensor showing whether a machine is in use."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"

    def __init__(
        self, coordinator: DataUpdateCoordinator, username: str, config_id: str
    ):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator=coordinator)

        self.laundry: Laundry = coordinator.data

        self._attr_unique_id = (
            f"{self.laundry.profile.user_id}_{username}_laundry_card_balance"
        )

        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, config_id)},
        }

        self._attr_name = "Laundry Card: Balance"

        self.update_device_data()

    def update_device_data(self) -> None:
        """Update the entity when coordinator is updated."""

        profile: LaundryProfile = self.laundry.profile

        self._attr_native_value = (
            0 if not profile.card_balance else profile.card_balance
        )

        self._attr_icon = "mdi:credit-card-chip-outline"

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()

        self.update_device_data()

    @callback  # type: ignore
    def _handle_coordinator_update(self) -> None:
        """Update the entity with new REST API data."""

        self.update_device_data()

        self.async_write_ha_state()


class AvailableMachines(SensorEntity, CoordinatorEntity):  # type: ignore
    """Sensor showing how many machines of a specific type will be available (not in use and online) at the specified time interval."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        machine_type: MachineType,
        config_id: str,
        time_offset: int = 0,
    ):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator=coordinator)

        self.laundry: Laundry = coordinator.data

        self._machine_type = machine_type
        self._time_offset = time_offset

        self._attr_unique_id = self._generate_name(unique_id=True)

        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, machine_type.value)},
        }

        self._attr_name = self._generate_name()

        self.update_device_data()

    def update_device_data(self) -> None:
        """Update the entity when coordinator is updated."""

        machines = self.laundry.machines

        self._attr_native_value = len(
            [
                machine
                for machine in machines.values()
                if isinstance(machine, LaundryMachine)
                and machine.type == self._machine_type
                and machine.minutes_remaining <= self._time_offset
            ]
        )

        icon_prefix = (
            "washing-machine"
            if self._machine_type == MachineType.WASHER
            else "tumble-dryer"
        )

        if self._attr_native_value > 0:
            self._attr_icon = f"mdi:{icon_prefix}"
        else:
            self._attr_icon = f"mdi:{icon_prefix}-off"

        total_machines_in_room = len(
            [
                machines
                for machine in machines.values()
                if isinstance(machine, LaundryMachine)
                and machine.type == self._machine_type
            ]
        )

        self._attr_extra_state_attributes = {
            "as_percent": f"{round((self._attr_native_value / total_machines_in_room) * 100)}%",
            f"total_{self._machine_type.value.lower()}s_in_laundry_room": total_machines_in_room,
        }

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()

        self.update_device_data()

    @callback  # type: ignore
    def _handle_coordinator_update(self) -> None:
        """Update the entity with new REST API data."""

        self.update_device_data()

        self.async_write_ha_state()

    def _generate_name(self, unique_id: bool = False) -> str:
        """Generate a name or unique ID for the entity."""

        time_descriptor = (
            "now" if self._time_offset == 0 else f"in {self._time_offset} min"
        )

        base_return_str = (
            f"{str(self._machine_type.value).lower()}s Available {time_descriptor}"
        )

        if unique_id:
            return f"{self.laundry.profile.user_id}_{base_return_str}_{time_descriptor}".lower().replace(
                " ", "_"
            )

        return (
            base_return_str.title()
            if self._time_offset == 0
            else f"{base_return_str}utes".title()
        )
