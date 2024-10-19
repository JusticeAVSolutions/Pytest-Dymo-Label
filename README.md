# Pytest-Dymo-Label

`pytest-dymo-label` is a pytest plugin designed to print Dymo labels from test data. This plugin allows you to generate labels based on test results, providing an easy way to mark and identify devices or units directly from your test suite.

## Features

- Print labels from test data automatically at the end of a test session.
- Customize the label content, including serial number, model number, firmware version, test status, and manufacturing date.
- Integrate directly with the Dymo LabelWriter 4XL printer using the Dymo Web Service.

## Installation

Install the plugin using pip:

```sh
pip install git+https://github.com/JusticeAVSolutions/pytest-dymo-label.git
```

## Requirements

- Python 3.x
- pytest
- requests
- lxml
- Dymo Web Service running on your system: download [Dymo Connect](https://www.dymo.com/support?cfid=user-guide)

## Usage

Add the following command-line options when running pytest to control the label printing:

- `--dymo-url`: Specify the Dymo Web Service URL. Defaults to `https://localhost:41951/`.
- `--print-label`: Set this flag to print a label at the end of the test session.

Example:

```sh
pytest --dymo-url "https://localhost:41951/" --print-label
```

To capture data that is to be printed on the label, use the `label_data` fixture.

Examples:

```python
def test_get_serial_number(label_data):
    # Simulate obtaining serial number from device
    serial_number = '5C:30:52:FF:FF:FF'
    label_data['serial_number'] = serial_number
    assert serial_number is not None  # Or any other assertion

def test_get_model_number(label_data):
    # Simulate obtaining model number from device
    model_number = 'ModelX'
    label_data['model_number'] = model_number
    assert model_number is not None

def test_get_firmware_version(label_data):
    # Simulate obtaining firmware version from device
    firmware_version = 'FW1.0.3'
    label_data['firmware_version'] = firmware_version
    assert firmware_version is not None
```

## Label Template

The label template (`manufacturing_label_30334.dymo`) should be included in the package's templates subpackage. This template contains placeholders for values such as:

- `[SerialNumber]`
- `[ModelNumber]`
- `[FirmwareVersion]`
- `[ManufacturingDate]`
- `[TestStatus]`
- Barcode contents (Serial number)
- QR Code contents (label text and first failed test)

These placeholders will be replaced with data from your test session.

## How It Works

1. **Add Options**: Use `pytest_addoption` to add command-line options for configuring the plugin, such as the Dymo Web Service URL and whether or not to print a label.
2. **Configure the Plugin**: `pytest_configure` sets up the configuration, including default values.
3. **Initialize Session Data**: `pytest_sessionstart` initializes an empty dictionary for storing label data.
4. **Run Tests**: During test execution, `pytest_runtest_makereport` captures the outcome of each test and updates the label data.
5. **Print Label**: After all tests have finished (`pytest_sessionfinish`), the plugin reads the label template, fills in the placeholders, and sends a print request to the Dymo Web Service.

## Example Workflow

1. Connect a Dymo LabelWriter 4XL to your computer.
2. Ensure the Dymo Web Service is running and accessible at the specified URL.
3. Ensure tests utilize `label_data` fixture for collecting serial number, etc.
3. Run your tests with the `--print-label` option.
4. At the end of the test session, a label is printed with the test results and other specified data.

