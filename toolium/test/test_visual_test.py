# -*- coding: utf-8 -*-
u"""
Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
This file is part of Toolium.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import re
import shutil

import mock
import pytest
from PIL import Image
# from needle.engines.imagemagick_engine import Engine as MagickEngine
from needle.engines.perceptualdiff_engine import Engine as PerceptualEngine
from needle.engines.pil_engine import Engine as PilEngine

from toolium.config_files import ConfigFiles
from toolium.driver_wrapper import DriverWrapper
from toolium.driver_wrapper import DriverWrappersPool
from toolium.test.test_utils import get_mock_element
from toolium.visual_test import VisualTest

# Get file paths
root_path = os.path.dirname(os.path.realpath(__file__))
file_v1 = os.path.join(root_path, 'resources', 'register.png')
file_v2 = os.path.join(root_path, 'resources', 'register_v2.png')
file_small = os.path.join(root_path, 'resources', 'register_small.png')
file_ios = os.path.join(root_path, 'resources', 'ios.png')


@pytest.yield_fixture
def driver_wrapper():
    # Remove previous visual path
    root_path = os.path.dirname(os.path.realpath(__file__))
    visual_path = os.path.join(root_path, 'output', 'visualtests')
    if os.path.exists(visual_path):
        shutil.rmtree(visual_path)

    # Reset wrappers pool values
    DriverWrappersPool._empty_pool()
    DriverWrapper.config_properties_filenames = None

    # Create a new wrapper
    driver_wrapper = DriverWrappersPool.get_default_wrapper()
    driver_wrapper.driver = mock.MagicMock()

    # Configure properties
    root_path = os.path.dirname(os.path.realpath(__file__))
    config_files = ConfigFiles()
    config_files.set_config_directory(os.path.join(root_path, 'conf'))
    config_files.set_config_properties_filenames('properties.cfg')
    config_files.set_output_directory(os.path.join(root_path, 'output'))
    driver_wrapper.configure(tc_config_files=config_files)
    driver_wrapper.config.set('VisualTests', 'enabled', 'true')

    yield driver_wrapper

    # Remove visual path
    visual_path = os.path.join(root_path, 'output', 'visualtests')
    if os.path.exists(visual_path):
        shutil.rmtree(visual_path)

    # Reset wrappers pool values
    DriverWrappersPool._empty_pool()
    DriverWrapper.config_properties_filenames = None


def test_no_enabled(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'enabled', 'false')
    visual = VisualTest(driver_wrapper)

    visual.assert_screenshot(None, filename='screenshot_full', file_suffix='screenshot_suffix')
    driver_wrapper.driver.save_screenshot.assert_not_called()


def test_engine_pil(driver_wrapper):
    visual = VisualTest(driver_wrapper)
    assert isinstance(visual.engine, PilEngine)


def test_engine_perceptual(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'engine', 'perceptualdiff')
    visual = VisualTest(driver_wrapper)

    assert isinstance(visual.engine, PerceptualEngine)


# def test_engine_magick(driver_wrapper):
#    driver_wrapper.config.set('VisualTests', 'engine', 'imagemagick')
#    visual = VisualTest(driver_wrapper)
#    assert isinstance(visual.engine, MagickEngine)


def test_engine_empty(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'engine', '')
    visual = VisualTest(driver_wrapper)

    assert isinstance(visual.engine, PilEngine)


def test_engine_unknown(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'engine', 'unknown')
    visual = VisualTest(driver_wrapper)

    assert isinstance(visual.engine, PilEngine)


def test_compare_files_equals(driver_wrapper):
    visual = VisualTest(driver_wrapper)
    message = visual.compare_files('report_name', file_v1, file_v1, 0)
    assert message is None


def test_compare_files_diff(driver_wrapper):
    visual = VisualTest(driver_wrapper)
    message = visual.compare_files('report_name', file_v1, file_v2, 0)
    assert 'by a distance of 522.65' in message


def test_compare_files_diff_fail(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'fail', 'true')
    visual = VisualTest(driver_wrapper)

    with pytest.raises(AssertionError):
        visual.compare_files('report_name', file_v1, file_v2, 0)


def test_compare_files_size(driver_wrapper):
    visual = VisualTest(driver_wrapper)
    message = visual.compare_files('report_name', file_v1, file_small, 0)
    # PIL returns an empty error, but PyTest modifies AssertionError
    assert 'assert (1680, 388) == (1246, 388)' in message


def test_compare_files_size_fail(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'fail', 'true')
    visual = VisualTest(driver_wrapper)

    with pytest.raises(AssertionError):
        visual.compare_files('report_name', file_v1, file_small, 0)


def test_get_html_row(driver_wrapper):
    expected_row = '<tr class=diff><td>report_name</td><td><img style="width: 100%" onclick=' \
                   '"launchModal\(this.src\)" src=".*register_v2.png"/></td></td><td><img style="width: 100%" ' \
                   'onclick="launchModal\(this.src\)" src=".*register.png"/></td></td><td></td></tr>'
    visual = VisualTest(driver_wrapper)
    row = visual._get_html_row('diff', 'report_name', file_v1, file_v2)
    assert re.compile(expected_row).match(row) is not None


def assert_image(visual, img, img_name, expected_image_filename):
    """Save img in an image file and compare with the expected image

    :param img: image object
    :param img_name: temporary filename
    :param expected_image_filename: filename of the expected image
    """
    # Save result image in output folder
    result_file = os.path.join(visual.output_directory, img_name + '.png')
    img.save(result_file)

    # Output image and expected image must be equals
    expected_image = os.path.join(root_path, 'resources', expected_image_filename + '.png')
    PilEngine().assertSameFiles(result_file, expected_image, 0.1)


def test_crop_element(driver_wrapper):
    # Create element mock
    web_element = get_mock_element(x=250, y=40, height=40, width=300)
    visual = VisualTest(driver_wrapper)

    # Resize image
    img = Image.open(file_v1)
    img = visual.crop_element(img, web_element)

    # Assert output image
    assert_image(visual, img, 'report_name', 'register_cropped_element')


def test_mobile_resize(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.driver.get_window_size.return_value = {'width': 375, 'height': 667}
    driver_wrapper.config.set('Driver', 'type', 'ios')
    visual = VisualTest(driver_wrapper)

    # Resize image
    img = Image.open(file_ios)
    img = visual.mobile_resize(img)

    # Assert output image
    assert_image(visual, img, 'report_name', 'ios_resized')


def test_mobile_no_resize(driver_wrapper):
    # Update conf and create a new VisualTest instance
    driver_wrapper.driver.get_window_size.return_value = {'width': 750, 'height': 1334}
    driver_wrapper.config.set('Driver', 'type', 'ios')
    visual = VisualTest(driver_wrapper)

    # Resize image
    orig_img = Image.open(file_ios)
    img = visual.mobile_resize(orig_img)

    # Assert that image object has not been modified
    assert orig_img == img


def test_exclude_elements(driver_wrapper):
    # Create elements mock
    visual = VisualTest(driver_wrapper)
    web_elements = [get_mock_element(x=250, y=40, height=40, width=300),
                    get_mock_element(x=250, y=90, height=20, width=100)]
    img = Image.open(file_v1)  # Exclude elements
    img = visual.exclude_elements(img, web_elements)

    # Assert output image
    assert_image(visual, img, 'report_name', 'register_exclude')


def test_exclude_element_outofimage(driver_wrapper):
    # Create elements mock
    visual = VisualTest(driver_wrapper)
    web_elements = [get_mock_element(x=250, y=40, height=40, width=1500)]
    img = Image.open(file_v1)

    # Exclude elements
    img = visual.exclude_elements(img, web_elements)

    # Assert output image
    assert_image(visual, img, 'report_name', 'register_exclude_outofimage')


def test_exclude_no_elements(driver_wrapper):
    # Exclude no elements
    visual = VisualTest(driver_wrapper)
    img = Image.open(file_v1)
    img = visual.exclude_elements(img, [])

    # Assert output image
    assert_image(visual, img, 'report_name', 'register')


def test_assert_screenshot_no_enabled_force(driver_wrapper):
    # Configure driver mock
    def copy_file_side_effect(output_file):
        shutil.copyfile(file_v1, output_file)

    driver_wrapper.driver.save_screenshot.side_effect = copy_file_side_effect

    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'enabled', 'false')
    visual = VisualTest(driver_wrapper, force=True)

    # Assert screenshot
    visual.assert_screenshot(None, filename='screenshot_full', file_suffix='screenshot_suffix')
    output_file = os.path.join(visual.output_directory, '01_screenshot_full__screenshot_suffix.png')
    driver_wrapper.driver.save_screenshot.assert_called_once_with(output_file)


def test_assert_screenshot_no_enabled_force_fail(driver_wrapper):
    # Configure driver mock
    def copy_file_side_effect(output_file):
        shutil.copyfile(file_v1, output_file)

    driver_wrapper.driver.save_screenshot.side_effect = copy_file_side_effect

    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('VisualTests', 'fail', 'false')
    driver_wrapper.config.set('VisualTests', 'enabled', 'false')
    visual = VisualTest(driver_wrapper, force=True)

    # Add v2 baseline image
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox', 'screenshot_full.png')
    shutil.copyfile(file_v2, baseline_file)

    # Assert screenshot
    with pytest.raises(AssertionError):
        visual.assert_screenshot(None, filename='screenshot_full', file_suffix='screenshot_suffix')
    output_file = os.path.join(visual.output_directory, '01_screenshot_full__screenshot_suffix.png')
    driver_wrapper.driver.save_screenshot.assert_called_once_with(output_file)


def test_assert_screenshot_full_and_save_baseline(driver_wrapper):
    # Configure driver mock
    def copy_file_side_effect(output_file):
        shutil.copyfile(file_v1, output_file)

    driver_wrapper.driver.save_screenshot.side_effect = copy_file_side_effect
    visual = VisualTest(driver_wrapper)

    # Assert screenshot
    visual.assert_screenshot(None, filename='screenshot_full', file_suffix='screenshot_suffix')
    output_file = os.path.join(visual.output_directory, '01_screenshot_full__screenshot_suffix.png')
    driver_wrapper.driver.save_screenshot.assert_called_once_with(output_file)

    # Output image and new baseline image must be equals
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox',
                                 'screenshot_full.png')
    PilEngine().assertSameFiles(output_file, baseline_file, 0.1)


def test_assert_screenshot_element_and_save_baseline(driver_wrapper):
    # Create element mock
    web_element = get_mock_element(x=250, y=40, height=40, width=300)

    # Configure driver mock
    with open(file_v1, "rb") as f:
        image_data = f.read()
    driver_wrapper.driver.get_screenshot_as_png.return_value = image_data
    visual = VisualTest(driver_wrapper)

    # Assert screenshot
    visual.assert_screenshot(web_element, filename='screenshot_elem', file_suffix='screenshot_suffix')
    driver_wrapper.driver.get_screenshot_as_png.assert_called_once_with()

    # Check cropped image
    expected_image = os.path.join(root_path, 'resources', 'register_cropped_element.png')
    output_file = os.path.join(visual.output_directory, '01_screenshot_elem__screenshot_suffix.png')
    PilEngine().assertSameFiles(output_file, expected_image, 0.1)

    # Output image and new baseline image must be equals
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox',
                                 'screenshot_elem.png')
    PilEngine().assertSameFiles(output_file, baseline_file, 0.1)


def test_assert_screenshot_full_and_compare(driver_wrapper):
    # Configure driver mock
    def copy_file_side_effect(output_file):
        shutil.copyfile(file_v1, output_file)

    driver_wrapper.driver.save_screenshot.side_effect = copy_file_side_effect
    visual = VisualTest(driver_wrapper)

    # Add baseline image
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox',
                                 'screenshot_full.png')
    shutil.copyfile(file_v1, baseline_file)

    # Assert screenshot
    visual.assert_screenshot(None, filename='screenshot_full', file_suffix='screenshot_suffix')
    output_file = os.path.join(visual.output_directory, '01_screenshot_full__screenshot_suffix.png')
    driver_wrapper.driver.save_screenshot.assert_called_once_with(output_file)


def test_assert_screenshot_element_and_compare(driver_wrapper):
    # Add baseline image
    visual = VisualTest(driver_wrapper)
    expected_image = os.path.join(root_path, 'resources', 'register_cropped_element.png')
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox',
                                 'screenshot_elem.png')
    shutil.copyfile(expected_image, baseline_file)

    # Create element mock
    web_element = get_mock_element(x=250, y=40, height=40, width=300)

    # Configure driver mock
    with open(file_v1, "rb") as f:
        image_data = f.read()
    driver_wrapper.driver.get_screenshot_as_png.return_value = image_data

    # Assert screenshot
    visual.assert_screenshot(web_element, filename='screenshot_elem', file_suffix='screenshot_suffix')
    driver_wrapper.driver.get_screenshot_as_png.assert_called_once_with()


def test_assert_screenshot_mobile_resize_and_exclude(driver_wrapper):
    # Create elements mock
    exclude_elements = [get_mock_element(x=0, y=0, height=24, width=375)]

    # Configure driver mock
    with open(file_ios, "rb") as f:
        image_data = f.read()
    driver_wrapper.driver.get_screenshot_as_png.return_value = image_data
    driver_wrapper.driver.get_window_size.return_value = {'width': 375, 'height': 667}

    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('Driver', 'type', 'ios')
    visual = VisualTest(driver_wrapper)

    # Assert screenshot
    visual.assert_screenshot(None, filename='screenshot_ios', file_suffix='screenshot_suffix',
                             exclude_elements=exclude_elements)
    driver_wrapper.driver.get_screenshot_as_png.assert_called_once_with()

    # Check cropped image
    expected_image = os.path.join(root_path, 'resources', 'ios_excluded.png')
    output_file = os.path.join(visual.output_directory, '01_screenshot_ios__screenshot_suffix.png')
    PilEngine().assertSameFiles(output_file, expected_image, 0.1)

    # Output image and new baseline image must be equals
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox',
                                 'screenshot_ios.png')
    PilEngine().assertSameFiles(output_file, baseline_file, 0.1)


def test_assert_screenshot_mobile_web_resize_and_exclude(driver_wrapper):
    # Create elements mock
    form_element = get_mock_element(x=0, y=0, height=559, width=375)
    exclude_elements = [get_mock_element(x=15, y=296.515625, height=32, width=345)]

    # Configure driver mock
    file_ios_web = os.path.join(root_path, 'resources', 'ios_web.png')
    with open(file_ios_web, "rb") as f:
        image_data = f.read()
    driver_wrapper.driver.get_screenshot_as_png.return_value = image_data
    driver_wrapper.driver.get_window_size.return_value = {'width': 375, 'height': 667}

    # Update conf and create a new VisualTest instance
    driver_wrapper.config.set('Driver', 'type', 'ios')
    driver_wrapper.config.set('AppiumCapabilities', 'browserName', 'safari')
    visual = VisualTest(driver_wrapper)

    # Assert screenshot
    visual.assert_screenshot(form_element, filename='screenshot_ios_web', file_suffix='screenshot_suffix',
                             exclude_elements=exclude_elements)
    driver_wrapper.driver.get_screenshot_as_png.assert_called_once_with()

    # Check cropped image
    expected_image = os.path.join(root_path, 'resources', 'ios_web_exclude.png')
    output_file = os.path.join(visual.output_directory, '01_screenshot_ios_web__screenshot_suffix.png')
    PilEngine().assertSameFiles(output_file, expected_image, 0.1)

    # Output image and new baseline image must be equals
    baseline_file = os.path.join(root_path, 'output', 'visualtests', 'baseline', 'firefox',
                                 'screenshot_ios_web.png')
    PilEngine().assertSameFiles(output_file, baseline_file, 0.1)


def test_assert_screenshot_str_threshold(driver_wrapper):
    visual = VisualTest(driver_wrapper)
    with pytest.raises(TypeError):
        visual.assert_screenshot(None, 'screenshot_full', threshold='name')


def test_assert_screenshot_greater_threshold(driver_wrapper):
    visual = VisualTest(driver_wrapper)
    with pytest.raises(TypeError):
        visual.assert_screenshot(None, 'screenshot_full', threshold=2)
