import re
from dataclasses import dataclass
from threading import Lock

import httpx
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models.model import Model, ModelInstance
from app.models.node import GpuDevice, Node
from app.schemas.model import ModelCreate, ModelInstanceRead, ModelUpdate
from app.utils.exceptions import APIError


@dataclass
class Allocation:
    node: Node
    gpu_indices: list[int]
    port: int


class ModelService:
    _deploy_lock = Lock()

    def __init__(self, db: Session):
        self.db = db

    def list_models(self) -> list[Model]:
        return list(self.db.scalars(select(Model).order_by(Model.created_at.desc())))

    def get_model(self, model_id: str) -> Model:
        model = self.db.get(Model, model_id)
        if model is None:
            raise APIError("Model not found", status_code=404, code=40401)
        return model

    def create_model(self, payload: ModelCreate) -> Model:
        existing = self.db.scalar(select(Model).where(Model.name == payload.name))
        if existing is not None:
            raise APIError("Model name already exists", status_code=409, code=40901)
        model = Model(**payload.model_dump())
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def update_model(self, model_id: str, payload: ModelUpdate) -> Model:
        model = self.get_model(model_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete_model(self, model_id: str) -> None:
        model = self.db.scalar(
            select(Model).options(selectinload(Model.instances)).where(Model.id == model_id)
        )
        if model is None:
            raise APIError("Model not found", status_code=404, code=40401)
        if model.instances:
            raise APIError("Model is still deployed", status_code=409, code=40902)
        self.db.delete(model)
        self.db.commit()

    def list_instances(self, model_id: str) -> list[ModelInstance]:
        self.get_model(model_id)
        stmt: Select[tuple[ModelInstance]] = (
            select(ModelInstance)
            .where(ModelInstance.model_id == model_id)
            .order_by(ModelInstance.started_at.desc())
        )
        return list(self.db.scalars(stmt))

    def deploy_model(self, model_id: str) -> tuple[Model, list[ModelInstance]]:
        with self._deploy_lock:
            model = self.db.scalar(
                select(Model).options(selectinload(Model.instances)).where(Model.id == model_id)
            )
            if model is None:
                raise APIError("Model not found", status_code=404, code=40401)
            if not model.container_image:
                raise APIError("Model container_image is required for deployment")
            if not model.launch_command:
                raise APIError("Model launch_command is required for deployment")
            if any(instance.status in {"starting", "running"} for instance in model.instances):
                raise APIError("Model is already deployed", status_code=409, code=40903)

            model.status = "deploying"
            self.db.commit()

            created_instances: list[ModelInstance] = []
            try:
                for replica_index in range(max(model.replicas, 1)):
                    allocation = self._allocate_for_model(model)
                    instance = self._launch_model_instance(model, allocation, replica_index)
                    created_instances.append(instance)
                model.status = "online"
                self.db.commit()
                self.db.refresh(model)
                return model, created_instances
            except Exception:
                self.db.rollback()
                self._cleanup_partial_instances(created_instances)
                failed_model = self.get_model(model_id)
                failed_model.status = "error"
                self.db.commit()
                raise

    def stop_model(self, model_id: str) -> Model:
        with self._deploy_lock:
            model = self.db.scalar(
                select(Model).options(selectinload(Model.instances)).where(Model.id == model_id)
            )
            if model is None:
                raise APIError("Model not found", status_code=404, code=40401)

            for instance in list(model.instances):
                self._stop_instance(instance)
                self._release_gpu_allocation(instance)
                self.db.delete(instance)

            model.status = "offline"
            self.db.commit()
            self.db.refresh(model)
            return model

    def _allocate_for_model(self, model: Model) -> Allocation:
        gpu_count, gpu_model_hint = self._parse_gpu_requirement(model.gpu_requirement)
        nodes = list(
            self.db.scalars(
                select(Node)
                .options(selectinload(Node.gpus))
                .where(Node.status.in_(["online", "maintenance"]))
                .order_by(Node.last_heartbeat.desc().nullslast(), Node.registered_at.asc())
            )
        )
        if not nodes:
            raise APIError("No available node for deployment", status_code=409, code=40904)

        for node in nodes:
            available = [
                gpu
                for gpu in node.gpus
                if gpu.status == "idle"
                and (not gpu_model_hint or gpu_model_hint.lower() in (gpu.gpu_model or "").lower())
            ]
            if len(available) < gpu_count:
                continue
            selected = sorted(available, key=lambda gpu: (gpu.utilization_gpu, gpu.gpu_index))[:gpu_count]
            for gpu in selected:
                gpu.status = "allocated"
            port = self._next_host_port(node.id)
            self.db.flush()
            return Allocation(node=node, gpu_indices=[gpu.gpu_index for gpu in selected], port=port)

        raise APIError("Insufficient GPU resources for deployment", status_code=409, code=40905)

    def _launch_model_instance(
        self,
        model: Model,
        allocation: Allocation,
        replica_index: int,
    ) -> ModelInstance:
        api_endpoint = f"http://{allocation.node.ip}:{allocation.port}"
        container_port = int((model.config_json or {}).get("container_port", settings.default_model_container_port))
        request_body = {
            "task_id": f"model-{model.id}-{replica_index}",
            "image": model.container_image,
            "gpus": allocation.gpu_indices,
            "command": model.launch_command,
            "ports": {str(allocation.port): container_port},
            "env": (model.config_json or {}).get("env", {}),
            "volumes": (model.config_json or {}).get("volumes", {}),
        }

        agent_base = f"http://{allocation.node.ip}:{allocation.node.agent_port or settings.default_agent_port}"
        with httpx.Client(timeout=settings.agent_request_timeout) as client:
            response = client.post(f"{agent_base}/api/run", json=request_body)
            if response.status_code >= 400:
                raise APIError(f"Agent launch failed: {response.text}", status_code=502, code=50201)
            response_payload = response.json()

        instance = ModelInstance(
            model_id=model.id,
            node_id=allocation.node.id,
            container_id=response_payload.get("container_id"),
            assigned_gpu_indices=allocation.gpu_indices,
            port=allocation.port,
            status="starting",
            api_endpoint=api_endpoint,
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        try:
            self._wait_for_health(instance)
            instance.status = "running"
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except Exception:
            self.db.rollback()
            try:
                self._stop_instance(instance)
            except Exception:  # noqa: BLE001
                pass
            persisted_instance = self.db.get(ModelInstance, instance.id)
            if persisted_instance is not None:
                self._release_gpu_allocation(persisted_instance)
                self.db.delete(persisted_instance)
                self.db.commit()
            else:
                self._release_allocation_by_node_and_gpus(allocation.node.id, allocation.gpu_indices)
                self.db.commit()
            raise

    def _wait_for_health(self, instance: ModelInstance) -> None:
        import time

        deadline = time.monotonic() + settings.model_health_timeout
        last_error: Exception | None = None
        with httpx.Client(timeout=10) as client:
            while time.monotonic() < deadline:
                try:
                    response = client.get(f"{instance.api_endpoint}/health")
                    if response.status_code < 400:
                        return
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                time.sleep(settings.model_health_interval)
        raise APIError(
            f"Model instance health check failed: {last_error or 'timeout'}",
            status_code=502,
            code=50202,
        )

    def _cleanup_partial_instances(self, instances: list[ModelInstance]) -> None:
        for instance in instances:
            try:
                self._stop_instance(instance)
            except Exception:  # noqa: BLE001
                pass
            try:
                attached = self.db.get(ModelInstance, instance.id)
                if attached is not None:
                    self._release_gpu_allocation(attached)
                    self.db.delete(attached)
                    self.db.commit()
            except Exception:  # noqa: BLE001
                self.db.rollback()

    def _stop_instance(self, instance: ModelInstance) -> None:
        node = self.db.get(Node, instance.node_id)
        if node is None:
            return
        agent_base = f"http://{node.ip}:{node.agent_port or settings.default_agent_port}"
        if instance.container_id:
            with httpx.Client(timeout=settings.agent_request_timeout) as client:
                response = client.post(
                    f"{agent_base}/api/stop",
                    json={"container_id": instance.container_id},
                )
                if response.status_code >= 400:
                    raise APIError(f"Agent stop failed: {response.text}", status_code=502, code=50203)

    def _release_gpu_allocation(self, instance: ModelInstance) -> None:
        if not instance.assigned_gpu_indices:
            return
        self._release_allocation_by_node_and_gpus(instance.node_id, instance.assigned_gpu_indices)

    def _release_allocation_by_node_and_gpus(self, node_id: str, gpu_indices: list[int] | None) -> None:
        if not gpu_indices:
            return
        stmt = select(GpuDevice).where(
            GpuDevice.node_id == node_id,
            GpuDevice.gpu_index.in_(gpu_indices),
        )
        for gpu in self.db.scalars(stmt):
            gpu.status = "idle"

    def _next_host_port(self, node_id: str) -> int:
        base_port = 8001
        stmt = (
            select(ModelInstance.port)
            .where(ModelInstance.node_id == node_id, ModelInstance.port.is_not(None))
            .with_for_update()
        )
        used_ports = {port for port in self.db.scalars(stmt) if port is not None}
        port = base_port
        while port in used_ports:
            port += 1
        return port

    @staticmethod
    def _parse_gpu_requirement(gpu_requirement: str | None) -> tuple[int, str | None]:
        if not gpu_requirement:
            return 1, None
        match = re.match(r"\s*(\d+)\s*x?\s*(.*)\s*$", gpu_requirement)
        if match is None:
            return 1, gpu_requirement
        count = max(int(match.group(1)), 1)
        gpu_model = match.group(2).strip() or None
        return count, gpu_model
