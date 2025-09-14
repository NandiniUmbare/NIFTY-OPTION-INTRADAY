# Deploying the Trading Terminal on PythonAnywhere

This guide provides step-by-step instructions for deploying the Flask web application to a free PythonAnywhere account.

---

### Prerequisites

*   A free PythonAnywhere account.
*   A Git repository (e.g., on GitHub) containing the project code.

---

### Step 1: Set up the Environment in a Bash Console

1.  **Open a Bash Console:**
    *   From your PythonAnywhere dashboard, go to the **Consoles** tab.
    *   Start a new **Bash** console.

2.  **Clone Your Repository:**
    *   In the Bash console, clone your Git repository using its HTTPS URL.
    *   Run: `git clone [YOUR_REPOSITORY_URL]`
    *   This will create a directory for your project. Note the name of this directory (e.g., `my-trading-app`).

3.  **Set up a Virtual Environment:**
    *   It's a best practice to use a virtual environment to manage your project's dependencies.
    *   Run the following command to create a virtual environment using Python 3.9 (you can choose a different version if you prefer).
    *   `mkvirtualenv --python=/usr/bin/python3.9 my-virtualenv`
    *   (You can change `my-virtualenv` to a name of your choice). Your console prompt will change to indicate that you are now inside the virtual environment.

4.  **Install Dependencies:**
    *   Navigate into your project directory: `cd [YOUR_PROJECT_DIRECTORY_NAME]`
    *   Install the required packages using the `requirements.txt` file:
    *   `pip install -r requirements.txt`

### Step 2: Configure the Web App

5.  **Create the Web App:**
    *   Go to the **Web** tab on your PythonAnywhere dashboard.
    *   Click **Add a new web app**.
    *   Follow the prompts. Your domain name will be `[your-username].pythonanywhere.com`.
    *   When you get to the "Select a Python web framework" step, choose **Manual configuration**.
    *   Choose the same Python version you used for your virtual environment (e.g., Python 3.9).

6.  **Configure the WSGI File:**
    *   This is the most important step. It tells PythonAnywhere how to run your Flask application.
    *   On the web app configuration page, scroll down to the **Code** section and click on the link to your WSGI file (it will be something like `/var/www/[your-username]_pythonanywhere_com_wsgi.py`).
    *   **Delete all the example code** in that file and replace it with this:
        ```python
        import sys
        import os

        # Add your project's directory to the Python path
        project_home = '/home/[YOUR_PYTHONANYWHERE_USERNAME]/[YOUR_PROJECT_DIRECTORY_NAME]'
        if project_home not in sys.path:
            sys.path.insert(0, project_home)

        # Import the Flask app object from your web_app.py file
        from web_app import app as application
        ```
    *   **IMPORTANT:** Replace `[YOUR_PYTHONANYWHERE_USERNAME]` and `[YOUR_PROJECT_DIRECTORY_NAME]` with your actual details. For example, if your username is `johnsmith` and your project directory is `my-trading-app`, the `project_home` path would be `/home/johnsmith/my-trading-app`.
    *   Save the file.

### Step 3: Finalize and Reload

7.  **Set the Virtual Environment Path:**
    *   Go back to the **Web** tab.
    *   In the "Virtualenv" section, enter the path to your virtual environment. It will be: `/home/[YOUR_PYTHONANYWHERE_USERNAME]/.virtualenvs/my-virtualenv`.
    *   (Replace `[YOUR_PYTHONANYWHERE_USERNAME]` and `my-virtualenv` with your details).

8.  **Reload the Web App:**
    *   At the top of the **Web** tab, click the big green **Reload** button.
    *   Wait a few moments, and then navigate to your site at `http://[your-username].pythonanywhere.com`.

### Step 4: Final Configuration

9.  **Update Kite Redirect URL:**
    *   You must update your Kite Connect app's **Redirect URL** to use your new PythonAnywhere domain.
    *   Go to your Kite Developer portal, edit your app, and set the Redirect URL to:
    *   `http://[your-username].pythonanywhere.com/connect/kite`

Your trading terminal application should now be running live! If you encounter any errors, you can check the **Error log** and **Server log** on the PythonAnywhere **Web** tab.
