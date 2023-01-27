"""The CyclePay integration."""
from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
from homeassistant.config_entries import ConfigEntry, device_registry as dr
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pylaundry import Laundry, MachineType
from pylaundry.exceptions import (
    AuthenticationError,
    CommunicationError,
    Rejected,
    ResponseFormatError,
)

from .const import DOMAIN, STARTUP_MESSAGE

log = logging.getLogger(__name__)

PLATFORMS: list[str] = ["binary_sensor", "sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CyclePay from a config entry."""

    if DOMAIN not in hass.data:
        # Print startup message
        log.info(STARTUP_MESSAGE)

    #
    # Load data from config entry
    #

    # Load data for domain. If not present, initlaize dict for this domain.
    hass.data.setdefault(DOMAIN, {})

    laundry = Laundry(async_get_clientsession(hass))

    try:
        await laundry.async_login(
            username=entry.data["username"], password=entry.data["password"]
        )
    except (CommunicationError, ResponseFormatError, Rejected) as err:
        raise ConfigEntryNotReady from err
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed("Invalid username or password.") from err

    async def async_update_data() -> Laundry:
        try:
            async with async_timeout.timeout(10):
                await laundry.async_refresh()
                return laundry
        except (CommunicationError, ResponseFormatError, Rejected) as err:
            raise UpdateFailed("Error communicating with API.") from err
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed from err

    coordinator = DataUpdateCoordinator(
        hass,
        log,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=1),
    )

    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Laundry Card",
        suggested_area="Laundry Room",
    )

    for machine_type in [  # pylint: disable=consider-using-tuple
        MachineType.WASHER,
        MachineType.DRYER,
    ]:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, machine_type.value)},
            name=f"{str(machine_type.value).title()}s Available",
            suggested_area="Laundry Room",
        )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return bool(unload_ok)
