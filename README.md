# CampusGear — Group 18

A web application for University of Kansas students to reserve and borrow equipment while staff manage inventory, checkouts, returns, and maintenance.

## Project Overview

CampusGear provides a centralized platform for managing shared university equipment. Students can browse available equipment, make reservations, view borrowing information, report damage, and communicate with staff. Staff can manage equipment inventory, process checkouts and returns, and handle maintenance requests.

## Technologies

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python with Flask
- **Database:** SQLite
- **Database Queries:** SQL
- **Testing:** pytest / Python testing tools
- **Version Control:** Git and GitHub

## Software Architecture

CampusGear uses a **three-layer architecture with modular design**. Each layer has separate responsibilities to make the application easier to develop, test, and maintain.

### 1. Presentation Layer

Handles the website interfaces and user interactions.

- Login Interface
- Student Interface
- Staff Interface
- HTML templates
- CSS styling and JavaScript functionality

Location: `src/campusgear/presentation/`

### 2. Business Logic Layer

Handles the application's main operations, rules, and processes.

- User and Access Management
- Equipment Management
- Reservation Management
- Loan Management
- Maintenance and Damage Management
- Messaging and Notifications

Location: `src/campusgear/business_logic/`

### 3. Data Access Layer

Handles communication with the SQLite database, including saving, retrieving, and updating application records.

- Database connection and operations

Location: `src/campusgear/data_access/`

The application follows this request flow:

**Presentation Layer → Business Logic Layer → Data Access Layer → SQLite Database**

The Presentation Layer communicates with the Business Logic Layer, which handles application rules and uses the Data Access Layer when database operations are needed.

## Getting Started

Follow these instructions to set up and run CampusGear locally.

### Prerequisites

- Python 3 installed
- Git installed
- Visual Studio Code or another code editor

### 1. Clone the Repository

```bash
git clone https://github.com/540jmc17/PROJECT-3-GROUP18.git
```

Navigate into the project directory:

```bash
cd PROJECT-3-GROUP18
```

### 2. Create a Virtual Environment

```bash
py -m venv .venv
```

### 3. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, allow activation for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Run the Application

From the project root, execute:

```bash
python app.py
```

Open a web browser and navigate to:

```text
http://127.0.0.1:5000
```

To stop the Flask development server, press `Ctrl + C` in the terminal.

## Running Tests

From the project root, run the project's automated tests.

If the project uses pytest:

```bash
python -m pytest
```

If pytest is not installed and is used by the team, add it to `requirements.txt` before running the tests.

## Development Guidelines

- Keep Presentation, Business Logic, and Data Access responsibilities separate.
- Presentation components should communicate with Business Logic rather than directly executing SQL queries.
- Business Logic components should use the Data Access Component for database operations.
- Keep HTML templates inside `presentation/templates/`.
- Keep CSS, JavaScript, and image files inside `presentation/static/`.
- Add automated tests for new functionality.
- Update documentation when application structure or behavior changes.
- Use feature branches when developing new functionality and submit changes through pull requests.
