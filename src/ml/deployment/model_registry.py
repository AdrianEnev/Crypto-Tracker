"""
Model Registry for managing ML model versions and deployments.
Provides version control, metadata management, and deployment tracking.
"""

import json
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import hashlib

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Model deployment status."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    ROLLING_BACK = "rolling_back"


@dataclass
class ModelVersion:
    """Container for model version information."""
    model_name: str
    version: str
    model_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    size_bytes: int = 0
    checksum: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'model_name': self.model_name,
            'version': self.version,
            'model_path': self.model_path,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'description': self.description,
            'tags': self.tags,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'dependencies': self.dependencies,
            'performance_metrics': self.performance_metrics,
            'training_config': self.training_config,
            'validation_metrics': self.validation_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelVersion':
        """Create ModelVersion from dictionary."""
        return cls(
            model_name=data['model_name'],
            version=data['version'],
            model_path=data['model_path'],
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data.get('created_by', 'system'),
            description=data.get('description', ''),
            tags=data.get('tags', []),
            size_bytes=data.get('size_bytes', 0),
            checksum=data.get('checksum', ''),
            dependencies=data.get('dependencies', {}),
            performance_metrics=data.get('performance_metrics', {}),
            training_config=data.get('training_config', {}),
            validation_metrics=data.get('validation_metrics', {})
        )


@dataclass
class Deployment:
    """Container for deployment information."""
    deployment_id: str
    model_name: str
    model_version: str
    environment: str
    status: DeploymentStatus
    deployed_at: Optional[datetime] = None
    deployed_by: str = "system"
    endpoint_url: Optional[str] = None
    replicas: int = 1
    resources: Dict[str, Any] = field(default_factory=dict)
    health_check_url: Optional[str] = None
    rollback_version: Optional[str] = None
    deployment_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'deployment_id': self.deployment_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'environment': self.environment,
            'status': self.status.value,
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None,
            'deployed_by': self.deployed_by,
            'endpoint_url': self.endpoint_url,
            'replicas': self.replicas,
            'resources': self.resources,
            'health_check_url': self.health_check_url,
            'rollback_version': self.rollback_version,
            'deployment_config': self.deployment_config
        }


