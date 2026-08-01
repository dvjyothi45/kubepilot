from fastapi import APIRouter, HTTPException
from kubernetes import client

from app.schemas.service import ServiceCreate

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


@router.get("/services")
def list_services():
    v1 = get_k8s_client()

    services = v1.list_service_for_all_namespaces()

    return {
        "services": [
            {
                "name": service.metadata.name,
                "namespace": service.metadata.namespace,
                "type": service.spec.type,
                "cluster_ip": service.spec.cluster_ip,
                "ports": [
                    {
                        "port": port.port,
                        "target_port": port.target_port,
                        "protocol": port.protocol,
                    }
                    for port in service.spec.ports
                ],
            }
            for service in services.items
        ]
    }    

@router.post("/services")
def create_service(service: ServiceCreate):

    v1 = get_k8s_client()

    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=service.name
        ),
        spec=client.V1ServiceSpec(
            selector={
                "app": service.selector
            },
            ports=[
                client.V1ServicePort(
                    port=service.port,
                    target_port=service.target_port,
                )
            ],
            type=service.type,
        ),
    )

    v1.create_namespaced_service(
        namespace="default",
        body=body,
    )

    return {
        "message": f"Service '{service.name}' created successfully"
    }   


@router.delete("/services/{service_name}")
def delete_service(service_name: str):

    v1 = get_k8s_client()

    v1.delete_namespaced_service(
        name=service_name,
        namespace="default",
    )

    return {
        "message": f"Service '{service_name}' deleted successfully"
    }     


@router.get("/pods/{namespace}/{pod_name}/logs")
def get_pod_logs(namespace: str, pod_name: str):

    v1 = get_k8s_client()

    logs = v1.read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        tail_lines=100,
    )

    return {
        "pod": pod_name,
        "namespace": namespace,
        "logs": logs,
    }    

@router.get("/events")
def list_events():

    v1 = get_k8s_client()

    events = v1.list_event_for_all_namespaces()

    return {
        "events": [
            {
                "namespace": event.metadata.namespace,
                "reason": event.reason,
                "type": event.type,
                "message": event.message,
                "object": event.involved_object.name,
                "time": event.last_timestamp or event.event_time,
            }
            for event in events.items
        ]
    }



@router.get("/dashboard")
def dashboard_summary():

    v1 = get_k8s_client()
    apps = get_apps_client()

    namespaces = v1.list_namespace().items
    pods = v1.list_pod_for_all_namespaces().items
    services = v1.list_service_for_all_namespaces().items
    deployments = apps.list_deployment_for_all_namespaces().items
    nodes = v1.list_node().items

    return {
        "nodes": len(nodes),
        "namespaces": len(namespaces),
        "pods": len(pods),
        "deployments": len(deployments),
        "services": len(services),
    }


@router.get("/nodes")
def list_nodes():

    v1 = get_k8s_client()

    nodes = v1.list_node()

    return {
        "nodes": [
            {
                "name": node.metadata.name,
                "status": node.status.conditions[-1].type,
                "kubelet_version": node.status.node_info.kubelet_version,
                "os": node.status.node_info.os_image,
                "architecture": node.status.node_info.architecture,
            }
            for node in nodes.items
        ]
    }    

@router.get("/nodes/{node_name}")
def get_node_details(node_name: str):

    v1 = get_k8s_client()

    node = v1.read_node(name=node_name)

    return {
        "name": node.metadata.name,
        "os": node.status.node_info.os_image,
        "architecture": node.status.node_info.architecture,
        "kernel_version": node.status.node_info.kernel_version,
        "kubelet_version": node.status.node_info.kubelet_version,
        "container_runtime": node.status.node_info.container_runtime_version,
        "addresses": [
            {
                "type": address.type,
                "address": address.address,
            }
            for address in node.status.addresses
        ],
    }    


@router.get("/cluster/health")
def cluster_health():

    v1 = get_k8s_client()
    apps = get_apps_client()

    nodes = v1.list_node().items
    pods = v1.list_pod_for_all_namespaces().items
    deployments = apps.list_deployment_for_all_namespaces().items
    services = v1.list_service_for_all_namespaces().items

    ready_nodes = sum(
        1
        for node in nodes
        if any(
            condition.type == "Ready" and condition.status == "True"
            for condition in node.status.conditions
        )
    )

    running_pods = sum(
        1
        for pod in pods
        if pod.status.phase == "Running"
    )

    failed_pods = sum(
        1
        for pod in pods
        if pod.status.phase == "Failed"
    )

    pending_pods = sum(
        1
        for pod in pods
        if pod.status.phase == "Pending"
    )

    return {
        "cluster_status": "Healthy" if ready_nodes == len(nodes) else "Warning",
        "nodes": {
            "total": len(nodes),
            "ready": ready_nodes,
        },
        "pods": {
            "total": len(pods),
            "running": running_pods,
            "pending": pending_pods,
            "failed": failed_pods,
        },
        "deployments": len(deployments),
        "services": len(services),
    }    