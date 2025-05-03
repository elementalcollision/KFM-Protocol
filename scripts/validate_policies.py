# scripts/validate_policies.py
import sys
import os
import glob
import logging
import yaml
from pydantic import ValidationError

# Adjust the path to import from the policy_engine directory
# This assumes the script is run from the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from policy_engine.parser import load_policy_file
except ImportError as e:
    print(f"Error importing policy engine components: {e}")
    print("Ensure the script is run from the project root or policy_engine is in PYTHONPATH.")
    sys.exit(1)

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

POLICY_DIR = "policies" # Define where policy files are stored

def main():
    """
    Finds and validates all policy YAML files.
    Returns 0 on success, 1 on failure.
    """
    # Ensure POLICY_DIR path is relative to the project root
    policy_dir_path = os.path.join(project_root, POLICY_DIR)

    policy_files = glob.glob(f"{policy_dir_path}/**/*.yaml", recursive=True)
    policy_files += glob.glob(f"{policy_dir_path}/**/*.yml", recursive=True) # Also check for .yml

    if not policy_files:
        logging.warning(f"No policy files (*.yaml, *.yml) found in '{policy_dir_path}'. Skipping validation.")
        return 0 # Exit successfully if no policies exist

    logging.info(f"Found {len(policy_files)} policy file(s) in '{policy_dir_path}'. Starting validation...")
    error_count = 0

    for file_path in policy_files:
        relative_path = os.path.relpath(file_path, project_root)
        try:
            load_policy_file(file_path)
            logging.info(f"  [PASS] {relative_path}")
        except (ValidationError, yaml.YAMLError, ValueError, FileNotFoundError) as e:
            logging.error(f"  [FAIL] {relative_path}")
            # Indent the reason for better readability
            reason_lines = str(e).split('\n')
            for i, line in enumerate(reason_lines):
                prefix = "       Reason: " if i == 0 else "               "
                logging.error(f"{prefix}{line}")

            if isinstance(e, ValidationError):
                # Log detailed Pydantic errors
                try:
                    # Attempt to format errors nicely
                    detailed_errors = "\n".join([f"         - {err['loc']}: {err['msg']}" for err in e.errors()])
                    logging.error(f"       Details:\n{detailed_errors}")
                except Exception:
                    logging.error(f"       Details: {e.errors()}") # Fallback
            error_count += 1
        except Exception as e: # Catch unexpected errors
            logging.error(f"  [FAIL] {relative_path}")
            logging.error(f"       Unexpected Error: {e}", exc_info=True)
            error_count += 1

    if error_count > 0:
        logging.error(f"\nValidation failed for {error_count} policy file(s). See logs above.")
        return 1
    else:
        logging.info("\nAll policy files validated successfully.")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 