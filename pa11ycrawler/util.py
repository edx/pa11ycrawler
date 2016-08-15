"""
Miscellaneous utilities for the crawler
"""
from json import JSONEncoder
from datetime import datetime


class DateTimeEncoder(JSONEncoder):
    "A JSON encoder that can handle datetimes"
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, datetime):
            return o.isoformat()
        return JSONEncoder.default(self, o)
