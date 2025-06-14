from setuptools import setup, find_packages

setup(
    name="postpy",
    version="1.2.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.0",
        "pydantic>=2.0.0",
        "flask>=3.0.0",
    ],
    entry_points={
        'console_scripts': [
            'postpy=postpy.cli:cli',
        ],
    },
) 