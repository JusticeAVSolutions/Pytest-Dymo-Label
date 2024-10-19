from setuptools import setup, find_packages

setup(
    name='pytest-dymo-label',
    version='0.1.0',
    author='Mark Mayhew',
    author_email='mark.mayhew@javs.com',
    description='A pytest plugin to print Dymo labels from test data.',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pytest',
        'requests',
        'lxml',
    ],
    entry_points={
        'pytest11': [
            'dymo_label = pytest_dymo_label.plugin',
        ],
    },
    classifiers=[
        'Framework :: Pytest',
    ],
    url='https://github.com/justiceavsolutions/pytest-dymo-label',
)
