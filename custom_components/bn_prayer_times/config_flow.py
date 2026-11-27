"""Config flow for BN Prayer Times."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DISTRICT,
    CONF_HIJRI_OFFSET,
    DEFAULT_DISTRICT,
    DEFAULT_HIJRI_OFFSET,
    DISTRICT_OPTIONS,
    DOMAIN,
)
from .hijri import format_hijri

# Dropdown values MUST be strings for HA frontend
HIJRI_OPTIONS = ["-3", "-2", "-1", "0", "1", "2", "3"]


def _schema(district, offset) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_DISTRICT,
                default=district,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=DISTRICT_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_HIJRI_OFFSET,
                default=str(offset),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=HIJRI_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _preview(offset) -> str:
    return format_hijri(dt_util.now().date(), int(offset))


# =====================================================
# CONFIG FLOW
# =====================================================
class BNPrayerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 9

    async def async_step_user(self, user_input=None):

        # allow only one instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # convert dropdown string → int
            user_input[CONF_HIJRI_OFFSET] = int(
                user_input.get(CONF_HIJRI_OFFSET, 0)
            )

            return self.async_create_entry(
                title="BN Prayer Times",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(DEFAULT_DISTRICT, DEFAULT_HIJRI_OFFSET),
            description_placeholders={
                "today": _preview(DEFAULT_HIJRI_OFFSET)
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BNPrayerOptionsFlow()


# =====================================================
# OPTIONS FLOW
# =====================================================
class BNPrayerOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):

        entry = self.config_entry

        if user_input is not None:
            user_input[CONF_HIJRI_OFFSET] = int(
                user_input.get(CONF_HIJRI_OFFSET, 0)
            )

            return self.async_create_entry(title="", data=user_input)

        offset = entry.options.get(
            CONF_HIJRI_OFFSET,
            entry.data.get(CONF_HIJRI_OFFSET, DEFAULT_HIJRI_OFFSET),
        )

        district = entry.options.get(
            CONF_DISTRICT,
            entry.data.get(CONF_DISTRICT, DEFAULT_DISTRICT),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(district, offset),
            description_placeholders={"today": _preview(offset)},
        )
