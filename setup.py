from setuptools import setup


setup(
    name='wssh',
    version='0.2.1',
    author='EricPai <ericpai94@hotmail.com>',
    packages=[
        'wssh'
        ],
    scripts=[
        'bin/wssh',
        'bin/wsshd'
        ],
    package_data={'': ['static/*', 'templates/*']},
    include_package_data=True,
    zip_safe=False
)
