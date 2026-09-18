from backend.app.simulator import CloudSimulator
from backend.app.safety import SafetyEngine
from backend.app.models import ActionProposal, ActionType

def test_stale_observation_blocks_scale_down():
    sim=CloudSimulator(); sim.reset_scenario('scenario_c_stale_observation')
    s=SafetyEngine(sim)
    p=ActionProposal(service_id='checkout-api',action=ActionType.scale_down,requested_instances=4)
    d=s.validate(p)
    assert not d.allowed
    assert d.reason_code=='stale_observation'

def test_min_capacity_blocks():
    sim=CloudSimulator(); s=SafetyEngine(sim)
    p=ActionProposal(service_id='reports-worker',action=ActionType.scale_down,requested_instances=0)
    d=s.validate(p)
    assert not d.allowed and d.reason_code=='below_min_capacity'

def test_health_blocks():
    sim=CloudSimulator(); sim.state['services']['orders-api']['healthy']=False
    s=SafetyEngine(sim)
    p=ActionProposal(service_id='orders-api',action=ActionType.scale_up,requested_instances=7)
    d=s.validate(p)
    assert not d.allowed and d.reason_code=='unhealthy_service'
