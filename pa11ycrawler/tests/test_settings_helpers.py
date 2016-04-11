# pylint: disable=missing-docstring
from unittest import TestCase

from pa11ycrawler.settings_helpers import is_pa11y_setting, is_pa11ycrawler_setting


class SettingsHelpersTestCase(TestCase):
    def test_is_pa11y_setting(self):
        setting_name = 'PA11Y_SOMETHING'
        self.assertTrue(is_pa11y_setting(setting_name))

    def test_is_not_pa11y_setting(self):
        setting_name = 'PA11YCRAWLER_SOMETHING'
        self.assertFalse(is_pa11y_setting(setting_name))

    def test_is_pa11ycrawler_setting(self):
        setting_name = 'PA11YCRAWLER_SOMETHING'
        self.assertTrue(is_pa11ycrawler_setting(setting_name))

    def test_is_not_pa11ycrawler_setting(self):
        setting_name = 'PA11Y_SOMETHING'
        self.assertFalse(is_pa11ycrawler_setting(setting_name))
