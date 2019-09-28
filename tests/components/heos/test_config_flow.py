"""Tests for the Heos config flow module."""
from pyheos import HeosError

from homeassistant import data_entry_flow
from homeassistant.components.heos.config_flow import HeosFlowHandler
from homeassistant.components.heos.const import DATA_DISCOVERED_HOSTS, DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME


async def test_flow_aborts_already_setup(hass, config_entry):
    """Test flow aborts when entry already setup."""
    config_entry.add_to_hass(hass)
    flow = HeosFlowHandler()
    flow.hass = hass
    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_setup"


async def test_no_host_shows_form(hass):
    """Test form is shown when host not provided."""
    flow = HeosFlowHandler()
    flow.hass = hass
    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_cannot_connect_shows_error_form(hass, controller):
    """Test form is shown with error when cannot connect."""
    flow = HeosFlowHandler()
    flow.hass = hass
    controller.connect.side_effect = HeosError()
    result = await flow.async_step_user({CONF_HOST: "127.0.0.1"})
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"][CONF_HOST] == "connection_failure"
    assert controller.connect.call_count == 1
    assert controller.disconnect.call_count == 1
    controller.connect.reset_mock()
    controller.disconnect.reset_mock()


async def test_create_entry_when_host_valid(hass, controller):
    """Test result type is create entry when host is valid."""
    flow = HeosFlowHandler()
    flow.hass = hass
    data = {CONF_HOST: "127.0.0.1"}
    result = await flow.async_step_user(data)
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "Controller (127.0.0.1)"
    assert result["data"] == data
    assert controller.connect.call_count == 1
    assert controller.disconnect.call_count == 1


async def test_create_entry_when_friendly_name_valid(hass, controller):
    """Test result type is create entry when friendly name is valid."""
    hass.data[DATA_DISCOVERED_HOSTS] = {"Office (127.0.0.1)": "127.0.0.1"}
    flow = HeosFlowHandler()
    flow.hass = hass
    data = {CONF_HOST: "Office (127.0.0.1)"}
    result = await flow.async_step_user(data)
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "Controller (127.0.0.1)"
    assert result["data"] == {CONF_HOST: "127.0.0.1"}
    assert controller.connect.call_count == 1
    assert controller.disconnect.call_count == 1
    assert DATA_DISCOVERED_HOSTS not in hass.data


async def test_discovery_shows_create_form(hass, controller, discovery_data):
    """Test discovery shows form to confirm setup and subsequent abort."""
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=discovery_data
    )
    await hass.async_block_till_done()
    assert len(hass.config_entries.flow.async_progress()) == 1
    assert hass.data[DATA_DISCOVERED_HOSTS] == {"Office (127.0.0.1)": "127.0.0.1"}

    discovery_data[CONF_HOST] = "127.0.0.2"
    discovery_data[CONF_NAME] = "Bedroom"
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=discovery_data
    )
    await hass.async_block_till_done()
    assert len(hass.config_entries.flow.async_progress()) == 1
    assert hass.data[DATA_DISCOVERED_HOSTS] == {
        "Office (127.0.0.1)": "127.0.0.1",
        "Bedroom (127.0.0.2)": "127.0.0.2",
    }


async def test_disovery_flow_aborts_already_setup(
    hass, controller, discovery_data, config_entry
):
    """Test discovery flow aborts when entry already setup."""
    config_entry.add_to_hass(hass)
    flow = HeosFlowHandler()
    flow.hass = hass
    result = await flow.async_step_ssdp(discovery_data)
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_setup"
