from pathlib import Path

import pytest
import yaml

from settings import EpicSettings


@pytest.mark.parametrize("provider", ["gemini", "glm"])
def test_scheduled_workflow_preserves_exact_model_for_all_roles(provider):
    workflow = yaml.safe_load(
        (Path(__file__).parents[1] / ".github/workflows/epic-gamer.yml").read_text("utf-8")
    )
    step = next(
        step
        for step in workflow["jobs"]["epic-gamer"]["steps"]
        if step["name"] == "Run Epic Awesome Gamer"
    )
    model_fields = (
        "GEMINI_MODEL",
        "GLM_MODEL",
        "CHALLENGE_CLASSIFIER_MODEL",
        "IMAGE_CLASSIFIER_MODEL",
        "SPATIAL_POINT_REASONER_MODEL",
        "SPATIAL_PATH_REASONER_MODEL",
    )
    model_env = {name: step["env"][name] for name in model_fields}
    config = EpicSettings(
        _env_file=None,
        LLM_PROVIDER=provider,
        GEMINI_API_KEY="test-only",
        GLM_API_KEY="test-only",
        **model_env,
    )
    assert config.LLM_PROVIDER == provider
    for name in model_fields:
        assert getattr(config, name) == "gemini-3.8-flash-high"
    assert step["env"]["LLM_PROVIDER"] == "${{ vars.LLM_PROVIDER || secrets.LLM_PROVIDER }}"
    assert step["env"]["GEMINI_BASE_URL"] == "${{ secrets.GEMINI_BASE_URL }}"
    assert step["env"]["GLM_BASE_URL"] == "${{ secrets.GLM_BASE_URL }}"
