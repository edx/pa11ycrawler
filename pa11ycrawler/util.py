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


def pa11y_counts(results):
    """
    Given a list of pa11y results, return three integers:
    number of errors, number of warnings, and number of notices.
    """
    num_error = 0
    num_warning = 0
    num_notice = 0
    for result in results:
        if result['type'] == 'error':
            num_error += 1
        elif result['type'] == 'warning':
            num_warning += 1
        elif result['type'] == 'notice':
            num_notice += 1
    return num_error, num_warning, num_notice
