# Contributing to TECHNEWS_404

Thank you for your interest in contributing to TECHNEWS_404. We welcome contributions from developers of all skill levels. This guide provides instructions on how to contribute code, report bugs, suggest new features, and set up your local development environment.

---

## Code of Conduct

We are committed to maintaining an open, welcoming, and professional environment for all contributors. Please ensure all interactions remain respectful, inclusive, and collaborative.

---

## How Can You Contribute?

### 1. Reporting Bugs

If you find a bug or unexpected behavior:
- Check existing repository issues to see if it has already been reported.
- Open a new GitHub issue with a descriptive title and detailed explanation.
- Include steps to reproduce the issue, expected versus actual behavior, and relevant system details or log outputs.

### 2. Suggesting Enhancements

We welcome proposals for new features or improvements:
- Open an issue outlining your proposal.
- Describe the use case, why the enhancement would be valuable, and any proposed implementation details.

### 3. Submitting Code Changes

To submit code or documentation updates:
- Fork the repository and create a new topic branch from `main`.
- Keep changes focused and concise.
- Ensure all automated tests pass before submitting your Pull Request.

---

## Local Development Setup

### Prerequisites

- Node.js (version 18 or higher)
- Python (version 3.10 or higher)
- Git

### Step-by-Step Environment Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/rutaabali3/TECHNEWS_404.git
   cd TECHNEWS_404
   ```

2. Set up Python virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install pytest requests beautifulsoup4
   ```

3. Configure local environment variables:
   Create a `.env` file or export your Groq API key:
   ```bash
   export GROQ_API_KEY="your_groq_api_key_here"
   ```

---

## Running Tests

Before submitting any code changes, ensure all tests pass locally.

### Frontend JavaScript Tests

Run Node.js native unit tests:
```bash
npm test
```

### Backend Python Tests

Run Python unit tests using `pytest`:
```bash
PYTHONPATH=. python3 -m pytest
```

Alternatively, run using Python's standard `unittest` module:
```bash
python3 -m unittest discover tests
```

---

## Coding Guidelines

- Documentation and commit messages must not contain emojis.
- Write clean, modern ES6+ JavaScript for frontend components without third-party frameworks.
- Follow Python PEP 8 style guidelines for all backend scripts.
- Ensure proper error handling and logging in Python automated tasks.
- Include unit tests for any new utility functions or feature updates.

---

## Pull Request Guidelines

1. Ensure your branch is up to date with the `main` branch.
2. Run all test suites and verify that zero tests fail.
3. Submit a Pull Request targeting the `main` branch with a clear title and detailed description of the changes made.
4. Address any code review comments or feedback promptly.

Thank you for contributing to TECHNEWS_404!
