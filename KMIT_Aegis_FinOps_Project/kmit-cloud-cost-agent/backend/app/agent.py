from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
import json
import os
import httpx
from .models import ActionProposal, ActionType

SYSTEM_PROMPT = """You are the autonomous decision layer of Aegis FinOps, a simulated cloud-operations cost optimization system. You must investigate using provided tools and then propose one safe action or no_action. You never bypass deterministic safety. Use concise, auditable summaries rather than hidden chain-of-thought. Return final JSON with: summary, proposal {service_id, action, requested_instances, requested_size, reason, evidence, requires_fresh_check}."""

TOOL_SCHEMAS=[
 {"name":"get_all_services","description":"List all current simulated services.","input_schema":{"type":"object","properties":{}}},
 {"name":"get_service","description":"Get full service state.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_service_metrics","description":"Get current service metrics.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_service_traffic","description":"Get latest traffic and trend for a service.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_recent_events","description":"Get recent events for a service.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_pricing","description":"Get current pricing information.","input_schema":{"type":"object","properties":{}}},
 {"name":"get_service_health","description":"Get health and availability.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_current_service_state","description":"Get current full service state.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_fresh_service_state","description":"Fetch a fresh service snapshot before a risky decision.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"calculate_cost_impact","description":"Calculate deterministic current daily/monthly cost for a service.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}}
]


class MockAgent:
    def __init__(self, tools, audit): self.tools=tools; self.audit=audit
    def run(self, prompt: str, scenario_id: str|None=None):
        trace=[]
        services=self.tools.call('get_all_services',{}); trace.append({'tool':'get_all_services','args':{},'result':services})
        p=prompt.lower()
        selected=None; action='no_action'; target=None; reason='Insufficient evidence for a safe action.'; evidence=[]; requires_fresh=False
        if 'payment' in p:
            selected=self.tools.call('get_service',{'service_id':'payment-api'}); trace.append({'tool':'get_service','args':{'service_id':'payment-api'},'result':selected})
            traffic=self.tools.call('get_service_traffic',{'service_id':'payment-api'}); trace.append({'tool':'get_service_traffic','args':{'service_id':'payment-api'},'result':traffic})
            if selected['latency_ms']>selected['max_latency_ms'] or selected['cpu_percent']>=80:
                action='scale_up'; target=min(selected['instances']+2,selected['max_instances']); reason='High CPU, memory and latency indicate insufficient capacity.'; evidence=[f"cpu={selected['cpu_percent']}%",f"latency={selected['latency_ms']}ms",f"requests/min={selected['requests_per_minute']}"]
        elif 'stale' in p or 'checkout' in p or 'reduce cost' in p:
            selected=self.tools.call('get_service',{'service_id':'checkout-api'}); trace.append({'tool':'get_service','args':{'service_id':'checkout-api'},'result':selected})
            traffic=self.tools.call('get_service_traffic',{'service_id':'checkout-api'}); trace.append({'tool':'get_service_traffic','args':{'service_id':'checkout-api'},'result':traffic})
            if traffic['timestamp']>selected['timestamp']:
                selected=self.tools.call('get_fresh_service_state',{'service_id':'checkout-api'}); trace.append({'tool':'get_fresh_service_state','args':{'service_id':'checkout-api'},'result':selected})
                requires_fresh=True; reason='The service snapshot was stale versus newer traffic, so a fresh state was required before optimization.'; evidence=[f"old_timestamp={self.tools.sim.service('checkout-api')['timestamp']}",f"latest_traffic={traffic['requests_per_minute']}/min",f"fresh_timestamp={selected['timestamp']}"]
                action='no_action'
        elif 'orders' in p or 'traffic' in p:
            selected=self.tools.call('get_service',{'service_id':'orders-api'}); trace.append({'tool':'get_service','args':{'service_id':'orders-api'},'result':selected})
            traffic=self.tools.call('get_service_traffic',{'service_id':'orders-api'}); trace.append({'tool':'get_service_traffic','args':{'service_id':'orders-api'},'result':traffic})
            prev=traffic.get('previous_requests_per_minute') or selected.get('previous_requests_per_minute') or 0
            rising=traffic['requests_per_minute']>prev*1.5 if prev else False
            if rising and selected['latency_ms']>selected['max_latency_ms']*0.8:
                action='scale_up'; target=min(selected['instances']+1,selected['max_instances']); reason='Traffic doubled while latency is near the service target; adding one instance preserves headroom.'; evidence=[f"traffic={traffic['requests_per_minute']}/min",f"previous={prev}/min",f"latency={selected['latency_ms']}ms/{selected['max_latency_ms']}ms"]
        else:
            # General cost optimization: inspect candidate services and pick evidence-based idle worker.
            for s in services:
                if s['requests_per_minute']==0 and s.get('stoppable_when_idle'):
                    selected=s
                    ev=self.tools.call('get_recent_events',{'service_id':s['service_id']}); trace.append({'tool':'get_recent_events','args':{'service_id':s['service_id']},'result':ev})
                    action='stop_idle_service'; reason='The worker is idle, healthy, available and explicitly marked stoppable when idle.'; evidence=["requests_per_minute=0",f"instances={s['instances']}","healthy=true"]
                    break
        proposal=ActionProposal(service_id=selected['service_id'] if selected else 'none',action=action,requested_instances=target,reason=reason,evidence=evidence,requires_fresh_check=requires_fresh)
        return {'summary':reason,'proposal':proposal,'trace':trace}

