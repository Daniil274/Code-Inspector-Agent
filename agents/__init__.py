"""
Агенты системы CodeInspector.
"""

from .master_agent import MasterAgent
from .file_analysis_agent import FileAnalysisAgent  
from .writer_agent import WriterAgent

__all__ = ['MasterAgent', 'FileAnalysisAgent', 'WriterAgent']
