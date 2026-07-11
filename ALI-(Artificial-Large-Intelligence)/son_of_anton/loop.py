import os
import time
from dotenv import load_dotenv
from son_of_anton.problem_selector import select_problem
from son_of_anton.reasoning_chain import anton_deep_reason
from son_of_anton.validator import validate_solution
from son_of_anton.brain_writer import write_solution_to_brain
from son_of_anton.visualize_results import generate_anton_visual

def run_anton_loop():
    print("--- Initiating Son of Anton Reasoning Loop ---")
    
    # Load Credentials/.env from project root
    _master_env = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "Credentials",
        ".env"
    )
    if os.path.exists(_master_env):
        load_dotenv(_master_env, override=True)
        print(f"Loaded credentials from: {_master_env}")
    else:
        print(f"Warning: env file not found at {_master_env}")
    # Force UTF-8 stdout on Windows to support emojis/special characters in terminal
    import sys
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    problem = select_problem()
    if not problem:
        print("No unsolved problems found.")
        return

    print(f"Target Problem: {problem}")

    max_iterations = 3
    last_solution = None

    for i in range(max_iterations):
        print(f"\nIteration {i+1}/{max_iterations} - Groq (Llama 3.3 70B) Reasoning...")
        last_solution = anton_deep_reason(problem)

        print("Validating with Gemini...")
        is_valid = validate_solution(problem, last_solution)

        if is_valid:
            print("[SUCCESS] Solution verified as correct!")
            write_solution_to_brain(
                problem=problem,
                solution=last_solution,
                iterations=i + 1,
                status="SOLVED"
            )
            generate_anton_visual(problem)
            return
        else:
            print(f"[REJECTED] Solution rejected. Retrying... ({i+1}/{max_iterations})")
            time.sleep(2)

    # All iterations exhausted — mark as failed so problem_selector skips it next run
    print(f"[WARNING] Max iterations ({max_iterations}) exhausted. Marking problem as FAILED.")
    write_solution_to_brain(
        problem=problem,
        solution=None,              # No valid solution found
        iterations=max_iterations,
        status="FAILED_MAX_ITERATIONS"
    )

if __name__ == "__main__":
    run_anton_loop()

