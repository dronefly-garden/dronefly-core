# Abstract base formatter classes


class BaseFormatter:
    def format():
        raise NotImplementedError


class ListFormatter(BaseFormatter):
    def format_page():
        raise NotImplementedError

    def last_page():
        raise NotImplementedError


class BaseCountFormatter(BaseFormatter):
    def count():
        raise NotImplementedError

    def description():
        raise NotImplementedError
