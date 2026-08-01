from kubernetes import client, config


def get_k8s_client():
    """
    Load kubeconfig from the local machine
    and return the Kubernetes CoreV1 API client.
    """
    config.load_kube_config()
    return client.CoreV1Api()