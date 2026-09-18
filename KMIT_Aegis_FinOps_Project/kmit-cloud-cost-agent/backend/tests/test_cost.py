from backend.app.simulator import CloudSimulator

def test_cost_model_changes_with_scale():
    sim=CloudSimulator(); before=sim.service('orders-api')['cost_per_hour']
    result=sim.execute('orders-api','scale_up',target_instances=8)
    assert result['status']=='success'
    after=sim.service('orders-api')['cost_per_hour']
    assert after>before
