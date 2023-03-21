import importlib.metadata

__version__ = importlib.metadata.version("teaching-toolshed")

from . import api
from . import gradebook
