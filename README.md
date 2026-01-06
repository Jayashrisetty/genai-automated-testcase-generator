# Automated Test Case Generation Using GenAI

## Problem Statement
Manual test case writing is time-consuming and error-prone.

## Solution
This project uses static code analysis and Generative AI concepts to automatically generate test cases.

## Architecture
Frontend → AST Parser → GenAI Engine → Test Generator

## Google Technologies Used
- Google AI Studio (Gemini)
- Vertex AI
- Google Cloud Run

## How It Works
1. Upload source code
2. Extract functions using AST
3. Generate test cases automatically
4. Export test files

## Sample Input
sample_code/calculator.py

## Sample Output
generated_tests/test_calculator.py
