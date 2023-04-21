from setuptools import setup

with open("README.md", "r") as file:
    long_description = file.read()


setup(
    name="chlorophyll",
    version="0.3.1",
    description="A module that fills your code with color - syntax highlighted text box widget for Tkinter.",
    author="rdbende",
    author_email="rdbende@gmail.com",
    url="https://gitlab.com/rdbende/chlorophyll",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["pygments", "toml", "tklinenums", "pyperclip"],
    python_requires=">=3.7",
    license="MIT license",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Typing :: Typed",
    ],
    packages=["chlorophyll"],
    package_data={"chlorophyll": ["colorschemes/*"]},
)
