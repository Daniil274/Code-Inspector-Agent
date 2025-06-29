class ConsoleSpanExporter:
    pass

class BatchTraceProcessor:
    def __init__(self, exporter=None, max_batch_size=1, schedule_delay=1.0):
        self.exporter = exporter
