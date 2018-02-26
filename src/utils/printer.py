"""
Provides utility methods for pretty logging
"""


def info(string):
    print(Color.INFO + 'INFO: ' + Color.ENDC + string)


def warning(string):
    print(Color.WARNING + 'WARNING: ' + Color.ENDC + string)


def error(string):
    print(Color.ERROR + 'ERROR : ' + Color.ENDC + string)


class Color:
    INFO = '\033[96m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'
