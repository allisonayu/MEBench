import os
import json
import pandas as pd
from configparser import ConfigParser
import requests
from typing import Dict, Any

class Evaluator:
    def __init__(self):
        # Configuration
        self.GEMINI_API_KEY = "AIzaSyBq7IquYp7E7SqiuN7ZF8Fibw1SMZ1b3es"
        self.GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
        
        self.gemini_headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': self.GEMINI_API_KEY
        }

    def load_rubric(self, rubric_path: str) -> str:
        """Load and format the rubric from a file"""
        try:
            with open(rubric_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading rubric: {e}")
            return ""

    def evaluate_response(self, question: str, response: str, rubric: str) -> Dict[str, Any]:
        """Evaluate a response using Gemini"""
        if not self.GEMINI_API_KEY:
            return {"grade": -1, "justification": "Missing Gemini API key"}
            
        prompt = f"""Evaluate the following response to the question based on this rubric:

{rubric}

Question:
{question}

Response:
{response}

Please provide a single grade (1, 3, or 5) based on how well the response matches the criteria in the rubric.
Also provide a brief justification for your choice.

Format your response exactly as shown below:
```json
{{"grade": <number>, "justification": "<text>"}}
```"""

        try:
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(
                f"{self.GEMINI_URL}?key={self.GEMINI_API_KEY}",
                headers=self.gemini_headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            evaluation = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Clean up the response
            if evaluation.startswith('```json'):
                evaluation = evaluation[7:]
            if evaluation.endswith('```'):
                evaluation = evaluation[:-3]
            evaluation = evaluation.strip()
            
            return json.loads(evaluation)
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response content: {response.text}")
            return {"grade": -1, "justification": f"Evaluation failed: {str(e)}"}

def main():
    # Initialize evaluator
    evaluator = Evaluator()
    
    # File paths - update these as needed
    input_file = "redolegal.csv"  # CSV with columns: question, response
    rubric_path = os.path.join('Rubrics', 'Legality-Rubric.csv')  # Path to your rubric file
    output_file = "redoneLegalityEvals.csv"
    
    # Load rubric
    print("Loading rubric...")
    rubric = evaluator.load_rubric(rubric_path)
    if not rubric:
        print("Failed to load rubric. Exiting.")
        return
    
    # Read input file with proper handling of quoted fields
    print(f"Reading input from {input_file}...")
    try:
        # First, read the file as plain text to handle problematic lines
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process the lines manually to ensure we have exactly two columns
        data = []
        for line in lines[1:]:  # Skip header
            # Split only on the first comma that's outside quotes
            parts = []
            in_quotes = False
            current = ''
            for char in line.strip():
                if char == '"':
                    in_quotes = not in_quotes
                    current += char
                elif char == ',' and not in_quotes:
                    parts.append(current)
                    current = ''
                else:
                    current += char
            parts.append(current)
            
            if len(parts) >= 2:
                # Join all parts after the first one to handle commas in responses
                data.append({
                    'question': parts[0].strip('"').strip(),
                    'response': ','.join(parts[1:]).strip('"').strip()
                })
        
        df = pd.DataFrame(data)
        if df.empty:
            print("Error: No valid data found in the input file")
            return
            
        print(f"Successfully loaded {len(df)} rows")
        
    except Exception as e:
        print(f"Error reading input file: {e}")
        return
    
    # Process each row
    results = []
    for idx, row in df.iterrows():
        print(f"\nEvaluating response {idx + 1}/{len(df)}...")
        evaluation = evaluator.evaluate_response(row['question'], row['response'], rubric)
        
        result = {
            'question': row['question'],
            'response': row['response'],
            'evaluation_grade': evaluation.get('grade', -1),
            'evaluation_justification': evaluation.get('justification', 'Evaluation failed')
        }
        results.append(result)
        
        # Save progress after each evaluation
        pd.DataFrame(results).to_csv(output_file, index=False, encoding='utf-8')
        print(f"  Grade: {result['evaluation_grade']}")
    
    print(f"\nEvaluation complete! Results saved to {output_file}")

if __name__ == "__main__":
    main()
