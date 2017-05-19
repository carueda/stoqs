#!/usr/bin/env python

__author__ = "Mike McCann"
__copyright__ = "Copyright 2011, MBARI"
__credits__ = ["Chander Ganesan, Open Technology Group"]
__license__ = "GPL"
__version__ = "$Revision: 12276 $".split()[1]
__maintainer__ = "Mike McCann"
__email__ = "mccann at mbari.org"
__status__ = "Development"
__doc__ = '''

Functional tests for the stoqs application

Mike McCann

@undocumented: __doc__ parser
@author: __author__
@status: __status__
@license: __license__
'''

from django.test import TestCase
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from stoqs.models import Parameter

import logging
import re
import time

logger = logging.getLogger(__name__)

class wait_for_text_to_match(object):
    def __init__(self, locator, pattern):
        self.locator = locator
        self.pattern = re.compile(pattern)

    def __call__(self, driver):
        try:
            element_text = EC._find_element(driver, self.locator).text
            return self.pattern.search(element_text)
        except StaleElementReferenceException:
            return False

class BaseTestCase(TestCase):
    # Note that the test runner sets DEBUG to False: 
    # https://docs.djangoproject.com/en/1.8/topics/testing/advanced/#django.test.runner.DiscoverRunner.setup_test_environment

    # Specifying fixtures will copy the default database to a test database allowing for simple stoqs.models
    # object retrieval.  Note that self.browser gets pages from the original default database, not the copy.
    fixtures = ['stoqs_test_data.json']
    multi_db = False

    def setUp(self):
        profile = webdriver.FirefoxProfile()
        self.browser = webdriver.Firefox(profile)
        self.browser.implicitly_wait(10)

    def tearDown(self):
        self.browser.quit()

    def _mapserver_loading_panel_test(self):
        '''Wait for ajax-loader GIF image to go away'''
        seconds = 2
        wait = WebDriverWait(self.browser, seconds)
        try:
            wait.until(lambda display: self.browser.find_element_by_id('map').
                        find_element_by_class_name('olControlLoadingPanel').
                        value_of_css_property('display') == 'none')
        except TimeoutException as e:
            return ('Mapserver images did not load after waiting ' +
                    str(seconds) + ' seconds')
        else:
            return ''

    def _wait_until_visible_then_click(self, element, scroll_up=True):
        # See: http://stackoverflow.com/questions/23857145/selenium-python-element-not-clickable
        element = WebDriverWait(self.browser, 5, poll_frequency=.2).until(
                        EC.visibility_of(element))
        if scroll_up:
            self.browser.execute_script("window.scrollTo(0, 0)")

        element.click()

    def _wait_until_text_is_visible(self, element_id, expected_text, contains=False):

        if contains:
            WebDriverWait(self.browser, 5, poll_frequency=.2).until(
                          wait_for_text_to_match((By.ID, element_id), expected_text))
        else:
            WebDriverWait(self.browser, 5, poll_frequency=.2).until(
                          EC.text_to_be_present_in_element((By.ID, element_id), expected_text))

    def _test_share_view(self, func_name):
        # Generic for any func_name that creates a view to share
        getattr(self, func_name)()

        share_view = self.browser.find_element_by_id('permalink')
        self._wait_until_visible_then_click(share_view)
        permalink = self.browser.find_element_by_id('permalink-box'
                             ).find_element_by_name('permalink')
        self._wait_until_visible_then_click(permalink)
        permalink_url = permalink.get_attribute('value')

        # Load permalink
        self.browser.get(permalink_url)
        self.assertEquals('', self._mapserver_loading_panel_test())


