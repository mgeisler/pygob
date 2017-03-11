from .loader import Loader


def load(buf):
    """Load and decode a bytes object."""
    loader = Loader()
    return loader.load(buf)
