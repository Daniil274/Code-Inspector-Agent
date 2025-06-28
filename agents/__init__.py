"""
Агенты системы CodeInspector.
"""

from .master_agent import MasterAgent
from .file_analysis_agent import FileAnalysisAgent  
from .composer_agent import ComposerAgent

__all__ = ['MasterAgent', 'FileAnalysisAgent', 'ComposerAgent']
