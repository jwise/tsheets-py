from distutils.core import setup

setup(
    name='tsheetspy',
    version='0.1.0',
    description='Python T-Sheets command line interface',
    author='Joshua Wise',
    packages=['tsheetspy'],
    scripts=['tsheetspy/scripts/tsheets'],
    install_requires=['requests']
)
