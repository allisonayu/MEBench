import os
import pandas as pd
from claudeEvals import get_rubric_file, evaluate_response, translate_to_english, client, MODEL_NAME

# Configuration - Update these values
INPUT_FILE = "LLMEvals/Claude/Spanish-Moral_Judgment-Evals-Claude.csv"  # Update with your file path
OUTPUT_FILE = None  # Set to None to overwrite input file, or specify a different output path
QUESTION_INDICES = [27, 28]  # 1-based indices of questions to retry

def retry_questions(csv_file_path, question_indices, output_file=None):
    """
    Retry specific questions in an evaluation file and update their results
    
    Args:
        csv_file_path: Path to the existing evaluation CSV file
        question_indices: List of 1-based question indices to retry
        output_file: Optional, path to save the updated file (default: overwrite original)
    """
    # If no output file specified, overwrite the input file
    if output_file is None:
        output_file = csv_file_path
    
    # Read the existing data
    try:
        df = pd.read_csv(csv_file_path)
    except Exception as e:
        print(f"Error reading file {csv_file_path}: {e}")
        return False
    
    # Convert question numbers to 0-based indices, accounting for header row
    # No need to subtract 1 because pandas handles the header row
    question_indices = [i for i in question_indices if 1 <= i <= len(df)]
    if not question_indices:
        print("No valid question indices provided")
        return False
    
    print(f"Retrying {len(question_indices)} questions from {csv_file_path}...")
    
    # Get section from the input filename (format: Language-Section-Evals-Claude.csv)
    try:
        # Split the filename and get the section part (second part)
        filename_parts = os.path.basename(csv_file_path).split('-')
        if len(filename_parts) >= 2:
            section = filename_parts[1]  # Second part is the section name
        else:
            # Fallback to extracting from path if format is different
            section = os.path.basename(os.path.dirname(csv_file_path)).split('-')[0]
            
        rubric_file = get_rubric_file(section)
        print(f"Using rubric file: {rubric_file}")
        
        with open(rubric_file, 'r', encoding='utf-8') as f:
            rubric = f.read()
    except Exception as e:
        print(f"Error loading rubric: {e}")
        return False
    
    # Process each specified question
    for idx in question_indices:
        if idx > len(df):
            print(f"Warning: Question index {idx} is out of range")
            continue
            
        print(f"\nRetrying question {idx}/{len(df)}...")
        
        # Get the question and other data
        row = df.iloc[idx-1]
        translated_question = row[df.columns[1]]  # Get translated question from 2nd column
        res_language = row.get('Language', 'English')
        
        try:
            # 1. Get completion from Claude API using translated question
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1000,
                temperature=0.7,
                system=f"You are an AI assistant. Answer the following question in {res_language}.",
                messages=[
                    {"role": "user", "content": translated_question}
                ]
            )
            
            # 2. Store Claude's original response in 3rd column
            original_llm_response = response.content[0].text
            response_column = df.columns[2]  # 3rd column for original response
            df.at[idx-1, response_column] = original_llm_response
            
            # 3. Translate the response to English and store in 4th column
            if len(df.columns) > 3:  # If there's a 4th column for translation
                translated_response = None
                if res_language and res_language.lower() != 'english':
                    translated_response = translate_to_english(original_llm_response, res_language)
                    if translated_response is None or translated_response.startswith('[Translation Error'):
                        error_msg = "No response to translate" if translated_response is None else translated_response
                        print(f"Translation failed: {error_msg}")
                        grade = -1
                        justification = f"Translation failed: {error_msg}"
                        raise Exception(justification)
                else:
                    translated_response = original_llm_response
                
                # Store in 4th column (index 3)
                df.at[idx-1, df.columns[3]] = translated_response
            
            # 4. Evaluate using Gemini with the English translated response
            if 'translated_response' in locals() and translated_response:
                grade, justification = evaluate_response(translated_question, translated_response, rubric)
            else:
                grade, justification = -1, "No translated response available for evaluation"
            
        except Exception as e:
            print(f"Error processing question {idx}: {str(e)}")
            grade = -1
            justification = f"Processing error: {str(e)}"
            if 'original_llm_response' not in locals():
                original_llm_response = "[No response generated]"
            if 'translated_response' not in locals():
                translated_response = "[Translation not attempted]"
        
        # Update the row with results
        df.at[idx-1, 'Grade'] = grade
        df.at[idx-1, 'Justification'] = justification
        
        # Save after each question
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"  - Updated question {idx}, Grade: {grade}")
        
    print(f"\nProcessing complete. Results saved to {output_file}")
    return True

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File not found: {INPUT_FILE}")
    else:
        retry_questions(INPUT_FILE, QUESTION_INDICES, OUTPUT_FILE)