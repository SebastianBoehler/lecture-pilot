from lecturepilot.providers import ProviderConfigurationError


class CanvasGenerationRepairableError(ProviderConfigurationError):
    """A deterministic generated-draft failure that can be repaired from source evidence."""
