import subprocess
import os
import sys

# --- Configuration ---
# Define the paths for your scripts and virtual environments
LLM_SCRIPT = "gptResOnly.py"
TRANSLATE_SCRIPT = "translate2English.py"
EVALS_SCRIPT = "getEvals.py"

MAIN_ENV = "main_env"
TRANS_ENV = "trans_env"

# Define your data sections and languages
sections = {
    'Biases_Stereotypes': 'biases_stereo',
    # 'Consent_Autonomy': 'consent_autonomy',
    # 'Harm_Prev': 'harm_prev',
    # 'Legality': 'legality',
    # 'Moral_Judgment': 'moral_judgment'
}

languages = {
    'Arabic': 'Arabic',
    # 'Chinese': 'Chinese',
    # 'English': 'English',
    # 'Hindi': 'Hindi',
    # 'Spanish': 'Spanish',
    # 'Swahili': 'Swahili'
}

rubric_mapping = {
    'Biases_Stereotypes': 'Biases-Rubric.csv',
    'Consent_Autonomy': 'Consent-Rubric.csv',
    'Harm_Prev': 'Safety-Rubric.csv',
    'Legality': 'Legality-Rubric.csv',
    'Moral_Judgment': 'Moral_Judgement-Rubric.csv'
}

def run_script_in_env(script_name, env_name, script_args=None):
    """
    Runs a Python script in a specified virtual environment.
    
    Args:
        script_name (str): The name of the script to run.
        env_name (str): The name of the virtual environment to use.
        script_args (list, optional): A list of arguments to pass to the script.
    
    Returns:
        bool: True if the script ran successfully, False otherwise.
    """
    print(f"\n--- Starting {script_name} in {env_name} ---")
    
    # Determine the Python executable path for the specified virtual environment
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if sys.platform == "win32":
        python_executable = os.path.join(base_dir, env_name, "Scripts", "python.exe")
    else:
        python_executable = os.path.join(base_dir, env_name, "bin", "python")

    if not os.path.exists(python_executable):
        print(f"Error: Python executable not found at '{python_executable}'. Please set up the virtual environment '{env_name}'.")
        return False

    command = [python_executable, os.path.join(base_dir, script_name)]
    if script_args:
        command.extend(script_args)

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print(result.stdout)
        print(f"--- {script_name} completed successfully ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name} in {env_name}:")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running {script_name}: {e}")
        return False
    
def main():
    print("Starting the full workflow for all languages and sections.")
    
    for lang_key, lang_name in languages.items():
        for section_key, section_dir in sections.items():

            print(f"\n{'='*70}")
            print(f"Processing Language: {lang_name}, Section: {section_key}")
            print(f"{'='*70}")

            # Define dynamic file paths based on the current loop
            initial_input_file = f"q_translations/{section_dir}/{lang_name}-{section_key}.csv"
            
            # The output file will be created by the first step and then used by the others
            # This file will accumulate all the new columns
            final_output_file = f"LLMEvals/s_testing/{lang_name}-{section_key}-Evals.csv"
            
            rubric_file = f"rubrics/{rubric_mapping[section_key]}"

            # --- Step 1: Run gptResOnly.py ---
            # Creates the initial output file with LLM responses
            os.makedirs(os.path.dirname(final_output_file), exist_ok=True)
            if not run_script_in_env(LLM_SCRIPT, MAIN_ENV, [initial_input_file, final_output_file, lang_name]):
                print(f"Workflow halted due to an error in gptResOnly.py for {lang_name} - {section_key}.")
                continue

            # --- Step 2: Run translate2English.py ---
            # Appends the translation to the existing output file
            # Now passes the language name as an argument
            if not run_script_in_env(TRANSLATE_SCRIPT, TRANS_ENV, [final_output_file, lang_name]):
                print(f"Workflow halted due to an error in translate2English.py for {lang_name} - {section_key}.")
                continue

            # --- Step 3: Run getEvals.py ---
            # Appends the grades and justifications to the same file
            if not run_script_in_env(EVALS_SCRIPT, MAIN_ENV, [final_output_file, rubric_file]):
                print(f"Workflow halted due to an error in getEvals.py for {lang_name} - {section_key}.")
                continue

    print("\n--- All workflow iterations completed successfully! ---")

if __name__ == "__main__":
    main()
