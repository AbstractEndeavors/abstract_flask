from time import time
import setuptools
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name='abstract_flask',
    version='0.0.0.1046',
    author='putkoff',
    author_email='partners@abstractendeavors.com',
    description="A composable toolkit for standing up Flask APIs without repeating yourself. Handles blueprint discovery, CORS, request parsing, endpoint introspection, and route generation — so the only code you write is the code that matters.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/AbstractEndeavors/abstract_flask",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
    ],
    install_requires=['flask', 'flask_cors', 'werkzeug'],      # pure-python, phone-clean                                                                                                                                                   
    extras_require={'users': ['abstract_essentials','abstract_apis','abstract_queries', 'psycopg[binary]']},  
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    # Add this line to include wheel format in your distribution
    setup_requires=['wheel'],
)
