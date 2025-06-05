# setup.py
from setuptools import setup, find_packages
import os

# Function to read the version from ultron/__init__.py
def get_version(package_name='ultron'):
    version_py = os.path.join(package_name, '__init__.py')
    with open(version_py) as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    raise RuntimeError("Version string not found")

# Function to read the requirements
def get_requirements():
    with open('requirements.txt') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read README for long description
def get_long_description():
    try:
        with open('README.md', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "ULTRON-AI: Advanced AI-powered code analysis with no strings attached."

setup(
    name='ultron-ai',
    version=get_version(),
    author='Xplo8E',
    author_email='xplo8e@outlook.com',  # Update with your email
    description='⚡ ULTRON-AI: Advanced AI-powered code analysis with no strings attached',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/Xplo8E/ultron-ai',  # Update with your GitHub URL
    project_urls={
        'Documentation': 'https://github.com/Xplo8E/ultron-ai#readme',
        'Source': 'https://github.com/Xplo8E/ultron-ai',
        'Tracker': 'https://github.com/Xplo8E/ultron-ai/issues',
    },
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=get_requirements(),
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=22.0',
            'flake8>=4.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'ultron-ai=ultron.main_cli:cli',
            'ultron=ultron.main_cli:cli',  # Shorter alias
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Security',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Natural Language :: English',
    ],
    keywords='code-analysis ai security vulnerability-scanner code-review gemini ultron',
    python_requires='>=3.8',
    zip_safe=False,
)