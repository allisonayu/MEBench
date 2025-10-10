import csv
import os
import requests
import json

# OpenRouter API configuration
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = <KEY>

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "<YOUR_SITE_URL>",
    "X-Title": "<YOUR_SITE_NAME>",
}

def process_csv_file(csv_file_path, output_file):
    """
    Process a CSV file containing questions and save responses to output file.
    
    Args:
        csv_file_path (str): Path to the input CSV file
        output_file (str): Path to save the responses
    """
    try:
        # Read questions from CSV
        questions = []
        original_questions = []
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) > 1:  # Ensure we have at least 2 columns
                    questions.append(row[1])  # Use second column as question
                    original_questions.append(row[0])  # Use first column as original question

        # Create output file and write header
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Original Question', 'AI Response'])

        # Process each question
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for question in questions:
                try:
                    # Prepare request payload
                    payload = {
                        "model": "qwen/qwen3-4b:free",
                        "messages": [
                            {
                                "role": "user",
                                "content": question
                            }
                        ]
                    }

                    # Send request to OpenRouter API
                    response = requests.post(
                        API_URL,
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        completion = response.json()
                        response_text = completion['choices'][0]['message']['content']
                    else:
                        error_msg = f"API Error: {response.status_code} - {response.text}"
                        print(f"Error processing question: {question[:50]}... Error: {error_msg}")
                        writer.writerow([original_questions[questions.index(question)], f"ERROR: {error_msg}"])
                        continue

                    # Write original question and response to file
                    writer.writerow([original_questions[questions.index(question)], response_text])
                    print(f"Processed question: {question[:50]}...")  # Print first 50 chars
                    
                except Exception as e:
                    print(f"Error processing question: {question[:50]}... Error: {str(e)}")
                    writer.writerow([question, f"ERROR: {str(e)}"])

    except Exception as e:
        print(f"Error processing file {csv_file_path}: {str(e)}")

if __name__ == "__main__":
    # Define input and output files
    input_file = os.path.join(os.path.dirname(__file__), 'Legality', 'arabic-Legality.csv')# ------------------------------- Change Input File name here     
    output_file = "Arabic-Legality-Responses.csv" # ------------------------------- Change Output File name here     
    
    # Process the specific file
    print(f"Processing file: {input_file}")
    process_csv_file(input_file, output_file)

    print("Processing complete!")
