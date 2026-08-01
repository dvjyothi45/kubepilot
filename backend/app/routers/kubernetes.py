from fastapi import APIRouter, HTTPException
from kubernetes import client

from app.schemas.scale import ScaleDeployment

from app.kubernetes.client import get_k8s_client, get_apps_client
from app.schemas.deployment import DeploymentCreate

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

@router.post("/deployments")
def create_deployment(deployment: DeploymentCreate):

    apps_v1 = client.AppsV1Api()

    container = client.V1Container(
        name=deployment.name,
        image=deployment.image,
        ports=[
            client.V1ContainerPort(container_port=80)
        ],
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": deployment.name}
        ),
        spec=client.V1PodSpec(
            containers=[container]
        ),
    )

    selector = client.V1LabelSelector(
        match_labels={"app": deployment.name}
    )

    spec = client.V1DeploymentSpec(
        replicas=deployment.replicas,
        selector=selector,
        template=template,
    )

    body = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(
            name=deployment.name
        ),
        spec=spec,
    )

    client.AppsV1Api().create_namespaced_deployment(
        namespace="default",
        body=body,
    )

    return {
        "message": f"Deployment '{deployment.name}' created successfully"
    }        


@router.get("/deployments")
def list_deployments():
    apps_v1 = get_apps_client()

    deployments = apps_v1.list_namespaced_deployment(namespace="default")

    return {
        "deployments": [
            {
                "name": dep.metadata.name,
                "replicas": dep.spec.replicas,
                "available_replicas": dep.status.available_replicas or 0,
                "ready_replicas": dep.status.ready_replicas or 0,
                "created_at": dep.metadata.creation_timestamp,
            }
            for dep in deployments.items
        ]
    }    


@router.put("/deployments/{deployment_name}/scale")
def scale_deployment(
    deployment_name: str,
    scale: ScaleDeployment,
):
    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    deployment.spec.replicas = scale.replicas

    apps_v1.patch_namespaced_deployment(
        name=deployment_name,
        namespace="default",
        body=deployment,
    )

    return {
        "message": f"Deployment '{deployment_name}' scaled to {scale.replicas} replicas"
    }

@router.delete("/deployments/{deployment_name}")
def delete_deployment(deployment_name: str):
    apps_v1 = get_apps_client()

    apps_v1.delete_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    return {
        "message": f"Deployment '{deployment_name}' deleted successfully"
    }        