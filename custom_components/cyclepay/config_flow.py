"""Config flow for NYC 311 Public Services Calendar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pylaundry import Laundry
from pylaundry.exceptions import (
    AuthenticationError,
    CommunicationError,
    Rejected,
    ResponseFormatError,
)

from .const import DOMAIN, OPT_FULL_LOAD

log = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required("username"): str, vol.Required("password"): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    laundry = Laundry(async_get_clientsession(hass))

    try:
        await laundry.async_login(username=data["username"], password=data["password"])
    except (CommunicationError, ResponseFormatError, Rejected) as err:
        raise CannotConnect from err
    except AuthenticationError as err:
        raise InvalidAuth from err

    log.debug("API authenticated successfully.")

    return {"title": f"{data['username']} on CyclePay"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for NYC 311 Public Services Calendar."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Tell Home Assistant that this integration supports configuration options."""
        return OptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                log.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)


class OptionsFlow(config_entries.OptionsFlow):  # type: ignore
    """Handle options flow for CyclePay."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle sole options flow step."""

        errors: dict = {}

        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    OPT_FULL_LOAD,
                    default=(
                        0
                        if not (full_dryer_load_swipes := self.options.get(OPT_FULL_LOAD))
                        else full_dryer_load_swipes
                    ),
                ): int
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            last_step=True,
        )


class CannotConnect(HomeAssistantError):  # type: ignore
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):  # type: ignore
    """Error to indicate there is invalid auth."""
