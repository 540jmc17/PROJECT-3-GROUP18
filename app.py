"""
Module Name: app.py

Description:
    Serves as the entry point for the CampusGear Flask application.
    Adds the src directory to Python's module search path, imports
    the application factory from the campusgear package, and creates
    the Flask application.

    When executed directly, this file starts Flask's development
    server so team members can run and test the website locally.

Inputs:
    No required command-line inputs.
    Application configuration is handled by the create_app function.

Outputs:
    Flask application instance.
    Runs the local Flask development server when executed directly.

Implementation Author: Jake Crawford and John Pannell, with substantial code-drafting assistance from ChatGPT Pro-6.
Creation Date: 11/6/26.
Reviewed by: Jake Crawford and John Pannell.
Documentation Author: Jake Crawford and John Pannell.
External Sources / Attribution: Python and Flask documentation.
Code Origin: Newly written for EECS 581 Project 3 with assistance from ChatGPT.
"""

import sys
from pathlib import Path

# Add src to Python's module search path.
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

# Import the create_app function from the campusgear package.
# This function sets up the Flask application and its routes.
from campusgear import create_app

# Create the CampusGear application using the imported function.
app = create_app()


# Run the Flask development server when this file is executed directly.
# This allows developers to test the website locally.
if __name__ == "__main__":
    app.run()