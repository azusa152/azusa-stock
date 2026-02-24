"""application.settings sub-package — re-exports public API for backward compatibility."""

from application.settings.preferences_service import (  # noqa: F401
    get_preferences,
    update_preferences,
)
from application.settings.persona_service import (  # noqa: F401
    create_profile,
    deactivate_profile,
    get_active_profile,
    list_templates,
    update_profile,
)
