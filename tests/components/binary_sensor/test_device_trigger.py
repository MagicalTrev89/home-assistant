"""The test for binary_sensor device automation."""
import pytest

from homeassistant.components.binary_sensor import DOMAIN, DEVICE_CLASSES
from homeassistant.components.binary_sensor.device_trigger import ENTITY_TRIGGERS
from homeassistant.const import STATE_ON, STATE_OFF, CONF_PLATFORM
from homeassistant.setup import async_setup_component
import homeassistant.components.automation as automation
from homeassistant.helpers import device_registry

from tests.common import (
    MockConfigEntry,
    async_mock_service,
    mock_device_registry,
    mock_registry,
    async_get_device_automations,
)


@pytest.fixture
def device_reg(hass):
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


@pytest.fixture
def entity_reg(hass):
    """Return an empty, loaded, registry."""
    return mock_registry(hass)


@pytest.fixture
def calls(hass):
    """Track calls to a mock serivce."""
    return async_mock_service(hass, "test", "automation")


async def test_get_triggers(hass, device_reg, entity_reg):
    """Test we get the expected triggers from a binary_sensor."""
    platform = getattr(hass.components, f"test.{DOMAIN}")
    platform.init()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_hass(hass)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    for device_class in DEVICE_CLASSES:
        entity_reg.async_get_or_create(
            DOMAIN,
            "test",
            platform.ENTITIES[device_class].unique_id,
            device_id=device_entry.id,
        )

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger["type"],
            "device_id": device_entry.id,
            "entity_id": platform.ENTITIES[device_class].entity_id,
        }
        for device_class in DEVICE_CLASSES
        for trigger in ENTITY_TRIGGERS[device_class]
    ]
    triggers = await async_get_device_automations(hass, "trigger", device_entry.id)
    assert triggers == expected_triggers


async def test_if_fires_on_state_change(hass, calls):
    """Test for on and off triggers firing."""
    platform = getattr(hass.components, f"test.{DOMAIN}")
    platform.init()
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    sensor1 = platform.ENTITIES["battery"]

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": sensor1.entity_id,
                        "type": "bat_low",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "bat_low {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                (
                                    "platform",
                                    "entity_id",
                                    "from_state.state",
                                    "to_state.state",
                                    "for",
                                )
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": sensor1.entity_id,
                        "type": "not_bat_low",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "not_bat_low {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                (
                                    "platform",
                                    "entity_id",
                                    "from_state.state",
                                    "to_state.state",
                                    "for",
                                )
                            )
                        },
                    },
                },
            ]
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(sensor1.entity_id).state == STATE_ON
    assert len(calls) == 0

    hass.states.async_set(sensor1.entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data["some"] == "not_bat_low device - {} - on - off - None".format(
        sensor1.entity_id
    )

    hass.states.async_set(sensor1.entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert len(calls) == 2
    assert calls[1].data["some"] == "bat_low device - {} - off - on - None".format(
        sensor1.entity_id
    )
