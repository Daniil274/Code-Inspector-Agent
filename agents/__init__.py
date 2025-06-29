"""
Агенты системы CodeInspector.
"""

from .master_agent import MasterAgent
from .file_analysis_agent import FileAnalysisAgent
from .composer_agent import ComposerAgent
from .reader_agent import ReaderAgent
from .processor_agent import ProcessorAgent

__all__ = [
    'MasterAgent',
    'FileAnalysisAgent',
    'ComposerAgent',
    'ReaderAgent',
    'ProcessorAgent',
]
