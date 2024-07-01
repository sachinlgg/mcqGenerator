from setuptools import find_packages, setup

setup(
    name='MCQGenerator',
    version='0.0.1',
    author='Sachin',
    author_email='sachin.plaksha@gmail.com',
    install_requires=['openai', 'langchain', 'streamlit', 'python-dotenv', 'PyPDF2'],
    packages=find_packages()
)
