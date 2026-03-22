import importlib.util
from pathlib import Path
import sys
import types


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

fake_claw_service = types.ModuleType("src.services.claw")
fake_claw_service.__path__ = [str(BACKEND_ROOT / "src" / "services" / "claw")]
sys.modules["src.services.claw"] = fake_claw_service

PROMPT_REGISTRY_MODULE_PATH = BACKEND_ROOT / "src" / "services" / "claw" / "prompt_registry.py"
PROMPT_REGISTRY_MODULE_NAME = "src.services.claw.prompt_registry_bootstrap_test"
prompt_registry_spec = importlib.util.spec_from_file_location(
    PROMPT_REGISTRY_MODULE_NAME,
    PROMPT_REGISTRY_MODULE_PATH,
)
prompt_registry = importlib.util.module_from_spec(prompt_registry_spec)
sys.modules[PROMPT_REGISTRY_MODULE_NAME] = prompt_registry
assert prompt_registry_spec.loader is not None
prompt_registry_spec.loader.exec_module(prompt_registry)


def test_prompt_registry_bootstraps_local_deepagents_paths():
    prompt_definitions = prompt_registry.get_prompt_definition_map()

    assert prompt_registry.SYSTEM_PROMPT_ID in prompt_definitions
    assert prompt_registry.MEMORY_SYSTEM_PROMPT_ID in prompt_definitions
    assert prompt_registry.SKILLS_SYSTEM_PROMPT_ID in prompt_definitions
    assert prompt_definitions[prompt_registry.MEMORY_SYSTEM_PROMPT_ID].default_content
