from fastapi import APIRouter

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