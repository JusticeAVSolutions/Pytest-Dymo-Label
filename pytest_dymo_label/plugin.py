import pytest
import datetime
import requests
from lxml import etree
import importlib.resources
import os
import uuid
from importlib.resources import files

# Use importlib.resources to access the label template within the package
from . import templates  # Assuming templates is a subpackage

# Add a custom marker attribute so that pytest sequencer picks it up
__pytest_sequencer_plugin__ = True

LABEL_TEMPLATE_FILENAME = 'manufacturing_label_30334.dymo'
DYMO_PATH = "DYMO/DLS/Printing"
DYMO_PRINT_LABEL = f"{DYMO_PATH}/PrintLabel"
DYMO_GET_PRINTERS = f"{DYMO_PATH}/GetPrinters"

def pytest_addoption(parser):
    # parser.addoption("--serial-number", action="store", help="Device serial number")
    # parser.addoption("--model-number", action="store", help="Device model number")
    # parser.addoption("--firmware-version", action="store", help="Firmware version")
    parser.addoption("--dymo-url", action="store", default="https://localhost:41951/", help="DYMO Web Service URL")
    parser.addoption("--print-label", action="store_true", default=False, help="Print label at end of test")

def pytest_configure(config):
    # config.serial_number = config.getoption("--serial-number")
    # config.model_number = config.getoption("--model-number")
    # config.firmware_version = config.getoption("--firmware-version")
    config.dymo_url = config.getoption("--dymo-url")
    config.test_status = 'PASS'  # Default to PASS; will be updated if any test fails
    config.label_should_print = config.getoption("--print-label", False)

def pytest_sessionstart(session):
    session.label_data = {}  # Initialize an empty dictionary for label data
    session.plugin_errors = []  # Initialize a list to store plugin errors

@pytest.fixture
def label_data(request):
    return request.session.label_data

def pytest_runtest_makereport(item, call):
    if "pytest_dymo_label/plugin.py" in item.nodeid:
        return  # Avoid processing the plugin's own tests

    if call.when == "call":
        outcome = 'PASS' if call.excinfo is None else 'FAIL'
        if outcome == 'FAIL':
            item.config.test_status = 'FAIL'  # Update overall test status on failure
            # Store the name of the first failed test if not already stored
            if 'first_failed_test' not in item.session.label_data:
                item.session.label_data['first_failed_test'] = item.name

