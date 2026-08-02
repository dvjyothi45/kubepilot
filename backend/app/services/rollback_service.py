import subprocess


def rollback_deployment(deployment_name: str, namespace: str = "default"):
    try:
        subprocess.run(
            [
                "kubectl",
                "rollout",
                "undo",
                f"deployment/{deployment_name}",
                "-n",
                namespace,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        return {
            "message": f"Deployment '{deployment_name}' rolled back successfully"
        }

    except subprocess.CalledProcessError as e:
        return {
            "error": e.stderr
        }