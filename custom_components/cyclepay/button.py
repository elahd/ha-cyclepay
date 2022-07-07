"""Implementation of an HA button."""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from homeassistant import core
from homeassistant.components import persistent_notification
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
from pylaundry import MachineOffline
from pylaundry import MachineType

from .const import DOMAIN
from .const import EVENT_VEND_BEGIN
from .const import OPT_FULL_LOAD


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

    # Create vend once buttons
    async_add_entities(
        (
            SwipeOnceButton(
                coordinator=coordinator,
                machine_id=machine.id_,
            )
            for machine in coordinator_data.machines.values()
            if isinstance(machine, LaundryMachine)
        ),
        True,
    )

    # Create base + topoff buttons for dryers
    async_add_entities(
        (
            SwipePreferredCycleButton(
                coordinator=coordinator, machine_id=machine.id_, config_entry=entry
            )
            for machine in coordinator_data.machines.values()
            if isinstance(machine, LaundryMachine) and machine.type == MachineType.DRYER
        ),
        True,
    )


class BaseButton(ButtonEntity, CoordinatorEntity):  # type: ignore
    """Integration button entity shared functions."""

    coordinator: DataUpdateCoordinator
    _attr_icon = "mdi:currency-usd"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        machine_id: str,
        name_suffix: str,
        id_suffix: str,
    ):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator=coordinator)

        self.machine_id = machine_id

        self.laundry: Laundry = coordinator.data
        self.machine: LaundryMachine = self.laundry.machines[machine_id]

        self.machine_type: MachineType = self.machine.type
        machine_type_str = str(self.machine.type.value).title()

        self._attr_unique_id = (
            f"{self.laundry.profile.user_id}_{machine_id}_{id_suffix}"
        )
        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, machine_id)},
        }

        self._attr_name = f"{machine_type_str} {self.machine.number}: {name_suffix}"

    def _show_permission_error(self, msg: str) -> Literal[False]:
        """Show Home Assistant notification to alert user of error."""

        persistent_notification.async_create(
            self.hass,
            msg,
            title="CyclePay Error",
            notification_id="alarmcom_permission_error",
        )

        return False

    def update_device_data(self) -> None:
        """Update device data when coordinator updates. To be implemented by child classes."""

        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()

        self.update_device_data()

    @callback  # type: ignore
    def _handle_coordinator_update(self) -> None:
        """Update the entity with new REST API data."""

        self.update_device_data()

        self.async_write_ha_state()

    async def _can_vend(self, num_swipes: int) -> bool:
        """Determine whether card and machine are able to vend."""

        # Abort if machine is busy and we're being asked to vend a full load.
        # if self.machine.busy and num_swipes > 1:
        #     self._show_permission_error(
        #         f"Cannot vend full cycle for dryer {self.machine.type.name.title()} {self.machine.number} because a cycle is already in progress."
        #     )

        # Fetch topoff data if we don't already have it.
        if not self.machine.topoff_price or not self.machine.base_price:
            try:
                # Use returned instance of topoff data. Update won't be reflected in self.laundry until next coordinator update.
                topoff_data = await self.laundry.async_get_topoff_data(self.machine.id_)
            except MachineOffline:
                return self._show_permission_error(
                    f"Cannot vend {self.machine.type.name.title()} {self.machine.number}. Machine is not connected to CyclePay."
                )

        log.debug(topoff_data)

        # Make sure we received correct values. Topoff data can be unreliable.
        if not isinstance(self.machine.base_price, float) or (
            self.machine.type == MachineType.DRYER
            and (not topoff_data or not isinstance(topoff_data.get("price"), float))
        ):
            return self._show_permission_error(
                f"Cannot determine whether sufficient funds are available to vend {self.machine.type.name.title()} {self.machine.number}."
            )

        # Make sure we're not requesting a topoff of a washer
        if num_swipes > 1 and self.machine.type is not MachineType.DRYER:
            return self._show_permission_error(
                f"Cannot topoff {self.machine.type.name.title()} {self.machine.number} because it is not a dryer."
            )

        # Abort topoff requests for an idle machine.

        if num_swipes > 1 and not self.machine.busy:
            return self._show_permission_error(
                f"Cannot topoff {self.machine.type.name.title()} {self.machine.number} until a cycle has started. Please swipe once and press the start button on the physical machine before topping off."
            )

        # Calculate cost of vend.
        if num_swipes == 1 and self.machine.busy:
            vend_cost = topoff_data.get("price")
        elif num_swipes == 1 and not self.machine.busy:
            vend_cost = self.machine.base_price
        elif num_swipes > 1 and self.machine.busy:
            vend_cost = self.machine.base_price - (
                topoff_data.get("price") * (num_swipes - 1)
            )

        card_balance = (
            0
            if not self.laundry.profile.card_balance
            else self.laundry.profile.card_balance
        )

        # Check if card has sufficient funds.
        if card_balance - vend_cost < 0:
            return self._show_permission_error(
                f"Card balance of ${card_balance:.2f} is insufficient for the requested ${vend_cost:.2f} payment. Please add funds to your virtual card using the CyclePay app."
            )

        return True


class SwipeOnceButton(BaseButton):
    """Integration button entity for swiping virtual card through machine a single time."""

    def __init__(self, coordinator: DataUpdateCoordinator, machine_id: str):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(
            coordinator=coordinator,
            machine_id=machine_id,
            name_suffix="Swipe Card Once",
            id_suffix="single_swipe",
        )

    def update_device_data(self) -> None:
        """Update device data when coordinator updates."""

        if self.machine.busy is True and self.machine.type == MachineType.WASHER:
            self._attr_available = False

        self._attr_available = True

    async def async_press(self) -> None:
        """Handle the button press."""

        self._attr_available = False
        self.hass.bus.async_fire(EVENT_VEND_BEGIN, {"machine_id": self.machine_id})

        if not await self._can_vend(num_swipes=1):
            self._attr_available = True
            return None

        await self.laundry.async_vend(self.machine_id)

        await asyncio.sleep(5)

        await self.coordinator.async_refresh()


class SwipePreferredCycleButton(BaseButton):
    """Integration button entity for fully loading a dryer cycle."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        machine_id: str,
        config_entry: ConfigEntry,
    ):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(
            coordinator=coordinator,
            machine_id=machine_id,
            name_suffix="Preferred Cycle Topoff",
            id_suffix="multi_swipe",
        )

        self._config_entry = config_entry

    def update_device_data(self) -> None:
        """Update device data when coordinator updates."""

        if not self.machine.busy:
            self._attr_available = False

        self._attr_available = True

    async def async_press(self) -> None:
        """Handle the button press."""

        num_swipes: int = self._config_entry.options.get(OPT_FULL_LOAD, 0)

        if num_swipes == 0:
            self._show_permission_error(
                f"Cannot topoff {self.machine.type.name.title()} {self.machine.number} because you have not yet configured your preferred cycle. Configure your preferred cycle in the CyclePay integration's settings."
            )
            return None

        self._attr_available = False

        self.hass.bus.async_fire(EVENT_VEND_BEGIN, {"machine_id": self.machine_id})

        if not await self._can_vend(num_swipes=num_swipes):
            self._attr_available = True
            return None

        i = 0
        while i <= num_swipes:

            # Ensures that the machine state doesn't update while we're vending.
            self.hass.bus.async_fire(EVENT_VEND_BEGIN, {"machine_id": self.machine_id})

            await self.laundry.async_vend(self.machine_id)
            i += 1

        await asyncio.sleep(5)

        await self.coordinator.async_refresh()
