"""
Helpers for determining purpose of settings.
"""
from scrapy.settings import Settings


def is_pa11y_setting(setting_name):
    """
    Returns true if setting is for Pa11y CLI.
    """
    return setting_name.startswith('PA11Y_')


def is_pa11ycrawler_setting(setting_name):
    """
    Returns true if setting is a custom setting for pa11ycrawler.
    """
    return setting_name.startswith('PA11YCRAWLER_')


def get_default_settings():
    """
    Returns default settings for pa11ycrawler
    """
    settings = Settings()
    settings.setmodule('pa11ycrawler.settings')
    return settings
