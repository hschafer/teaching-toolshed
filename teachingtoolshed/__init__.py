import importlib.metadata

__version__ = importlib.metadata.version("teachingtoolshed")

from . import api
from . import gradebook
