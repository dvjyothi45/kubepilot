from fastapi import APIRouter, HTTPException
from kubernetes import client


from app.schemas.namespace import NamespaceCreate
from app.schemas.labels import LabelsUpdate

from typing import Optional

from app.services.rollback_service import rollback_deployment

from app.schemas.annotations import AnnotationsUpdate

from app.schemas.configmap_update import ConfigMapUpdate
from app.schemas.secret_update import SecretUpdate

import yaml
from app.schemas.yaml import YAMLManifest
from kubernetes.utils import create_from_dict

from app.services.metrics_service import (
    get_node_metrics,
    get_pod_metrics,
)

from app.schemas.pvc import PVCCreate

from app.schemas.configmap import ConfigMapCreate

from app.schemas.secret import SecretCreate
import base64

from datetime import datetime
from fastapi import HTTPException

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
def create_deployment(
    deployment: DeploymentCreate,
    namespace: str = "default",
):

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
    namespace=namespace,
    body=body,
)

    return {
    "message": f"Deployment '{deployment.name}' created successfully in namespace '{namespace}'"
}       


@router.get("/deployments")
def list_deployments(namespace: str = "default"):
    apps_v1 = get_apps_client()

    deployments = apps_v1.list_namespaced_deployment(
        namespace=namespace
    )

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
def delete_deployment(
    deployment_name: str,
    namespace: str = "default",
    confirm: bool = False,
):
    apps_v1 = get_apps_client()

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Set confirm=true to delete the deployment."
        )

    apps_v1.delete_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
    )

    return {
        "message": f"Deployment '{deployment_name}' deleted successfully from namespace '{namespace}'"
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
def delete_service(
    service_name: str,
    namespace: str = "default",
):
    v1 = get_k8s_client()

    v1.delete_namespaced_service(
        name=service_name,
        namespace=namespace,
    )

    return {
        "message": f"Service '{service_name}' deleted successfully from namespace '{namespace}'"
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


@router.get("/replicasets")
def list_replicasets():
    apps_v1 = get_apps_client()

    replicasets = apps_v1.list_namespaced_replica_set(
        namespace="default"
    )

    return {
        "replicasets": [
            {
                "name": rs.metadata.name,
                "replicas": rs.spec.replicas,
                "ready": rs.status.ready_replicas or 0,
            }
            for rs in replicasets.items
        ]
    }    


@router.get("/metrics/nodes")
def node_metrics():

    return {
        "metrics": get_node_metrics()
    }    


@router.get("/metrics/pods")
def pod_metrics():

    return {
        "metrics": get_pod_metrics()
    }    


@router.post("/deployments/{deployment_name}/restart")
def restart_deployment(
    deployment_name: str,
    namespace: str = "default",
):

    apps_v1 = get_apps_client()

    try:
        deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
     )

        # Create annotations dictionary if it doesn't exist
        if deployment.spec.template.metadata.annotations is None:
            deployment.spec.template.metadata.annotations = {}

        deployment.spec.template.metadata.annotations[
            "kubectl.kubernetes.io/restartedAt"
        ] = datetime.utcnow().isoformat()

        apps_v1.patch_namespaced_deployment(
    name=deployment_name,
    namespace=namespace,
    body=deployment,
)

        return {
    "message": f"Deployment '{deployment_name}' restarted successfully in namespace '{namespace}'"
}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  


@router.post("/configmaps")
def create_configmap(configmap: ConfigMapCreate):

    v1 = get_k8s_client()

    body = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(
            name=configmap.name
        ),
        data=configmap.data,
    )

    v1.create_namespaced_config_map(
        namespace="default",
        body=body,
    )

    return {
        "message": f"ConfigMap '{configmap.name}' created successfully"
    }        


@router.get("/configmaps")
def list_configmaps():

    v1 = get_k8s_client()

    configmaps = v1.list_namespaced_config_map(
        namespace="default"
    )

    return {
        "configmaps": [
            {
                "name": cm.metadata.name,
                "data": cm.data,
            }
            for cm in configmaps.items
        ]
    }    

@router.put("/configmaps/{configmap_name}")
def update_configmap(
    configmap_name: str,
    configmap: ConfigMapUpdate,
    namespace: str = "default",
):
    v1 = get_k8s_client()

    existing = v1.read_namespaced_config_map(
        name=configmap_name,
        namespace=namespace,
    )

    existing.data = configmap.data

    v1.patch_namespaced_config_map(
        name=configmap_name,
        namespace=namespace,
        body=existing,
    )

    return {
        "message": (
            f"ConfigMap '{configmap_name}' updated successfully in namespace '{namespace}'"
        ),
        "data": existing.data,
    }

@router.delete("/configmaps/{configmap_name}")
def delete_configmap(
    configmap_name: str,
    namespace: str = "default",
):
    v1 = get_k8s_client()

    v1.delete_namespaced_config_map(
        name=configmap_name,
        namespace=namespace,
    )

    return {
        "message": f"ConfigMap '{configmap_name}' deleted successfully from namespace '{namespace}'"
    }



