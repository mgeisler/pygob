from .loader import Loader


def load(buf):
    """Load and decode a bytes object."""
    loader = Loader()
    return loader.load(buf)


def load_all(buf):
    """Decode all gobs in a bytes object."""
    loader = Loader()
    return loader.load_all(buf)
