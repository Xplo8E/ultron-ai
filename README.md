# Ultron Code Reviewer 🤖

Ultron is an AI-powered Command Line Interface (CLI) tool that leverages Google's Gemini API to perform comprehensive code reviews. It helps developers identify security vulnerabilities, bugs, and areas for improvement in their code, providing actionable feedback directly in the terminal.

## Features

-   **AI-Powered Analysis**: Utilizes Google Gemini for deep code understanding.
-   **Security Focused**: Prioritizes identification of exploitable vulnerabilities.
-   **Detailed Feedback**: Provides descriptions, impact analysis, Proof of Concept (POC) ideas, and suggestions.
-   **Multi-Language Support**: Can review code in various programming languages.
-   **User-Friendly CLI**: Easy to integrate into development workflows.
-   **Rich Output**: Formatted terminal output using Rich for better readability.
-   **JSON Output**: Option for structured JSON output for programmatic use.
-   **Contextual Reviews**: Allows providing additional context for more targeted analysis.

## Prerequisites

-   Python 3.8 or higher.
-   A Google Gemini API Key. You can obtain one from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Installation

1.  **Clone the Repository (Optional):**
    If you want to modify the code or contribute:
    ```bash
    git clone [https://github.com/yourusername/ultron-cli.git](https://github.com/yourusername/ultron-cli.git) # Replace with your actual repo URL
    cd ultron-cli
    ```

2.  **Set Up a Virtual Environment (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    If you cloned the repository:
    ```bash
    pip install -r requirements.txt
    ```
    Then, to make the `ultron` command available from anywhere (development mode):
    ```bash
    pip install -e .
    ```
    Alternatively, if you plan to distribute it or install from a source distribution:
    ```bash
    # Assuming you have the setup.py and the src directory
    # pip install .
    ```

4.  **Configure API Key:**
    Create a file named `.env` in the root of the project directory (e.g., `ultron-cli/.env` if you cloned it, or in the directory where you run `ultron` if installed globally and it can't find it otherwise).
    Add your Gemini API key to this file:
    ```env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    ```
    Replace `"YOUR_GEMINI_API_KEY_HERE"` with your actual API key.
    Ultron will also check for the `GEMINI_API_KEY` environment variable if the `.env` file is not found or the key isn't in it.

## Usage

Once installed, you can use the `ultron` command from your terminal.

**Basic Command:**
```bash
ultron review --file <path_to_your_code_file> --language <language>