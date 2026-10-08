"""Runtime settings assembled from independent configuration modules."""
from .environment import environment_layer
from .merge import merge_layers
from .validation import validate_port, validate_timeout

def load_settings(defaults, file_values, environ):
    """Build validated runtime settings from defaults, file and environment."""
    values = merge_layers(defaults, file_values, environment_layer(environ))
    values["port"] = validate_port(values["port"])
    values["timeout"] = validate_timeout(values["timeout"])
    return values
