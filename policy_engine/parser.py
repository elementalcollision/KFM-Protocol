import yaml
from typing import List, Dict, Any
from pydantic import ValidationError
import logging

# Assuming models are in the same directory or package
from .models import Policy, PolicyFile

logger = logging.getLogger(__name__)

def load_policy_file(file_path: str) -> List[Policy]:
    """
    Loads KFM policies from a YAML file, validates them against the Pydantic models,
    and returns a list of valid Policy objects.

    Args:
        file_path: The path to the policy YAML file.

    Returns:
        A list of validated Policy objects.

    Raises:
        FileNotFoundError: If the specified file path does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        ValidationError: If the policy data does not conform to the PolicyFile schema.
        ValueError: If the top-level structure is incorrect (e.g., missing 'policies' key).
    """
    logger.info(f"Loading policy file from: {file_path}")
    try:
        with open(file_path, 'r') as f:
            raw_data = yaml.safe_load(f)

        if not isinstance(raw_data, dict) or 'policies' not in raw_data:
            logger.error(f"Invalid policy file structure in {file_path}: Missing top-level 'policies' key.")
            raise ValueError("Invalid policy file structure: Missing top-level 'policies' key.")

        # Validate the entire file structure using PolicyFile
        policy_file_obj = PolicyFile.parse_obj(raw_data)

        logger.info(f"Successfully loaded and validated {len(policy_file_obj.policies)} policies from {file_path}.")
        return policy_file_obj.policies

    except FileNotFoundError:
        logger.error(f"Policy file not found at path: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        raise
    except ValidationError as e:
        logger.error(f"Policy validation failed for file {file_path}: {e}")
        # Consider logging more detailed errors from e.errors() if needed
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading policy file {file_path}: {e}")
        raise

def serialize_policy_file(policies: List[Policy], file_path: str) -> None:
    """
    Serializes a list of Policy objects into YAML format and writes to a file.

    Args:
        policies: A list of Policy objects to serialize.
        file_path: The path to write the output YAML file.

    Raises:
        IOError: If there is an error writing the file.
        Exception: For other unexpected errors during serialization.
    """
    logger.info(f"Serializing {len(policies)} policies to file: {file_path}")
    try:
        policy_file_obj = PolicyFile(policies=policies)
        # Use Pydantic's dict() method with by_alias=True if needed for Enum serialization
        # Exclude None to keep the YAML cleaner
        data_to_dump = policy_file_obj.dict(exclude_none=True)

        with open(file_path, 'w') as f:
            yaml.dump(data_to_dump, f, default_flow_style=False, sort_keys=False, indent=2)

        logger.info(f"Successfully serialized policies to {file_path}.")

    except IOError as e:
        logger.error(f"Error writing policy file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during policy serialization to {file_path}: {e}")
        raise

# Example usage (optional, can be removed or placed under if __name__ == '__main__'):
# if __name__ == '__main__':
#     try:
#         # Create a dummy policy file policies.yaml first
#         # with open('policies.yaml', 'w') as f:
#         #     f.write('''
#         # policies:
#         #   - id: policy-test-001
#         #     name: "Test Policy"
#         #     conditions:
#         #       - type: time_in_state
#         #         operator: ">="
#         #         value: "1 day"
#         #     actions:
#         #       - type: log
#         #         message: "Policy triggered"
#         # ''')
#         loaded_policies = load_policy_file('policies.yaml')
#         print(f"Loaded {len(loaded_policies)} policies.")
#         if loaded_policies:
#             print("First policy:", loaded_policies[0])
#         # You could also test serialization here
#         # serialize_policy_file(loaded_policies, 'policies_out.yaml')
#     except Exception as e:
#         print(f"Error: {e}") 