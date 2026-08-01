from fastapi import APIRouter, HTTPException

from app.kubernetes.client import get_k8s_client

router = APIRouter(
    prefix="/kubernetes",
    tags=["Kubernetes"],
)


@router.get("/namespaces")
def list_namespaces():
    v1 = get_k8s_client()

    namespaces = v1.list_namespace()

    return {
        "namespaces": [
            ns.metadata.name
            for ns in namespaces.items
        ]
    }


@router.get("/pods")
def list_pods():
    v1 = get_k8s_client()

    pods = v1.list_pod_for_all_namespaces(watch=False)

    return {
        "pods": [
            {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "pod_ip": pod.status.pod_ip,
            }
            for pod in pods.items
        ]
    }


@router.get("/pods/{namespace}")
def list_pods_by_namespace(namespace: str):
    v1 = get_k8s_client()

    pods = v1.list_namespaced_pod(namespace=namespace)

    return {
        "namespace": namespace,
        "pods": [
            {
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "pod_ip": pod.status.pod_ip,
            }
            for pod in pods.items
        ]
    }


@router.get("/pod/{namespace}/{pod_name}")
def get_pod_details(namespace: str, pod_name: str):
    v1 = get_k8s_client()

    try:
        pod = v1.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "pod_ip": pod.status.pod_ip,
            "host_ip": pod.status.host_ip,
            "restart_policy": pod.spec.restart_policy,
            "creation_timestamp": pod.metadata.creation_timestamp,
            "containers": [
                {
                    "name": container.name,
                    "image": container.image,
                }
                for container in pod.spec.containers
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))