@router.post("/secrets")
def create_secret(secret: SecretCreate):

    v1 = get_k8s_client()

    encoded_data = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in secret.data.items()
    }

    body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name=secret.name
        ),
        data=encoded_data,
        type="Opaque",
    )

    v1.create_namespaced_secret(
        namespace="default",
        body=body,
    )

    return {
        "message": f"Secret '{secret.name}' created successfully"
    }    

@router.get("/secrets")
def list_secrets():

    v1 = get_k8s_client()

    secrets = v1.list_namespaced_secret(
        namespace="default"
    )

    return {
        "secrets": [
            {
                "name": secret.metadata.name,
                "type": secret.type,
            }
            for secret in secrets.items
        ]
    }    

@router.put("/secrets/{secret_name}")
def update_secret(
    secret_name: str,
    secret: SecretUpdate,
    namespace: str = "default",
):
    v1 = get_k8s_client()

    existing = v1.read_namespaced_secret(
        name=secret_name,
        namespace=namespace,
    )

    encoded_data = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in secret.data.items()
    }

    existing.data = encoded_data

    v1.patch_namespaced_secret(
        name=secret_name,
        namespace=namespace,
        body=existing,
    )

    return {
        "message": f"Secret '{secret_name}' updated successfully in namespace '{namespace}'"
    }

@router.delete("/secrets/{secret_name}")
def delete_secret(
    secret_name: str,
    namespace: str = "default",
):
    v1 = get_k8s_client()

    v1.delete_namespaced_secret(
        name=secret_name,
        namespace=namespace,
    )

    return {
        "message": f"Secret '{secret_name}' deleted successfully from namespace '{namespace}'"
    }



@router.post("/persistentvolumeclaims")
def create_pvc(pvc: PVCCreate):

    v1 = get_k8s_client()

    body = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(
            name=pvc.name
        ),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=[pvc.access_mode],
            resources=client.V1VolumeResourceRequirements(
                requests={
                    "storage": pvc.storage
                }
            ),
        ),
    )

    v1.create_namespaced_persistent_volume_claim(
        namespace="default",
        body=body,
    )

    return {
        "message": f"PVC '{pvc.name}' created successfully"
    }    


@router.get("/persistentvolumeclaims")
def list_pvcs():

    v1 = get_k8s_client()

    pvcs = v1.list_namespaced_persistent_volume_claim(
        namespace="default"
    )

    return {
        "persistent_volume_claims": [
            {
                "name": pvc.metadata.name,
                "status": pvc.status.phase,
                "storage": pvc.spec.resources.requests["storage"],
                "access_modes": pvc.spec.access_modes,
            }
            for pvc in pvcs.items
        ]
    }


@router.delete("/persistentvolumeclaims/{pvc_name}")
def delete_pvc(pvc_name: str):

    v1 = get_k8s_client()

    v1.delete_namespaced_persistent_volume_claim(
        name=pvc_name,
        namespace="default",
    )

    return {
        "message": f"PVC '{pvc_name}' deleted successfully"
    }        

@router.get("/persistentvolumes")
def list_persistent_volumes():

    v1 = get_k8s_client()

    pvs = v1.list_persistent_volume()

    return {
        "persistent_volumes": [
            {
                "name": pv.metadata.name,
                "capacity": pv.spec.capacity["storage"],
                "access_modes": pv.spec.access_modes,
                "status": pv.status.phase,
                "storage_class": pv.spec.storage_class_name,
                "claim": (
                    f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}"
                    if pv.spec.claim_ref
                    else None
                ),
            }
            for pv in pvs.items
        ]
    }    


@router.get("/deployments/{deployment_name}/status")
def deployment_status(deployment_name: str):

    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    return {
        "name": deployment.metadata.name,
        "replicas": deployment.spec.replicas,
        "ready_replicas": deployment.status.ready_replicas or 0,
        "available_replicas": deployment.status.available_replicas or 0,
        "updated_replicas": deployment.status.updated_replicas or 0,
        "unavailable_replicas": deployment.status.unavailable_replicas or 0,
    }    

@router.get("/deployments/{deployment_name}/history")
def deployment_history(deployment_name: str):

    apps_v1 = get_apps_client()

    replicasets = apps_v1.list_namespaced_replica_set(
        namespace="default"
    )

    history = []

    for rs in replicasets.items:
        owner_refs = rs.metadata.owner_references or []

        for owner in owner_refs:
            if owner.kind == "Deployment" and owner.name == deployment_name:
                history.append({
                    "replicaset": rs.metadata.name,
                    "replicas": rs.spec.replicas,
                    "ready_replicas": rs.status.ready_replicas or 0,
                    "created_at": rs.metadata.creation_timestamp,
                })

    return {
        "deployment": deployment_name,
        "history": history
    }   

@router.get("/deployments/{deployment_name}/yaml")
def export_deployment_yaml(deployment_name: str):

    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    deployment_dict = deployment.to_dict()

    yaml_output = yaml.dump(
        deployment_dict,
        sort_keys=False,
    )

    return {
        "deployment": deployment_name,
        "yaml": yaml_output,
    }


