"""
Module Name: __init__.py

Description:
    Creates and configures the CampusGear Flask application.
    Sets the locations of the presentation templates and static files,
    applies optional configuration settings, and registers the website
    routes with the Flask application.

Inputs:
    test_config (dict, optional): Configuration settings used when
    creating the application, primarily for automated testing.

Outputs:
    Flask application: Returns the configured Flask application
    with the CampusGear website routes registered.

Implementation Author: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
Creation Date: 11/6/26.
Reviewed by: Jake Crawford and John Pannell.
Documentation Author: Jake Crawford and John Pannell.
External Sources / Attribution: Flask documentation - Application Factories.
Code Origin: Newly written for EECS 581 Project 3 with assistance from ChatGPT.
"""

from flask import Flask

def create_app(test_config=None):
    """
    Create and configure the CampusGear Flask application.

    Args:
        test_config (dict, optional): Additional application settings
            that can be supplied when running automated tests.

    Returns:
        Flask: The configured CampusGear application.
    """

    # Initialize the Flask application and specify the locations
    # of the HTML templates and static files.
    app = Flask(
        __name__,
        template_folder="presentation/templates",
        static_folder="presentation/static"
    )

    # Apply optional configuration settings when provided.
    if test_config:
        app.config.update(test_config)

    # Import the website routes from the routes module.
    from .routes import site

    # Register the website blueprint so Flask recognizes its URLs.
    app.register_blueprint(site)

    # Return the configured application for app.py to run.
    return app