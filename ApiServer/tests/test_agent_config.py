from __future__ import annotations

from api_server.engine.config_loader import load_default_pipeline_definition


def test_default_pipeline_stage_agents_exist() -> None:
    definition = load_default_pipeline_definition()

    agent_ids = {agent.id for agent in definition.agents}
    assert len(agent_ids) == len(definition.agents)

    for stage in definition.stages:
        assert stage.agent_ids
        for agent_id in stage.agent_ids:
            assert agent_id in agent_ids


def test_default_agents_have_required_fields() -> None:
    definition = load_default_pipeline_definition()

    for agent in definition.agents:
        assert agent.role
        assert agent.system_prompt
        assert isinstance(agent.accepted_input_artifact_types, list)
        assert agent.output_artifact_contract is not None
        assert isinstance(agent.context_paths, list)
