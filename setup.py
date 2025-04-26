# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="paperbites",
    version="0.1.0",
    author="Rimsha Kayastha",
    author_email="rkayastha@outlook.com",
    description="Convert research papers to TikTok-style videos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rimshatest/paperbites",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "moviepy",
        "requests",
        "PyMuPDF",
        "scholarly",
        "pytesseract",
        "pdf2image",
        "nltk",
        "scikit-learn",
        "aiohttp",
        "transformers",
        "gtts",
        "Pillow",
        "pydub"
    ],
    entry_points={
        "console_scripts": [
            "paperbites=paperbites.cli:main",
        ],
    },
)