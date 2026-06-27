# Abstract base formatter classes


class BaseFormatter:
    def format(*args, **kwargs):
        raise NotImplementedError


class ListFormatter(BaseFormatter):
    def format_page(*args, **kwargs):
        raise NotImplementedError

    def last_page(*args, **kwargs):
        raise NotImplementedError


class BaseCountFormatter(BaseFormatter):
    def count(*args, **kwargs):
        raise NotImplementedError

    def description(*args, **kwargs):
        raise NotImplementedError
