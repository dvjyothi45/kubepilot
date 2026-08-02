import subprocess


def get_node_metrics():
    result = subprocess.check_output(
        ["kubectl", "top", "nodes"],
        text=True,
    )

    return result


def get_pod_metrics():
    result = subprocess.check_output(
        ["kubectl", "top", "pods"],
        text=True,
    )

    return result