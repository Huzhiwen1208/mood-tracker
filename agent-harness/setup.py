from setuptools import find_namespace_packages, setup


setup(
    name="cli-anything-mood-tracker",
    version="1.0.0",
    description="CLI-Anything harness for the mood-tracker GitHub Pages app",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    package_data={
        "cli_anything.mood_tracker": ["skills/*.md"],
    },
    install_requires=[
        "click>=8.1,<9",
    ],
    extras_require={
        "dev": [
            "jinja2>=3.1,<4",
            "prompt_toolkit>=3.0,<4",
            "pytest>=8,<9",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-mood-tracker=cli_anything.mood_tracker.mood_tracker_cli:cli",
        ]
    },
    python_requires=">=3.10",
)
