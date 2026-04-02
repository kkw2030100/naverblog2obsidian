from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="naverblog2obsidian",
    version="1.0.0",
    author="Kim Kiwon",
    author_email="kkw2030100@gmail.com",
    description="네이버 블로그를 옵시디언 마크다운으로 변환하는 도구",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kkw2030100/naverblog2obsidian",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "naverblog2obsidian=naverblog2obsidian.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: Markdown",
    ],
)
