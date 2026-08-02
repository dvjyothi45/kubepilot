from kubernetes import client, config

config.load_kube_config()


def get_k8s_client():
    return client.CoreV1Api()


def get_apps_client():
    return client.AppsV1Api()


    