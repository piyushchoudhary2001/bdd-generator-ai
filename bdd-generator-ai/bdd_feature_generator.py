import os
import json
from typing import Dict, Any

# This script will take the output of java_code_analyzer.py (controllers.json)
# and generate BDD Gherkin feature files for each API endpoint, including positive and negative scenarios.
# It will also prepare a stub for step definition generation.

def load_analysis(json_path: str) -> Dict[str, Any]:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def scenario_for_endpoint(controller, endpoint, dtos, validations, exceptions, service_calls):
    """
    Generate positive and negative BDD scenarios for a given endpoint, including service calls.
    """
    feature_lines = []
    feature_lines.append(f"Feature: {endpoint['name']} endpoint in {controller['name']}")
    feature_lines.append("")
    # Positive scenario
    feature_lines.append(f"  Scenario: Successful call to {endpoint['name']}")
    feature_lines.append(f"    Given valid input for {endpoint['name']}")
    feature_lines.append(f"    When the API is called")
    feature_lines.append(f"    Then the response should indicate success")
    feature_lines.append("")
    # Negative scenarios from validations
    for v in validations:
        feature_lines.append(f"  Scenario: Validation error - {v}")
        feature_lines.append(f"    Given invalid input that triggers {v}")
        feature_lines.append(f"    When the API is called")
        feature_lines.append(f"    Then the response should indicate a validation error for {v}")
        feature_lines.append("")
    # Negative scenarios from exceptions
    for e in exceptions:
        feature_lines.append(f"  Scenario: Exception - {e}")
        feature_lines.append(f"    Given a situation that causes {e}")
        feature_lines.append(f"    When the API is called")
        feature_lines.append(f"    Then the response should indicate an error for {e}")
        feature_lines.append("")
    # Scenarios for service calls
    for call in service_calls:
        feature_lines.append(f"  Scenario: Dependency call - {call}")
        feature_lines.append(f"    Given the API depends on {call}")
        feature_lines.append(f"    When the API is called")
        feature_lines.append(f"    Then the response should reflect the result of {call}")
        feature_lines.append("")
    return '\n'.join(feature_lines)

def generate_bdd_features(analysis: Dict[str, Any], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for controller in analysis.get('controllers', []):
        for endpoint in controller.get('endpoints', []):
            dtos = analysis.get('dtos', [])
            validations = analysis.get('validations', [])
            exceptions = analysis.get('exceptions', [])
            service_calls = endpoint.get('service_calls', [])
            feature_content = scenario_for_endpoint(controller, endpoint, dtos, validations, exceptions, service_calls)
            feature_file = os.path.join(output_dir, f"{controller['name']}_{endpoint['name']}.feature")
            with open(feature_file, 'w', encoding='utf-8') as f:
                f.write(feature_content)
            print(f"Generated: {feature_file}")

# --- Step Definition Generator/Updater ---
def extract_steps_from_feature(feature_content: str):
    """
    Extract Given/When/Then steps from a Gherkin feature string.
    """
    import re
    steps = set()
    for line in feature_content.splitlines():
        line = line.strip()
        if line.startswith("Given ") or line.startswith("When ") or line.startswith("Then "):
            # Remove parameters for step definition matching
            step = re.sub(r'\s+<[^>]+>', '', line)
            steps.add(step)
    return steps

def find_existing_step_defs(step_def_dir: str):
    """
    Find all existing step definition method names in Java files in the given directory.
    """
    import re
    step_defs = set()
    for root, _, files in os.walk(step_def_dir):
        for file in files:
            if file.endswith('.java'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for @Given/@When/@Then annotations
                    for match in re.finditer(r'@(Given|When|Then)\("([^"]+)"\)', content):
                        step_defs.add(match.group(2))
    return step_defs

def generate_java_step_def(step: str) -> str:
    """
    Generate a Java method stub for a Cucumber step definition.
    """
    import re
    annotation = step.split(' ', 1)[0]
    step_text = step[len(annotation):].strip()
    method_name = re.sub(r'[^a-zA-Z0-9]', '_', step_text).lower()
    return f'''    @{annotation}("{step_text}")\n    public void {method_name}() {{\n        // TODO: Implement step\n    }}\n'''

def update_or_create_step_defs(feature_dir: str, step_def_dir: str):
    """
    For each feature file, ensure all steps have a Java step definition.
    If not present, append stub to a StepDefinitions.java file.
    """
    all_steps = set()
    for file in os.listdir(feature_dir):
        if file.endswith('.feature'):
            with open(os.path.join(feature_dir, file), 'r', encoding='utf-8') as f:
                feature_content = f.read()
                all_steps |= extract_steps_from_feature(feature_content)
    existing_steps = find_existing_step_defs(step_def_dir)
    missing_steps = all_steps - existing_steps
    if not missing_steps:
        print("All step definitions already exist.")
        return
    step_def_file = os.path.join(step_def_dir, 'StepDefinitions.java')
    with open(step_def_file, 'a', encoding='utf-8') as f:
        for step in missing_steps:
            f.write(generate_java_step_def(step))
            f.write('\n')
    print(f"Added {len(missing_steps)} new step definitions to {step_def_file}")

# --- CLI update ---
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate BDD feature files and Java step definitions from Java API analysis JSON.")
    parser.add_argument("analysis_json", help="Path to controllers.json from java_code_analyzer.py")
    parser.add_argument("--output_dir", default="features", help="Directory to write .feature files")
    parser.add_argument("--step_def_dir", default="stepdefs", help="Directory for Java step definitions")
    args = parser.parse_args()
    analysis = load_analysis(args.analysis_json)
    generate_bdd_features(analysis, args.output_dir)
    os.makedirs(args.step_def_dir, exist_ok=True)
    update_or_create_step_defs(args.output_dir, args.step_def_dir)
    print(f"All feature files and step definitions generated.")

if __name__ == "__main__":
    main()
