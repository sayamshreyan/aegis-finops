from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from .agent import MockAgent, AnthropicAgent, OpenAIAgent
from .config import settings
from .models import AgentRunResponse

class AgentOrchestrator:
    def __init__(self, tools, audit, db):
        self.tools=tools; self.audit=audit; self.db=db
        self.provider_name=self._provider_name()
        if self.provider_name=='anthropic' and settings.anthropic_api_key:
            self.agent=AnthropicAgent(tools,audit,settings.anthropic_api_key,settings.anthropic_model)
        elif self.provider_name=='openai' and settings.openai_api_key:
            self.agent=OpenAIAgent(tools,audit,settings.openai_api_key,settings.openai_model)
        else:
            self.provider_name='mock'
            self.agent=MockAgent(tools,audit)

    def _provider_name(self): return settings.provider

    def run(self,prompt,scenario_id=None):
        run_id='run-'+uuid4().hex[:10]
        self.audit.run_id=run_id
        self.db.save_run(run_id,self.provider_name,prompt,'RUNNING','',self._now())
        self.db.log_event(run_id,'request_received',{'prompt':prompt,'scenario_id':scenario_id},self._now())
        if scenario_id:
            self.tools.sim.reset_scenario(scenario_id)
            self.db.log_event(run_id,'scenario_loaded',{'scenario_id':scenario_id},self._now())
        try:
            result=self.agent.run(prompt,scenario_id)
            proposal=result['proposal']
            self.db.log_event(run_id,'agent_proposal',proposal.model_dump(mode='json'),self._now())
            # Deterministic safety is always run on the proposal.
            safety=self.audit.safety.validate(proposal)
            self.db.log_event(run_id,'final_safety',safety.model_dump(mode='json'),self._now())
            execution=None; verification=None
            if proposal.action.value != 'no_action':
                # Execute through the same controlled audit path; this reruns safety before mutation.
                kwargs={}
                if proposal.requested_instances is not None: kwargs['target_instances']=proposal.requested_instances
                if proposal.requested_size is not None: kwargs['target_size']=proposal.requested_size
                raw=self.audit.execute_action(proposal.service_id,proposal.action.value,**kwargs)
                if raw.get('execution'): execution=self.audit.last_execution
                verification=self.audit.last_verification
            summary=result.get('summary','')
            self.db.save_run(run_id,self.provider_name,'', 'COMPLETED',summary,self._now())
            response=AgentRunResponse(run_id=run_id,provider=self.provider_name,summary=summary,proposal=proposal,safety=safety,execution=execution,verification=verification,tool_trace=result.get('trace',[]))
            return response
        except Exception as e:
            self.db.save_run(run_id,self.provider_name,'','FAILED',str(e),self._now())
            self.db.log_event(run_id,'agent_error',{'error':str(e)},self._now())
            raise
    def _now(self): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