class AnthropicAgent:
    def __init__(self, tools, audit, api_key, model): self.tools=tools; self.audit=audit; self.api_key=api_key; self.model=model
    def run(self, prompt: str, scenario_id: str|None=None):
        messages=[{'role':'user','content':prompt}]
        trace=[]
        headers={'x-api-key':self.api_key,'anthropic-version':'2023-06-01','content-type':'application/json'}
        for _ in range(8):
            payload={'model':self.model,'max_tokens':1800,'system':SYSTEM_PROMPT,'messages':messages,'tools':TOOL_SCHEMAS}
            with httpx.Client(timeout=60) as client:
                r=client.post('https://api.anthropic.com/v1/messages',headers=headers,json=payload)
                r.raise_for_status(); data=r.json()
            content=data.get('content',[])
            tool_uses=[b for b in content if b.get('type')=='tool_use']
            if tool_uses:
                messages.append({'role':'assistant','content':content})
                results=[]
                for u in tool_uses:
                    name=u['name']; args=u.get('input',{})
                    try:
                        result=self.tools.call(name,args)
                    except Exception as e:
                        result={'error':str(e)}
                    trace.append({'tool':name,'args':args,'result':result})
                    results.append({'type':'tool_result','tool_use_id':u['id'],'content':json.dumps(result,default=str)})
                messages.append({'role':'user','content':results})
                continue
            text=''.join((b.get('text') or '') for b in content if b.get('type')=='text').strip()
            try:
                obj=json.loads(text)
                proposal=ActionProposal.model_validate(obj['proposal'])
                return {'summary':obj.get('summary',''),'proposal':proposal,'trace':trace}
            except Exception as e:
                messages.append({'role':'user','content':f"Your final answer must be valid JSON only. Error: {e}"})
        raise RuntimeError('Anthropic agent did not return a valid structured proposal')

TOOL_SCHEMAS=[
 {"name":"get_all_services","description":"List all current simulated services.","input_schema":{"type":"object","properties":{}}},
 {"name":"get_service","description":"Get full service state.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_service_metrics","description":"Get current service metrics.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_service_traffic","description":"Get latest traffic and trend for a service.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_recent_events","description":"Get recent events for a service.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_pricing","description":"Get current pricing information.","input_schema":{"type":"object","properties":{}}},
 {"name":"get_service_health","description":"Get health and availability.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_current_service_state","description":"Get current full service state.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"get_fresh_service_state","description":"Fetch a fresh service snapshot before a risky decision.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}},
 {"name":"calculate_cost_impact","description":"Calculate deterministic current daily/monthly cost for a service.","input_schema":{"type":"object","properties":{"service_id":{"type":"string"}},"required":["service_id"]}}
]

class OpenAIAgent:
    def __init__(self, tools, audit, api_key, model):
        self.tools=tools; self.audit=audit; self.api_key=api_key; self.model=model

    def run(self, prompt: str, scenario_id: str|None=None):
        messages=[{"role":"user","content":prompt}]
        trace=[]
        headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"}
        function_tools=[{"type":"function","name":t["name"],"description":t["description"],"parameters":t["input_schema"]} for t in TOOL_SCHEMAS]
        for _ in range(8):
            payload={"model":self.model,"instructions":SYSTEM_PROMPT,"input":messages,"tools":function_tools}
            with httpx.Client(timeout=60) as client:
                r=client.post("https://api.openai.com/v1/responses",headers=headers,json=payload)
                r.raise_for_status(); data=r.json()
            output=data.get("output",[])
            calls=[item for item in output if item.get("type")=="function_call"]
            if calls:
                messages.extend(output)
                for call in calls:
                    name=call["name"]
                    args=json.loads(call.get("arguments","{}"))
                    try:
                        result=self.tools.call(name,args)
                    except Exception as e:
                        result={"error":str(e)}
                    trace.append({"tool":name,"args":args,"result":result})
                    messages.append({"type":"function_call_output","call_id":call["call_id"],"output":json.dumps(result,default=str)})
                continue
            text_parts=[]
            for item in output:
                if item.get("type")=="message":
                    for content in item.get("content",[]):
                        if content.get("type") in ("output_text","text"):
                            text_parts.append(content.get("text", ""))
            text="".join(text_parts).strip()
            try:
                obj=json.loads(text)
                proposal=ActionProposal.model_validate(obj["proposal"])
                return {"summary":obj.get("summary",""),"proposal":proposal,"trace":trace}
            except Exception as e:
                messages.append({"role":"user","content":f"Return valid JSON only with a proposal object. Error: {e}"})
        raise RuntimeError("OpenAI agent did not return a valid structured proposal")
