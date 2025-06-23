# setup.py
from setuptools import setup, find_packages

# Read the version from ultron/__init__.py
def get_version():
    with open('ultron/__init__.py') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return "0.1.4"  # fallback version

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
    author_email='xplo8e@outlook.com',
    description='⚡ ULTRON-AI: Advanced AI-powered code analysis with Chain of Thought and ReAct framework',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/Xplo8E/ultron-ai',
    project_urls={
        'Source': 'https://github.com/Xplo8E/ultron-ai',
        'Tracker': 'https://github.com/Xplo8E/ultron-ai/issues',
    },
    license='GPL-3.0',
    packages=find_packages(exclude=['test*', 'venv*']),
    include_package_data=True,
    install_requires=[
    'google-genai',
    'google-api-core',
    'python-dotenv',
    'click',
    'rich',
    'pydantic',
    'demjson3',
    'networkx',
    ],
    entry_points={
        'console_scripts': [
            'ultron=ultron.main_cli:cli',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Security',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Environment :: Console',
    ],
    keywords='sast code-analysis ai security vulnerability-scanner code-review devsecops auditing llm gemini ultron chain-of-thought react sarif',
    python_requires='>=3.10',
    zip_safe=False,
)