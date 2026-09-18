from backend.app.main import agent, sim

def test_scenario_a():
    r=agent.run('Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.','scenario_a_cost_optimization')
    assert r.proposal.service_id=='reports-worker'
    assert r.proposal.action.value in ('stop_idle_service','scale_down')

def test_scenario_b():
    r=agent.run('Orders traffic is increasing. Keep the service within its latency target.','scenario_b_rising_traffic')
    assert r.proposal.service_id=='orders-api'
    assert r.proposal.action.value=='scale_up'
    assert r.proposal.requested_instances==5

def test_scenario_c():
    r=agent.run('Reduce cost if it is safe.','scenario_c_stale_observation')
    assert r.proposal.service_id=='checkout-api'
    assert r.proposal.requires_fresh_check is True
    assert r.proposal.action.value=='no_action'

def test_scenario_d():
    r=agent.run('Scale the payment service only if the current state requires it.','scenario_d_failed_action')
    assert r.proposal.service_id=='payment-api'
    assert r.proposal.action.value=='scale_up'
    assert r.execution is not None
    assert r.execution.status.value=='FAILED'
    assert r.execution.error=='capacity_unavailable'
    assert r.verification is not None
    assert r.verification.verified is False
