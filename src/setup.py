from setuptools import setup


setup(
    name='dfl',
    packages=["dfl"],
    author='Mihai Pomarlan',
    license='MIT',
    install_requires=['inflection', 'progressbar', 'requests', 'rdflib'],
)
