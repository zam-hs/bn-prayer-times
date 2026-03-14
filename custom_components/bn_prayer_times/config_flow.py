from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol
from datetime import datetime

from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_HIJRI_OFFSET,
    DEFAULT_HIJRI_OFFSET,
    CONF_DISTRICT,
    DEFAULT_DISTRICT,
    DISTRICT_OPTIONS,
)
from .sensor import gregorian_to_hijri, HIJRI_MONTHS


# Dropdown values MUST be strings for HA frontend
HIJRI_OPTIONS = ["-3", "-2", "-1", "0", "1", "2", "3"]


# =====================================================
# CONFIG FLOW
# =====================================================
class BNPrayerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 9

    async def async_step_user(self, user_input=None):

        # allow only one instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        preview = self._preview(DEFAULT_HIJRI_OFFSET)

        if user_input is not None:
            # convert dropdown string → int
            user_input[CONF_HIJRI_OFFSET] = int(
                user_input.get(CONF_HIJRI_OFFSET, 0)
            )

            return self.async_create_entry(
                title="BN Prayer Times",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DISTRICT,
                    default=DEFAULT_DISTRICT,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DISTRICT_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_HIJRI_OFFSET,
                    default=str(DEFAULT_HIJRI_OFFSET),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=HIJRI_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={"today": preview},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return BNPrayerOptionsFlow()

    def _preview(self, offset):
        offset = int(offset)

        today = dt_util.now().date()
        h_day, h_month, h_year = gregorian_to_hijri(
            datetime.combine(today, datetime.min.time())
        )

        h_day = int(h_day + offset)

        return f"{h_day} {HIJRI_MONTHS[h_month-1]} {h_year} AH"


# =====================================================
# OPTIONS FLOW
# =====================================================
class BNPrayerOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):

        entry = self.config_entry

        offset = entry.options.get(
            CONF_HIJRI_OFFSET,
            entry.data.get(CONF_HIJRI_OFFSET, DEFAULT_HIJRI_OFFSET),
        )

        district = entry.options.get(
            CONF_DISTRICT,
            entry.data.get(CONF_DISTRICT, DEFAULT_DISTRICT),
        )

        preview = self._preview(offset)

        if user_input is not None:
            user_input[CONF_HIJRI_OFFSET] = int(
                user_input.get(CONF_HIJRI_OFFSET, 0)
            )

            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
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

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"today": preview},
        )

    def _preview(self, offset):
        offset = int(offset)

        today = dt_util.now().date()
        h_day, h_month, h_year = gregorian_to_hijri(
            datetime.combine(today, datetime.min.time())
        )

        h_day = int(h_day + offset)

        return f"{h_day} {HIJRI_MONTHS[h_month-1]} {h_year} AH"
