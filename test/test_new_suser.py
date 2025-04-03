import subprocess
import difflib
import pytest
import re

# Test parameters
username = "mhyeh"
clusternames = ["lawrencium", "ood_inter", "californium", "nano", "errorexample"]

accounts_condo = [
    "errorexample", "lr_esd2", "lr_oppie", "lr_omega", "lr_alsu",
    "condo_co2seq", "lr_esd1", "lr_axl", "lr_nokomis", "lr_jgicloud",
    "lr_minnehaha", "lr_matminer", "lr_ceder", "lr_qchem", "lr_neugroup",
    "lr_fstheory", "lr_statmech", "lr_farea", "lr_tns"
]

accounts_normal = [
    "lr_cumulus", "lr_chandra", "lr_ninjaone", "lr_amos",
    "lr_essdata", "lr_mhg2", "lr_rncstar", "lr_nanotheory", "lr_geop"
]

## List of python script implementations to test:
# These are run with the --debug flag so that they only print command output.
python_scripts = ["src/new-suser.py", "src/new-suser-v2.py"]

def run_python_script(script, username, cluster, account):
    cmd = ["python3", script, username, cluster, account, "--debug"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def run_bash_reference(username, cluster, account):
    # Run the reference bash script.
    # Ensure that reference.sh is executable (chmod +x test/reference.sh) or call it with sh.
    cmd = ["sh", "test/reference.sh", username, cluster, account]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def normalize_output(text, username, account):
    # Remove debug prefixes
    text = text.replace("DEBUG exec_command: ", "")
    text = text.replace("DEBUG run_command: ", "")
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    # Replace the actual username and account with placeholders so that
    # expected (bash) output, which uses $username/$ACCOUNT, will match.
    text = text.replace(username, "$username")
    text = text.replace(account, "$ACCOUNT")
    return text.strip()

def filter_sacctmgr_calls(text):
    # Only keep the valid slurm command portion from lines that contain "/usr/bin/sacctmgr -i"
    lines = text.splitlines()
    filtered = []
    for line in lines:
        if "/usr/bin/sacctmgr -i" in line:
            # In case the line contains extra output (like from "show account -p" and group messages),
            # split on the last occurrence of "/usr/bin/sacctmgr -i" and prepend it back.
            parts = line.rsplit("/usr/bin/sacctmgr -i", 1)
            command = "/usr/bin/sacctmgr -i" + parts[1]
            # Normalize whitespace in the extracted command.
            command = re.sub(r'\s+', ' ', command).strip()
            if "create user" in command or "modify user" in command:
                filtered.append(command)
    return "\n".join(filtered).strip()

def get_diff(text1, text2, label1, label2):
    diff = list(difflib.unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile=label1,
        tofile=label2
    ))
    return "".join(diff)

@pytest.mark.parametrize("script", python_scripts)
@pytest.mark.parametrize("cluster", clusternames)
@pytest.mark.parametrize("account", accounts_normal)
def test_compare_with_bash(script, cluster, account):
    python_out = run_python_script(script, username, cluster, account)
    bash_out = run_bash_reference(username, cluster, account)
    # Pass username and account to normalize_output for variable substitution.
    norm_python = normalize_output(python_out, username, account)
    norm_bash = normalize_output(bash_out, username, account)
    # Filter the outputs to only include lines with '/usr/bin/sacctmgr'
    filtered_python = filter_sacctmgr_calls(norm_python)
    filtered_bash = filter_sacctmgr_calls(norm_bash)
    diff = get_diff(filtered_bash, filtered_python, "Expected (bash)", "Actual (python)")
    assert filtered_python == filtered_bash, (
        f"Output differs for {script} with cluster '{cluster}' and account '{account}':\n"
        f"Expected (filtered bash output):\n{filtered_bash}\n\n"
        f"Actual (filtered python output):\n{filtered_python}\n\n"
        f"Diff:\n{diff}"
    )
# Additional test: Compare the output of new-suser.py with new-suser-v2.py.
#
# This test runs both scripts in --debug mode and then compares their output.
# If the outputs differ, it prints a unified diff.
@pytest.mark.parametrize("cluster", clusternames)
@pytest.mark.parametrize("account", accounts_normal)
def test_compare_python_versions(cluster, account):
    output_py1 = run_python_script("src/new-suser.py", username, cluster, account)
    output_py2 = run_python_script("src/new-suser-v2.py", username, cluster, account)
    norm_py1 = normalize_output(output_py1)
    norm_py2 = normalize_output(output_py2)
    if norm_py1 != norm_py2:
        diff = get_diff(norm_py1, norm_py2, "new-suser.py --debug (normalized)", "new-suser-v2.py --debug (normalized)")
        pytest.fail(f"Output differs between new-suser.py and new-suser-v2.py for cluster '{cluster}' and account '{account}':\n{diff}")