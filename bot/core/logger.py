import logging as _logging

from colorlog import ColoredFormatter as _ColoredFormatter

__all__: (
    "XynusLogger"
)

class XynusLogger(_logging.Logger):
    def __init__(self, name):
        super().__init__(name)
        self.setLevel(_logging.INFO)

        self.formatter = _ColoredFormatter(
            '\033[90m[%(asctime)s]%(reset)s | \033[35m%(name)s%(reset)s | %(log_color)s%(levelname)s%(reset)s | %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'cyan',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red'
            }
        )



        self.handler = _logging.StreamHandler()
        self.handler.setFormatter(self.formatter)
        self.addHandler(self.handler)