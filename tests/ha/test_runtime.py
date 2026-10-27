import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.core import Context as HAContext, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartify_energy import async_setup
from custom_components.smartify_energy.config_flow import HeatPumpSubentryFlow
from custom_components.smartify_energy.devices.base import BaseDevice, Context, Decision
from custom_components.smartify_energy.devices.heatpump import HeatPumpDevice
from custom_components.smartify_energy.manager import EnergyManager
from custom_components.smartify_energy.sensor import SmartifySensor
from custom_components.smartify_energy.helpers import SensorSpec
from custom_components.smartify_energy.diagnostics import async_get_config_entry_diagnostics


def manager(hass):
    entry = MockConfigEntry(domain='smartify_energy', data={'grid_sensor':'sensor.grid'})
    entry.add_to_hass(hass)
    m = EnergyManager(hass, entry)
    entry.runtime_data = m
    return m


async def test_real_manager_reruns_events_during_await(hass):
    m = manager(hass)
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def cycle():
        calls.append(len(calls))
        if len(calls) == 1:
            entered.set()
            await release.wait()
    m._async_run = cycle
    task = asyncio.create_task(m.async_run())
    await entered.wait()
    await m.async_run()
    m._schedule_run(0.5)
    release.set()
    await task
    assert len(calls) == 2
    assert not m._lock.locked()


async def test_manager_actual_budget_distribution(hass):
    m = manager(hass)
    hass.states.async_set('sensor.grid', '3000', {'unit_of_measurement':'W'})
    class Consumer(BaseDevice):
        def is_on(self): return False
        def decide(self, ctx, left):
            self.status = 'bereit'
            return Decision(left >= 2000, 2000 if left >= 2000 else 0)
        async def async_apply(self, decision, ctx): pass
    for n in range(2):
        dev = Consumer(m,str(n),str(n),{'nominal_power':2000})
        dev.params.update(mode='auto',priority=n+1)
        m.devices[str(n)] = dev
    await m.async_run()
    assert m.devices['0'].last_decision.on
    assert not m.devices['1'].last_decision.on
    assert m.allocated == 2000
    assert m.device_budgets['1']['aktuell_w'] == 1000
    await m.async_stop()


async def test_unavailable_guard_and_button_unknown(hass):
    m = manager(hass)
    d = HeatPumpDevice(m,'wp','WP',{'boost_entity':'switch.wp','boost_type':'switch'})
    hass.states.async_set('switch.wp','unavailable')
    ctx = Context(dt_util.now(),30,3000,3000,3000,True,False,3000)
    d.async_apply=AsyncMock()
    await d.async_run(ctx,3000)
    d.async_apply.assert_not_awaited()
    assert d.status == 'actuator_unavailable'
    d.cfg['boost_entity']='button.wp'
    hass.states.async_set('button.wp','unknown')
    assert d._unavailable_actor() is None


async def test_actor_timeout_and_no_success_state(hass):
    m=manager(hass)
    d=HeatPumpDevice(m,'wp','WP',{'boost_entity':'switch.wp','boost_type':'switch'})
    hass.states.async_set('switch.wp','off')
    async def slow(call): await asyncio.sleep(100)
    hass.services.async_register('switch','turn_on',slow)
    timeout=asyncio.timeout
    with patch('custom_components.smartify_energy.devices.base.asyncio.timeout',lambda seconds:timeout(0.01)):
        with pytest.raises(TimeoutError): await d._switch('switch.wp',True)
    assert hass.states.get('switch.wp').state=='off'


async def test_battery_uses_last_positive_forecast_hour(hass):
    m=manager(hass)
    m.has_battery=True
    m.cfg['battery_capacity']=5
    m.params.update(battery_strategy='forecast',battery_min_soc=20,battery_target_soc=100,battery_safety=1,base_load=400)
    m.battery_soc=80
    now=dt_util.now().replace(hour=15,minute=0,second=0,microsecond=0)
    m.forecast.hours={now:1600,now+timedelta(hours=1):0}
    m._battery_strategy(now)
    assert m.battery_devices_first  # 1600 - 400 > 1000 needed, not base load until 21:00


async def test_explicit_input_fields_and_fast_cache(hass):
    m=manager(hass)
    d=HeatPumpDevice(m,'wp','sensor.fake_name',{'boost_entity':'switch.wp','name':'sensor.fake_name','power_sensor':'sensor.power','ww_active_entity':'binary_sensor.ww'})
    m.devices['wp']=d
    assert d.observed_entities()=={'switch.wp','sensor.power','binary_sensor.ww'}
    await m.async_start()
    assert 'sensor.grid' in m._fast_inputs
    await m.async_stop()


async def test_sensor_enum_recorder_and_dedup(hass):
    m=manager(hass)
    d=HeatPumpDevice(m,'wp','WP',{})
    sensor=SmartifySensor(m,d,d.sensor_specs()[0])
    sensor.hass=hass
    sensor.entity_id='sensor.wp_status'
    sensor._attr_translation_key = None
    sensor.async_write_ha_state=AsyncMock() # overwritten below: normal callback is synchronous
    from unittest.mock import Mock
    sensor.async_write_ha_state=Mock()
    sensor._handle_update()
    sensor._handle_update()
    assert sensor.async_write_ha_state.call_count==1
    d.status='wartet'
    sensor._handle_update()
    assert sensor.native_value=='waiting'
    assert sensor.device_class=='enum'
    assert 'waiting' in sensor.options
    assert 'stunden' in SmartifySensor._unrecorded_attributes
    assert 'geraete' in SmartifySensor._unrecorded_attributes