class ModelRegistry:
    """
    Model registry for version control and deployment management.
    """
    
    def __init__(self, registry_path: str = "./model_registry"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        # Storage paths
        self.models_path = self.registry_path / "models"
        self.metadata_path = self.registry_path / "metadata"
        self.deployments_path = self.registry_path / "deployments"
        
        # Create directories
        self.models_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)
        self.deployments_path.mkdir(exist_ok=True)
        
        # In-memory cache
        self.model_versions: Dict[str, Dict[str, ModelVersion]] = {}
        self.deployments: Dict[str, Deployment] = {}
        
        # Load existing data
        self._load_registry()
        
        logger.info(f"Initialized model registry at {self.registry_path}")
    
    def _load_registry(self) -> None:
        """Load existing registry data from disk."""
        # Load model versions
        for model_dir in self.metadata_path.iterdir():
            if model_dir.is_dir():
                model_name = model_dir.name
                self.model_versions[model_name] = {}
                
                for version_file in model_dir.glob("*.json"):
                    try:
                        with open(version_file, 'r') as f:
                            data = json.load(f)
                        version = ModelVersion.from_dict(data)
                        self.model_versions[model_name][version.version] = version
                    except Exception as e:
                        logger.error(f"Failed to load version {version_file}: {e}")
        
        # Load deployments
        for deployment_file in self.deployments_path.glob("*.json"):
            try:
                with open(deployment_file, 'r') as f:
                    data = json.load(f)
                deployment = Deployment(
                    deployment_id=data['deployment_id'],
                    model_name=data['model_name'],
                    model_version=data['model_version'],
                    environment=data['environment'],
                    status=DeploymentStatus(data['status']),
                    deployed_at=datetime.fromisoformat(data['deployed_at']) if data.get('deployed_at') else None,
                    deployed_by=data.get('deployed_by', 'system'),
                    endpoint_url=data.get('endpoint_url'),
                    replicas=data.get('replicas', 1),
                    resources=data.get('resources', {}),
                    health_check_url=data.get('health_check_url'),
                    rollback_version=data.get('rollback_version'),
                    deployment_config=data.get('deployment_config', {})
                )
                self.deployments[deployment.deployment_id] = deployment
            except Exception as e:
                logger.error(f"Failed to load deployment {deployment_file}: {e}")
    
    def register_model(self, 
                      model_name: str,
                      model_path: str,
                      version: str,
                      metadata: Optional[Dict[str, Any]] = None,
                      description: str = "",
                      tags: Optional[List[str]] = None,
                      created_by: str = "system",
                      performance_metrics: Optional[Dict[str, float]] = None,
                      training_config: Optional[Dict[str, Any]] = None,
                      validation_metrics: Optional[Dict[str, float]] = None) -> ModelVersion:
        """
        Register a new model version.
        
        Args:
            model_name: Name of the model
            model_path: Path to the model file
            version: Version identifier
            metadata: Additional metadata
            description: Model description
            tags: List of tags
            created_by: User who created the model
            performance_metrics: Performance metrics
            training_config: Training configuration
            validation_metrics: Validation metrics
            
        Returns:
            ModelVersion object
        """
        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Calculate file size and checksum
        size_bytes = model_path_obj.stat().st_size
        checksum = self._calculate_checksum(model_path)
        
        # Copy model to registry
        registry_model_path = self.models_path / model_name / version / model_path_obj.name
        registry_model_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(model_path, registry_model_path)
        
        # Create model version
        model_version = ModelVersion(
            model_name=model_name,
            version=version,
            model_path=str(registry_model_path),
            metadata=metadata or {},
            description=description,
            tags=tags or [],
            created_by=created_by,
            size_bytes=size_bytes,
            checksum=checksum,
            performance_metrics=performance_metrics or {},
            training_config=training_config or {},
            validation_metrics=validation_metrics or {}
        )
        
        # Store in memory
        if model_name not in self.model_versions:
            self.model_versions[model_name] = {}
        self.model_versions[model_name][version] = model_version
        
        # Save to disk
        self._save_model_version(model_version)
        
        logger.info(f"Registered model {model_name}:{version}")
        return model_version
    
    def get_model_version(self, model_name: str, version: str) -> Optional[ModelVersion]:
        """Get a specific model version."""
        return self.model_versions.get(model_name, {}).get(version)
    
    def list_model_versions(self, model_name: str) -> List[ModelVersion]:
        """List all versions of a model."""
        versions = self.model_versions.get(model_name, {}).values()
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def list_models(self) -> List[str]:
        """List all registered models."""
        return list(self.model_versions.keys())
    
    def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get the latest version of a model."""
        versions = self.list_model_versions(model_name)
        return versions[0] if versions else None
    
    def delete_model_version(self, model_name: str, version: str) -> bool:
        """Delete a model version."""
        if model_name not in self.model_versions:
            return False
        
        if version not in self.model_versions[model_name]:
            return False
        
        model_version = self.model_versions[model_name][version]
        
        # Delete model file
        model_path = Path(model_version.model_path)
        if model_path.exists():
            model_path.unlink()
        
        # Delete metadata file
        metadata_file = self.metadata_path / model_name / f"{version}.json"
        if metadata_file.exists():
            metadata_file.unlink()
        
        # Remove from memory
        del self.model_versions[model_name][version]
        
        # Remove model directory if empty
        model_dir = self.metadata_path / model_name
        if model_dir.exists() and not any(model_dir.iterdir()):
            model_dir.rmdir()
        
        # Remove model directory if no versions left
        if not self.model_versions[model_name]:
            del self.model_versions[model_name]
            models_dir = self.models_path / model_name
            if models_dir.exists():
                shutil.rmtree(models_dir)
        
        logger.info(f"Deleted model version {model_name}:{version}")
        return True
    
    def create_deployment(self,
                         model_name: str,
                         model_version: str,
                         environment: str,
                         endpoint_url: Optional[str] = None,
                         replicas: int = 1,
                         resources: Optional[Dict[str, Any]] = None,
                         deployment_config: Optional[Dict[str, Any]] = None,
                         deployed_by: str = "system") -> Deployment:
        """
        Create a new deployment.
        
        Args:
            model_name: Name of the model to deploy
            model_version: Version of the model to deploy
            environment: Deployment environment
            endpoint_url: Endpoint URL for the deployment
            replicas: Number of replicas
            resources: Resource requirements
            deployment_config: Deployment configuration
            deployed_by: User creating the deployment
            
        Returns:
            Deployment object
        """
        # Check if model version exists
        model_version_obj = self.get_model_version(model_name, model_version)
        if not model_version_obj:
            raise ValueError(f"Model version {model_name}:{model_version} not found")
        
        # Generate deployment ID
        deployment_id = f"{model_name}-{model_version}-{environment}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create deployment
        deployment = Deployment(
            deployment_id=deployment_id,
            model_name=model_name,
            model_version=model_version,
            environment=environment,
            status=DeploymentStatus.PENDING,
            deployed_by=deployed_by,
            endpoint_url=endpoint_url,
            replicas=replicas,
            resources=resources or {},
            deployment_config=deployment_config or {}
        )
        
        # Store deployment
        self.deployments[deployment_id] = deployment
        self._save_deployment(deployment)
        
        logger.info(f"Created deployment {deployment_id}")
        return deployment
    
    def update_deployment_status(self, 
                               deployment_id: str, 
                               status: DeploymentStatus,
                               endpoint_url: Optional[str] = None,
                               health_check_url: Optional[str] = None) -> bool:
        """Update deployment status."""
        if deployment_id not in self.deployments:
            return False
        
        deployment = self.deployments[deployment_id]
        deployment.status = status
        
        if status == DeploymentStatus.ACTIVE:
            deployment.deployed_at = datetime.now(timezone.utc)
            if endpoint_url:
                deployment.endpoint_url = endpoint_url
            if health_check_url:
                deployment.health_check_url = health_check_url
        
        self._save_deployment(deployment)
        logger.info(f"Updated deployment {deployment_id} status to {status.value}")
        return True
    
    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID."""
        return self.deployments.get(deployment_id)
    
    def list_deployments(self, model_name: Optional[str] = None, environment: Optional[str] = None) -> List[Deployment]:
        """List deployments with optional filtering."""
        deployments = list(self.deployments.values())
        
        if model_name:
            deployments = [d for d in deployments if d.model_name == model_name]
        
        if environment:
            deployments = [d for d in deployments if d.environment == environment]
        
        return sorted(deployments, key=lambda d: d.deployed_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    def get_active_deployment(self, model_name: str, environment: str) -> Optional[Deployment]:
        """Get active deployment for a model in an environment."""
        deployments = self.list_deployments(model_name, environment)
        for deployment in deployments:
            if deployment.status == DeploymentStatus.ACTIVE:
                return deployment
        return None
    
    def rollback_deployment(self, deployment_id: str, rollback_version: str) -> bool:
        """Rollback deployment to a previous version."""
        if deployment_id not in self.deployments:
            return False
        
        deployment = self.deployments[deployment_id]
        deployment.status = DeploymentStatus.ROLLING_BACK
        deployment.rollback_version = rollback_version
        
        self._save_deployment(deployment)
        logger.info(f"Rolling back deployment {deployment_id} to version {rollback_version}")
        return True
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _save_model_version(self, model_version: ModelVersion) -> None:
        """Save model version metadata to disk."""
        metadata_dir = self.metadata_path / model_version.model_name
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_file = metadata_dir / f"{model_version.version}.json"
        with open(metadata_file, 'w') as f:
            json.dump(model_version.to_dict(), f, indent=2)
    
    def _save_deployment(self, deployment: Deployment) -> None:
        """Save deployment to disk."""
        deployment_file = self.deployments_path / f"{deployment.deployment_id}.json"
        with open(deployment_file, 'w') as f:
            json.dump(deployment.to_dict(), f, indent=2)
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get registry summary statistics."""
        total_models = len(self.model_versions)
        total_versions = sum(len(versions) for versions in self.model_versions.values())
        total_deployments = len(self.deployments)
        
        active_deployments = sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.ACTIVE)
        
        return {
            'total_models': total_models,
            'total_versions': total_versions,
            'total_deployments': total_deployments,
            'active_deployments': active_deployments,
            'models': list(self.model_versions.keys()),
            'deployment_status_counts': {
                status.value: sum(1 for d in self.deployments.values() if d.status == status)
                for status in DeploymentStatus
            }
        }