@router.post("/apply")
def apply_yaml(manifest: YAMLManifest):

    k8s_client = get_k8s_client()

    documents = list(yaml.safe_load_all(manifest.yaml))

    created = []

    for doc in documents:

        if doc:
            create_from_dict(
                client.ApiClient(),
                data=doc,
            )

            created.append(
                {
                    "kind": doc.get("kind"),
                    "name": doc.get("metadata", {}).get("name"),
                }
            )

    return {
        "message": "Manifest applied successfully",
        "resources": created,
    }    


@router.post("/namespaces")
def create_namespace(namespace: NamespaceCreate):

    v1 = get_k8s_client()

    body = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=namespace.name
        )
    )

    v1.create_namespace(body=body)

    return {
        "message": f"Namespace '{namespace.name}' created successfully"
    }


@router.delete("/namespaces/{namespace_name}")
def delete_namespace(
    namespace_name: str,
    confirm: bool = False,
):
    v1 = get_k8s_client()

    if not confirm:
        return {
            "message": (
                f"Please confirm deletion of namespace '{namespace_name}' "
                "by setting confirm=true."
            )
        }

    v1.delete_namespace(name=namespace_name)

    return {
        "message": (
            f"Namespace '{namespace_name}' deleted successfully."
        )
    }

@router.get("/deployments/{deployment_name}/labels")
def get_deployment_labels(deployment_name: str):

    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    return {
        "deployment": deployment_name,
        "labels": deployment.metadata.labels or {}
    }    

@router.put("/deployments/{deployment_name}/labels")
def update_deployment_labels(
    deployment_name: str,
    labels: LabelsUpdate,
):

    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    if deployment.metadata.labels is None:
        deployment.metadata.labels = {}

    deployment.metadata.labels.update(labels.labels)

    apps_v1.patch_namespaced_deployment(
        name=deployment_name,
        namespace="default",
        body=deployment,
    )

    return {
        "message": f"Labels updated for deployment '{deployment_name}'",
        "labels": deployment.metadata.labels,
    }

@router.get("/deployments/{deployment_name}/annotations")
def get_deployment_annotations(deployment_name: str):

    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    return {
        "deployment": deployment_name,
        "annotations": deployment.metadata.annotations or {}
    }


@router.put("/deployments/{deployment_name}/annotations")
def update_deployment_annotations(
    deployment_name: str,
    annotations: AnnotationsUpdate,
):

    apps_v1 = get_apps_client()

    deployment = apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace="default",
    )

    if deployment.metadata.annotations is None:
        deployment.metadata.annotations = {}

    deployment.metadata.annotations.update(
        annotations.annotations
    )

    apps_v1.patch_namespaced_deployment(
        name=deployment_name,
        namespace="default",
        body=deployment,
    )

    return {
        "message": f"Annotations updated for deployment '{deployment_name}'",
        "annotations": deployment.metadata.annotations,
    } 


@router.post("/deployments/{deployment_name}/rollback")
def rollback(deployment_name: str):
    return rollback_deployment(deployment_name)

@router.get("/search")
def search_resources(q: str):

    v1 = get_k8s_client()
    apps = get_apps_client()

    pods = v1.list_pod_for_all_namespaces().items
    services = v1.list_service_for_all_namespaces().items
    deployments = apps.list_deployment_for_all_namespaces().items

    matching_pods = [
        {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
        }
        for pod in pods
        if q.lower() in pod.metadata.name.lower()
    ]

    matching_services = [
        {
            "name": service.metadata.name,
            "namespace": service.metadata.namespace,
            "type": service.spec.type,
        }
        for service in services
        if q.lower() in service.metadata.name.lower()
    ]

    matching_deployments = [
        {
            "name": deployment.metadata.name,
            "namespace": deployment.metadata.namespace,
            "replicas": deployment.spec.replicas,
        }
        for deployment in deployments
        if q.lower() in deployment.metadata.name.lower()
    ]

    return {
        "query": q,
        "pods": matching_pods,
        "services": matching_services,
        "deployments": matching_deployments,
    }    


@router.get("/pods")
def list_pods(
    namespace: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    sort_by: Optional[str] = None,
):
    v1 = get_k8s_client()

    # Get pods
    if namespace:
        pods = v1.list_namespaced_pod(namespace=namespace)
    else:
        pods = v1.list_pod_for_all_namespaces()

    pod_list = []

    # Apply status filter
    for pod in pods.items:

        if status and pod.status.phase.lower() != status.lower():
            continue

        pod_list.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "pod_ip": pod.status.pod_ip,
        })

    # Sorting
    if sort_by == "name":
        pod_list.sort(key=lambda pod: pod["name"])

    elif sort_by == "namespace":
        pod_list.sort(key=lambda pod: pod["namespace"])

    elif sort_by == "status":
        pod_list.sort(key=lambda pod: pod["status"])

    # Pagination
    start = (page - 1) * limit
    end = start + limit

    paginated_pods = pod_list[start:end]

    return {
        "page": page,
        "limit": limit,
        "total": len(pod_list),
        "sorted_by": sort_by,
        "pods": paginated_pods,
    }