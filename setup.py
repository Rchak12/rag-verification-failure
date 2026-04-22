"""Setup configuration for rag-verification-failure package."""

from setuptools import setup, find_packages

with open("README_NEW.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="rag-verification-failure",
    version="1.0.0",
    author="Rishab Chakravarty",
    author_email="rchak@purdue.edu",
    description="Analyzing false positives in claim verification for RAG systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Rchak12/rag-verification-failure",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    include_package_data=True,
    keywords=[
        "rag", "retrieval-augmented-generation", "verification", "nlp", 
        "fact-checking", "biomedical", "llm", "gpt-4", "false-positives"
    ],
    project_urls={
        "Bug Reports": "https://github.com/Rchak12/rag-verification-failure/issues",
        "Source": "https://github.com/Rchak12/rag-verification-failure",
        "Documentation": "https://github.com/Rchak12/rag-verification-failure/tree/main/docs",
    },
)
