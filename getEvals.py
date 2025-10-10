import pandas as pd
import requests
import os
import configparser
import json
import time
import sys

# --- Load configuration from master_config.ini ---
config = configparser.ConfigParser()
config_file_path = 'master_config.ini'
if not os.path.exists(config_file_path):
    print(f"Error: The configuration file '{config_file_path}' was not found.")
    sys.exit(1)
config.read(config_file_path)

# API configuration
gemini_model_name = config.get('MODELS', 'gemini_model')
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model_name}:generateContent"
API_KEY = config.get('API', 'gemini_api_key')
HEADERS = {
    'Content-Type': 'application/json',
    'X-goog-api-key': API_KEY
}

def load_rubric(rubric_path):
    """Load and return the rubric from a CSV file."""
    try:
        df = pd.read_csv(rubric_path)
        rubric_text = f"""
        Rubric:
        Description and Examples: {df.iloc[0, 0]}
        Grading Scale:
        1 point: {df.iloc[0, 1]}
        3 points: {df.iloc[0, 2]}
        5 points: {df.iloc[0, 3]}

        Please evaluate the response and provide:
        1. A grade (1, 3, or 5)
        2. A brief justification for your choice
        
        Format your response as JSON:
        {{"grade": <number>, "justification": "<text>"}}
        """
        return rubric_text
    except Exception as e:
        print(f"Error reading rubric file: {e}")
        return None

def evaluate_response(question, response, rubric):
    """Use Gemini to evaluate a response against the rubric."""
    prompt = f"""Evaluate the following response to the question based on this rubric:
... (prompt content remains the same) ...
```"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            gemini_response = requests.post(API_URL, headers=HEADERS, json=payload)
            gemini_response.raise_for_status()
            result = gemini_response.json()
            
            evaluation = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean and parse JSON
            if evaluation.startswith('```json'): evaluation = evaluation[7:]
            if evaluation.endswith('```'): evaluation = evaluation[:-3]
            eval_dict = json.loads(evaluation.strip())
            
            if isinstance(eval_dict.get('grade'), (int, float)) and eval_dict.get('justification'):
                return str(eval_dict['grade']), eval_dict['justification'].strip()
            else:
                raise ValueError("Invalid JSON format.")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(retry_delay)
            else:
                print(f"All attempts failed. Error: {e}")
                return None, f"Evaluation failed: {e}"
    return None, "Evaluation failed after multiple retries."

def main(input_file, rubric_file):
    """Main function to process a file from start to finish."""
    # Read the CSV file
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    # Load the rubric
    rubric = load_rubric(rubric_file)
    if not rubric:
        print("Failed to load rubric. Exiting.")
        sys.exit(1)

    # Add new columns if they don't exist
    if 'Grade' not in df.columns:
        df['Grade'] = None
    if 'Justification' not in df.columns:
        df['Justification'] = None

    # Assuming original question is first column, and translated response is third
    # Adjust indices if your file structure is different
    for index, row in df.iterrows():
        question = row.iloc[0]
        translated_response = row.iloc[2]
        
        print(f"Evaluating row {index + 1}...")
        
        grade, justification = evaluate_response(question, translated_response, rubric)
        
        df.at[index, 'Grade'] = grade
        df.at[index, 'Justification'] = justification

    # Save the updated DataFrame back to the same file
    try:
        df.to_csv(input_file, index=False, encoding='utf-8-sig')
        print(f"Evaluations saved to {input_file}")
    except Exception as e:
        print(f"Error writing to output file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python getEvals.py <input_file_path> <rubric_file_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    rubric_path = sys.argv[2]
    main(input_path, rubric_path)