async def test_config_schema_and_cross_field_validation(hass):
    flow=HeatPumpSubentryFlow()
    flow.hass=hass
    schema=flow.schema({})
    data={'name':'WW','boost_type':'switch','boost_entity':'switch.wp','nominal_power':2000,'ww_active_minutes':0}
    assert schema(data)['ww_active_minutes']==0
    assert flow.validate(data)=={}
    assert flow.validate(data|{'boost_type':'number'})
    with pytest.raises(vol.Invalid): schema(data|{'ww_active_minutes':181})


async def test_service_validation_error(hass):
    await async_setup(hass,{})
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call('smartify_energy','set_priority_order',{'device_ids':['x','x']},blocking=True)
    assert err.value.translation_key=='duplicate_device'


async def test_diagnostics_omit_private_identifiers(hass):
    m=manager(hass)
    d=HeatPumpDevice(m,'private-sub-id','Private Name',{'boost_entity':'switch.secret'})
    m.devices[d.id]=d
    d.last_decision=Decision(True,2000,'private detail')
    result=await async_get_config_entry_diagnostics(hass,m.entry)
    text=str(result)
    assert all(word not in text for word in ('Private Name','switch.secret','private-sub-id','private detail'))
    assert result['devices'][0]['decision']['power']==2000

async def test_real_entry_platform_setup_translated_enum(hass, caplog):
    from homeassistant.setup import async_setup_component
    entry=MockConfigEntry(domain='smartify_energy',data={'grid_sensor':'sensor.grid'},
        subentries_data=[{'subentry_id':'hp','subentry_type':'heatpump','title':'Test WP','unique_id':None,
                         'data':{'boost_type':'button','boost_entity':'button.wp'}}])
    entry.add_to_hass(hass)
    hass.states.async_set('button.wp','unknown')
    assert await async_setup_component(hass,'smartify_energy',{})
    await hass.async_block_till_done()
    statuses=[s for s in hass.states.async_all('sensor') if s.attributes.get('device_class')=='enum']
    assert statuses
    assert 'Error adding entity' not in caplog.text
    assert len(hass.states.async_all('sensor')) >= 10
    assert any(s.state=='initializing' for s in statuses)
    assert await hass.config_entries.async_unload(entry.entry_id)

@pytest.mark.parametrize('kind,key', [('load','switch'),('dryer','switch'),('pool','switch'),('heater','switch'),('ev','current_entity'),('heatpump','boost_entity')])
async def test_all_device_types_block_unavailable_actors(hass,kind,key):
    from custom_components.smartify_energy.devices import DEVICE_CLASSES
    m=manager(hass)
    d=DEVICE_CLASSES[kind](m,'d','D',{key:'switch.actor'})
    hass.states.async_set('switch.actor','unavailable')
    d.params['mode']='auto'
    d.async_apply=AsyncMock()
    ctx=Context(dt_util.now(),30,5000,5000,5000,True,False,5000)
    for _ in range(3): await d.async_run(ctx,5000)
    d.async_apply.assert_not_awaited()
    assert d.status=='actuator_unavailable'
    hass.states.async_set('switch.actor','off')
    assert d._unavailable_actor() is None


async def test_failed_actor_keeps_budget_reserved(hass):
    m=manager(hass)
    hass.states.async_set('sensor.grid','3000',{'unit_of_measurement':'W'})
    class Consumer(BaseDevice):
        def is_on(self): return False
        def decide(self,ctx,left): return Decision(left>=2000,2000 if left>=2000 else 0)
        async def async_apply(self,d,ctx):
            if self.id=='first': raise TimeoutError
    for rank,key in enumerate(('first','second')):
        d=Consumer(m,key,key,{'nominal_power':2000})
        d.params.update(mode='auto',priority=rank+1)
        m.devices[key]=d
    await m.async_run()
    assert not m.devices['second'].last_decision.on
    assert m.allocated==2000
    await m.async_stop()


def test_reason_localization_preserves_numeric_details():
    from custom_components.smartify_energy.reasons import localize_reason
    assert localize_reason('WW-Boost-Startsperre: noch 25 min','en')=='Hot-water boost cooldown remaining: 25 min'
    assert localize_reason('Modus: Aus','en')=='Mode: Off'
    assert localize_reason('Modus: Aus','de')=='Modus: Aus'

async def test_hub_config_flow_wizard(hass):
    with patch('custom_components.smartify_energy.config_flow.async_forecast_entry_options',return_value=[]), patch('custom_components.smartify_energy.config_flow.async_default_forecast_entries',return_value=[]), patch('custom_components.smartify_energy.async_setup_entry',return_value=True):
        result=await hass.config_entries.flow.async_init('smartify_energy',context={'source':'user'})
        assert result['step_id']=='user'
        result=await hass.config_entries.flow.async_configure(result['flow_id'],{'name':'Test','grid_sensor':'sensor.grid','grid_sign':'export_positive','interval':30})
        assert result['step_id']=='forecast'
        result=await hass.config_entries.flow.async_configure(result['flow_id'],{})
        assert result['step_id']=='battery'
        result=await hass.config_entries.flow.async_configure(result['flow_id'],{'battery_sign':'charge_positive'})
        assert result['type']=='create_entry'
        assert result['data']['grid_sensor']=='sensor.grid'
