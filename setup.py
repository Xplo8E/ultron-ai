# setup.py
from setuptools import setup, find_packages
import os

# Function to read the version from src/ultron/__init__.py
def get_version(package_name='ultron'):
    version_py = os.path.join('src', package_name, '__init__.py')
    with open(version_py) as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    raise RuntimeError("Version string not found")

# Function to read the requirements
def get_requirements():
    with open('requirements.txt') as f:
        return f.read().splitlines()

setup(
    name='ultron-cli',
    version=get_version(),
    author='Your Name', # Replace with your name
    author_email='your.email@example.com', # Replace with your email
    description='An AI-powered code reviewer using Google Gemini.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/ultron-cli', # Replace with your project's URL
    license='MIT', # Or your chosen license
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    include_package_data=True, # To include non-code files specified in MANIFEST.in (if any)
    install_requires=get_requirements(),
    entry_points={
        'console_scripts': [
            'ultron = ultron.main_cli:cli',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta', # Or your project's status
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License', # Or your chosen license
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Environment :: Console',
    ],
    python_requires='>=3.8',
)