class BrowserTestCase(BaseTestCase):
    '''Use selenium to test standard things in the browser
    '''

    def test_campaign_page(self):
        self.browser.get('http://localhost:8000/')
        self.assertIn('Campaign List', self.browser.title)

    def test_query_page(self):
        self.browser.get('http://localhost:8000/default/query/')
        self.assertIn('default', self.browser.title)
        self.assertEquals('', self._mapserver_loading_panel_test())

    def test_dorado_trajectory(self):
        self.browser.get('http://localhost:8000/default/query/')
        try:
            # Click on Platforms to expand
            platforms_anchor = self.browser.find_element_by_id(
                                    'platforms-anchor')
            self._wait_until_visible_then_click(platforms_anchor)
        except NoSuchElementException as e:
            print e
            print "Is the development server running?"
            return

        # Finds <tr> for 'dorado' then gets the button for clicking
        dorado_button = self.browser.find_element_by_id('dorado'
                            ).find_element_by_tag_name('button')
        self._wait_until_visible_then_click(dorado_button)

        # Test that Mapserver returns images
        self.assertEquals('', self._mapserver_loading_panel_test())

        # Test Spatial 3D
        spatial_3d_anchor = self.browser.find_element_by_id('spatial-3d-anchor')
        self._wait_until_visible_then_click(spatial_3d_anchor)
        showplatforms = self.browser.find_element_by_id('showplatforms')
        self._wait_until_visible_then_click(showplatforms)
        self.assertEquals('geolocation', self.browser.find_element_by_id('dorado_LOCATION').tag_name)

    def test_m1_timeseries(self):
        self.browser.get('http://localhost:8000/default/query/')
        # Test Temporal->Parameter for timeseries plots
        parameter_tab = self.browser.find_element_by_id('temporal-parameter-li')
        # Wait one second before clicking parameter_tab
        time.sleep(1)
        self._wait_until_visible_then_click(parameter_tab)
        djtb = self.browser.find_element_by_id('djHideToolBarButton')
        djtb.click()
        expected_text = 'bbp420'
        self._wait_until_text_is_visible('stride-info', expected_text, contains=True)
        self.assertIn(expected_text, self.browser.find_element_by_id('stride-info').text)

    def test_share_view_trajectory(self):
        self._test_share_view('test_dorado_trajectory')
        self.browser.implicitly_wait(10)
        self.assertEquals('geolocation', self.browser.find_element_by_id('dorado_LOCATION').tag_name)

    def test_share_view_timeseries(self):
        self._test_share_view('test_m1_timeseries')
        expected_text = 'bbp420'
        self._wait_until_text_is_visible('stride-info', expected_text, contains=True)
        self.assertIn(expected_text, self.browser.find_element_by_id('stride-info').text)

    def test_contour_plots(self):
        self.browser.get('http://localhost:8000/default/query/')

        # Open Measured Parameters section
        mp_section = self.browser.find_element_by_id('measuredparameters-anchor')
        self._wait_until_visible_then_click(mp_section)

        # Expand Temporal window
        expand_temporal = self.browser.find_element_by_id('td-zoom-rc-button')
        self._wait_until_visible_then_click(expand_temporal)

        # Make contour color plot of M1 northward_sea_water_velocity and hide Django toolbar
        northward_sea_water_velocity_HR_id = Parameter.objects.get(name='northward_sea_water_velocity_HR').id
        parameter_plot_radio_button = self.browser.find_element(By.XPATH,
            "//input[@name='parameters_plot' and @value='{}']".format(northward_sea_water_velocity_HR_id))
        parameter_plot_radio_button.click()
        contour_button = self.browser.find_element(By.XPATH, "//input[@name='showdataas' and @value='contour']")
        self._wait_until_visible_then_click(contour_button)
        djtb = self.browser.find_element_by_id('djHideToolBarButton')
        self._wait_until_visible_then_click(djtb)

        expected_text = 'Color: northward_sea_water_velocity_HR from M1_Mooring'
        self._wait_until_text_is_visible('temporalparameterplotinfo', expected_text)
        self.assertEquals(expected_text, self.browser.find_element_by_id('temporalparameterplotinfo').text)

        # Contour line of M1 northward_sea_water_velocity - same as color plot
        parameter_contour_plot_radio_button = self.browser.find_element(By.XPATH,
            "//input[@name='parameters_contour_plot' and @value='{}']".format(northward_sea_water_velocity_HR_id))
        parameter_contour_plot_radio_button.click()

        # Test that at least the color bar image appears
        self.assertIn('_M1_Mooring_colorbar_', self.browser.find_element_by_id('sectioncolorbarimg').get_property('src'))

        # Contour line of M1 SEA_WATER_SALINITY_HR_id - different from color plot
        SEA_WATER_SALINITY_HR_id = Parameter.objects.get(name='SEA_WATER_SALINITY_HR').id
        parameter_contour_plot_radio_button = self.browser.find_element(By.XPATH,
            "//input[@name='parameters_contour_plot' and @value='{}']".format(SEA_WATER_SALINITY_HR_id))
        parameter_contour_plot_radio_button.click()

        expected_text = 'Lines: SEA_WATER_SALINITY_HR from M1_Mooring'
        self._wait_until_text_is_visible('temporalparameterplotinfo_lines', expected_text)
        self.assertEquals(expected_text, self.browser.find_element_by_id('temporalparameterplotinfo_lines').text)

        # Clear the Color plot leaving just the Lines plot
        clear_color_plot_radio_button = self.browser.find_element_by_id('mp_parameters_plot_clear')
        clear_color_plot_radio_button.click()

        expected_text_color = ''
        expected_text_lines = 'Lines: SEA_WATER_SALINITY_HR from M1_Mooring'
        self._wait_until_text_is_visible('temporalparameterplotinfo', expected_text_color)
        self._wait_until_text_is_visible('temporalparameterplotinfo_lines', expected_text_lines)
        self.assertEquals(expected_text_color, self.browser.find_element_by_id('temporalparameterplotinfo').text)
        self.assertEquals(expected_text_lines, self.browser.find_element_by_id('temporalparameterplotinfo_lines').text)

        # Uncomment to visually inspect the plot for correctness
        ##self.browser.execute_script("window.scrollTo(0, 0)")
        ##import pdb; pdb.set_trace()


class BugsFoundTestCase(BaseTestCase):
    '''Test bugs that have been found
    '''
    fixtures = ['stoqs_test_data.json']
    multi_db = False

    def test_select_wrong_platform_after_plot(self):
        self.browser.get('http://localhost:8000/default/query/')

        # Open Measured Parameters section and plot Parameter bb470 from M1
        mp_section = self.browser.find_element_by_id('measuredparameters-anchor')
        self._wait_until_visible_then_click(mp_section)
        self.browser.find_element(By.XPATH,
                "//input[@name='parameters_plot' and @value='{}']".format(
                Parameter.objects.get(name='bb470').id)).click()

        # Select 'dorado' Platform - bb470 will not be in the selection
        platforms_anchor = self.browser.find_element_by_id('platforms-anchor')
        self._wait_until_visible_then_click(platforms_anchor)
        dorado_button = self.browser.find_element_by_id('dorado'
                            ).find_element_by_tag_name('button')
        self._wait_until_visible_then_click(dorado_button)

        # Uncomment to visually inspect the plot for correctness
        ##import pdb; pdb.set_trace()
