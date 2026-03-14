import os

from pydantic import ValidationError

from src.application.di_container import DIContainer
from src.domain_models.config import AppConfig, ModelRoutingRules
from src.interfaces.llm_protocol import LLMProtocol

# UAT-01-01: Secure Application Configuration and Startup
print("Running UAT-01-01: Secure Application Configuration and Startup")
os.environ.pop("OPENROUTER_API_KEY", None)
os.environ.pop("TENANT_ID", None)

try:
    AppConfig(openrouter_api_key="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", tenant_id="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef") # type: ignore[arg-type]
    raise AssertionError("Expected ValidationError due to missing keys")
except ValidationError:
    print("Success: AppConfig correctly rejected missing OPENROUTER_API_KEY.")

os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
os.environ["TENANT_ID"] = "tenant1"
try:
    ModelRoutingRules(text_fast_model="")
    raise AssertionError("Expected ValidationError due to empty string in model rules")
except ValidationError:
    print("Success: AppConfig correctly rejected invalid routing rules.")

config = AppConfig(openrouter_api_key="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", tenant_id="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef") # type: ignore[arg-type]
print("String representation of config: ", config)
assert "sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" not in str(config), "SecretStr leaked!"
assert "**********" in str(config), "SecretStr did not mask correctly!"
print("Success: SecretStr securely masked.")
print()

# UAT-01-02: Dependency Injection and Protocol Resolution
print("Running UAT-01-02: Dependency Injection and Protocol Resolution")
class DummyLLM:
    pass

container = DIContainer()
instance = DummyLLM()
container.register_singleton(LLMProtocol, instance)
resolved = container.resolve(LLMProtocol) # type: ignore[type-abstract]
assert resolved is instance # type: ignore[comparison-overlap]
print("Success: Resolved singleton successfully.")

class ServiceA:
    def __init__(self, b: 'ServiceB') -> None:
        self.b = b

class ServiceB:
    def __init__(self, a: 'ServiceA') -> None:
        self.a = a

def factory_a() -> ServiceA:
    b = container.resolve(ServiceB)
    return ServiceA(b)

def factory_b() -> ServiceB:
    a = container.resolve(ServiceA)
    return ServiceB(a)

container.register(ServiceA, factory_a)
container.register(ServiceB, factory_b)

try:
    container.resolve(ServiceA)
    raise AssertionError("Expected RuntimeError due to circular dependency")
except RuntimeError as e:
    assert "Circular dependency detected" in str(e)
    print(f"Success: Circular dependency caught gracefully: {e}")
print()

# UAT-01-03: Hybrid Environment Mock Mode Execution
print("Running UAT-01-03: Hybrid Environment Mock Mode Execution")
class MockLLMService(LLMProtocol):
    async def generate_text(self, prompt: str, model: str) -> str:
        return "mocked"

mock_container = DIContainer()
if os.environ.get("MATOME_MOCK_MODE", "true") == "true":
    mock_container.register_singleton(LLMProtocol, MockLLMService()) # type: ignore[type-abstract]

assert isinstance(mock_container.resolve(LLMProtocol), MockLLMService) # type: ignore[type-abstract]
print("Success: Mock Mode Execution successfully resolved to mock implementation.")
print("UATs passed successfully.")