def pytest_sessionfinish(session, exitstatus):
    config = session.config
    label_data = session.label_data
    printer_name = 'DYMO LabelWriter 4XL'

    if not config.label_should_print:
        return 
    
    is_connected = get_printer_connected(config.dymo_url, printer_name)
    if is_connected:
        print(f"The printer '{printer_name}' is connected.")
    else:
        error_message = f"The printer '{printer_name}' is not connected."
        print(f"[PLUGIN_ERROR] {__name__}: {error_message}")
        session.plugin_errors.append({
            'plugin': __name__,
            'error': error_message
        })
        return  # Exit early if printer is not connected

    # **1. Check for Non-Test Execution Modes**
    non_test_flags = [
        'collectonly',
        'version',
        'help',
        'fixtures',
        'markers',
        'trace_config',
        'doctest_mods',
        'showfixtures',
        'runxfail',
    ]

    if any(getattr(config.option, flag, False) for flag in non_test_flags):
        # logger.info("Non-test execution mode detected. Skipping label printing.")
        return

    # **2. Check if in a Worker Process (e.g., pytest-xdist)**
    if hasattr(config, 'workerinput'):
        # logger.info("Worker process detected. Skipping label printing.")
        return

    # **3. Check Exit Status**
    if exitstatus not in [0, 1]:
        # logger.info(f"Pytest exited with status {exitstatus}. Skipping label printing.")
        return

    # **4. Check if Tests Were Collected and Executed**
    if session.testscollected == 0:
        # logger.info("No tests were collected. Skipping label printing.")
        return

    terminalreporter = session.config.pluginmanager.getplugin("terminalreporter")
    
    # Retrieve lists of passed and failed test reports
    passed_tests = terminalreporter.stats.get('passed', [])
    failed_tests = terminalreporter.stats.get('failed', [])

    # Count the number of passed and failed tests
    num_passed = len(passed_tests)
    num_failed = len(failed_tests)

    if num_failed + num_passed == 0:
        # logger.info("No tests were executed. Skipping label printing.")
        return

    # Read the label template from the package
    try:
        label_xml = files(templates).joinpath(LABEL_TEMPLATE_FILENAME).read_text(encoding='utf-8')
    except FileNotFoundError:
        error_message = f"Label template '{LABEL_TEMPLATE_FILENAME}' not found in the package."
        print(f"[PLUGIN_ERROR] {__name__}: {error_message}")
        session.plugin_errors.append({
            'plugin': __name__,
            'error': error_message
        })
        return
    except Exception as e:
        error_message = f"Error reading label template: {e}"
        print(f"[PLUGIN_ERROR] {__name__}: {error_message}")
        session.plugin_errors.append({
            'plugin': __name__,
            'error': error_message
        })
        return

    # Replace placeholders
    label_xml = label_xml.replace('[SerialNumber]', label_data.get('serial_number', 'N/A'))
    label_xml = label_xml.replace('[ModelNumber]', label_data.get('model_number', 'N/A'))
    label_xml = label_xml.replace('[FirmwareVersion]', label_data.get('firmware_version', 'N/A'))
    label_xml = label_xml.replace('[ManufacturingDate]', datetime.date.today().isoformat())
    label_xml = label_xml.replace('[TestStatus]', config.test_status)
    label_xml = label_xml.replace('[BarcodeSN]', label_data.get('serial_number', 'N/A'))

    first_failed_test = label_data.get('first_failed_test', 'None')

    # Update QR code content
    qr_content = f"""Serial: {label_data.get('serial_number', 'N/A')}
Model: {label_data.get('model_number', 'N/A')}
Date: {datetime.date.today().isoformat()}
Status: {config.test_status}
FW: {label_data.get('firmware_version', 'N/A')}
First Failed Test: {first_failed_test}"""

    # Parse the XML to update the QR code content
    try:
        root = etree.fromstring(label_xml.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        error_message = f"Failed to parse label XML: {e}"
        print(f"[PLUGIN_ERROR] {__name__}: {error_message}")
        session.plugin_errors.append({
            'plugin': __name__,
            'error': error_message
        })
        return

    # Update QR code DataString and Value
    data_string_elements = root.xpath('//QRCodeObject/Data/DataString')
    value_elements = root.xpath('//QRCodeObject/TextDataHolder/Value')

    for elem in data_string_elements + value_elements:
        elem.text = qr_content

    # Convert back to string
    label_xml = etree.tostring(root, encoding='utf-8').decode('utf-8')

    # Send the label to the Dymo printer
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'printerName': printer_name,
        # 'printParamsXml': '',
        'labelXml': label_xml,
        'labelSetXml': ''
    }

    try:
        response = requests.post(f"{config.dymo_url}{DYMO_PRINT_LABEL}", headers=headers, data=data, verify=False)
        response.raise_for_status()
        print("Label printed successfully.")
    except requests.exceptions.RequestException as e:
        error_message = f"Failed to print label: {e}"
        print(f"[PLUGIN_ERROR] {__name__}: {error_message}")
        session.plugin_errors.append({
            'plugin': __name__,
            'error': error_message
        })

def get_printer_connected(dymo_url, printer_name):
    printers = get_printers(dymo_url)
    for printer in printers:
        if printer['Name'] == printer_name:
            return printer['IsConnected']
    
    return False

def get_printers(dymo_url):
    try:
        response = requests.get(f"{dymo_url}{DYMO_GET_PRINTERS}", verify=False)
        response.raise_for_status()
        # Parse XML response
        root = etree.fromstring(response.content)
        printers = []
        for printer in root.findall('.//LabelWriterPrinter'):
            name = printer.findtext('Name')
            model_name = printer.findtext('ModelName')
            is_connected = printer.findtext('IsConnected') == 'True'

            printers.append({
                'Name': name,
                'IsConnected': is_connected
                })
        return printers
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to retrieve printers: {e}")
        return []
    except etree.XMLSyntaxError as e:
        print(f"[ERROR] Failed to parse GetPrinters response XML: {e}")
        return []
