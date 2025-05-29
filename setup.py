from setuptools import setup, find_packages

setup(
    name='translation_service',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'tenacity',
        'chardet',
        'regex',
        'lxml',
    ],
    entry_points={
        'console_scripts': [
            'enchant_cli=enchant_cli:main',
        ],
    },
    author='Your Name',
    author_email='your.email@example.com',
    description='A CLI tool to translate Chinese text to English using AI.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/translation_service',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
