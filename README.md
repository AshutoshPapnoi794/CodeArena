# Interactive DSA Roadmap

An interactive, web-based visualization of a Data Structures and Algorithms learning path. Built with Flask and D3.js, this application provides a guided curriculum, tracks user progress, and offers a dynamic, engaging interface for learning.

## Features

- **Interactive Graph Visualization:** A D3.js force-directed graph shows the entire DSA roadmap and topic dependencies.
- **User Progress Tracking:** Progress is saved in a database, allowing users to track completed problems across sessions and devices.
- **User Authentication:** Secure user signup and login system using Flask-Login and Bcrypt.
- **Guided Learning Path:** Problems on topic pages are sorted by sub-topic and difficulty (Easy -> Hard) to provide a smooth learning curve.
- **Dynamic Unlocking:** Topics on the main roadmap unlock only after the user completes 50% of the prerequisite topics.
- **Advanced Problem Curation:** A robust "signal score" ranks problems based on like ratios, submission volume, and acceptance rates to surface the highest quality content.
- **Similar Questions:** Each problem links to similar questions, encouraging deeper exploration of concepts.
- **Polished UI/UX:** Features a "cosmic nebula" theme, animated particle background, and satisfying UI animations like animated strikethroughs on completed tasks.

## Setup & Installation

To run this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    cd YOUR_REPOSITORY_NAME
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000`.

## Usage

1.  Navigate to the signup page to create a new account.
2.  Explore the main roadmap. Click on any unlocked topic to view the problem list.
3.  As you solve problems on LeetCode, check them off on the topic page to save your progress.
4.  Watch as your progress bars fill up on the main roadmap and new topics unlock!