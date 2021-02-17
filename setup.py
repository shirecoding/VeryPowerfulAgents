from distutils.core import setup

from setuptools import find_packages

exec(open("agents/version.py").read())
setup(
    name="powerful-agents",
    version=__version__,
    author="shirecoding",
    author_email="shirecoding@gmail.com",
    install_requires=["pyzmq", "rx", "pyrsistent", "aiohttp[speedups]"],
    extras_require={
        "test": ["pytest", "pytest-cov", "pytest-html", "pytest-metadata", "numpy"],
        "docs": ["mkdocs", "mkdocstrings"],
    },
    url="https://github.com/shirecoding/VeryPowerfulAgents.git",
    download_url=f"https://github.com/shirecoding/VeryPowerfulAgents/archive/{__version__}.tar.gz",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
    include_package_data=True,
    packages=find_packages() + [],
    package_data={},
)
