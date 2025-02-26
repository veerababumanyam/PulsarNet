"""Data models for the PulsarNet REST API.

This module defines Pydantic models that represent the data structures
used in the PulsarNet REST API for request and response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class DeviceType(str, Enum):
    """Enum representing supported device types."""
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    JUNIPER = "juniper"
    ARISTA_EOS = "arista_eos"
    HP_COMWARE = "hp_comware"
    HP_PROCURVE = "hp_procurve"
    CUSTOM = "custom"


class ProtocolType(str, Enum):
    """Enum representing supported protocol types."""
    SSH = "ssh"
    TELNET = "telnet"
    CONSOLE = "console"
    HTTP = "http"
    HTTPS = "https"


class ScheduleType(str, Enum):
    """Enum representing schedule types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ConsolidationStrategyEnum(str, Enum):
    """Enum representing consolidation strategies."""
    MIGRATION = "migration"
    REPLACEMENT = "replacement"
    MERGE = "merge"
    STANDARDIZATION = "standardization"
    DECOMMISSION = "decommission"


class ConsolidationStatusEnum(str, Enum):
    """Enum representing consolidation plan statuses."""
    DRAFT = "draft"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"


class DeviceModel(BaseModel):
    """Model representing a network device."""
    name: str
    ip_address: str
    device_type: DeviceType
    username: str
    password: Optional[str] = None
    enable_password: Optional[str] = None
    port: int = 22
    protocol: ProtocolType = ProtocolType.SSH
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "core-switch-01",
                "ip_address": "192.168.1.1",
                "device_type": "cisco_ios",
                "username": "admin",
                "password": "password123",
                "enable_password": "enable123",
                "port": 22,
                "protocol": "ssh",
                "custom_settings": {"timeout": 60}
            }
        }


class GroupModel(BaseModel):
    """Model representing a device group."""
    name: str
    description: Optional[str] = None
    device_names: List[str] = Field(default_factory=list)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "core-switches",
                "description": "Core network switches",
                "device_names": ["core-switch-01", "core-switch-02"]
            }
        }


class BackupModel(BaseModel):
    """Model representing a device backup."""
    device_name: str
    filename: str
    timestamp: datetime
    status: str
    verified: bool = False
    checksum: Optional[str] = None
    size: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "device_name": "core-switch-01",
                "filename": "core-switch-01_20250225_134400.txt",
                "timestamp": "2025-02-25T13:44:00",
                "status": "success",
                "verified": True,
                "checksum": "a1b2c3d4e5f6g7h8i9j0",
                "size": 1024
            }
        }


class ScheduleModel(BaseModel):
    """Model representing a backup schedule."""
    name: str
    device_name: Optional[str] = None
    group_name: Optional[str] = None
    schedule_type: ScheduleType
    time: str
    days: Optional[List[int]] = None
    enabled: bool = True
    
    @validator('device_name', 'group_name')
    def validate_target(cls, v, values):
        """Validate that either device_name or group_name is provided."""
        if 'device_name' in values and values['device_name'] and 'group_name' in values and values['group_name']:
            raise ValueError("Cannot specify both device_name and group_name")
        if not (('device_name' in values and values['device_name']) or ('group_name' in values and values['group_name'])):
            raise ValueError("Must specify either device_name or group_name")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "daily-core-backup",
                "device_name": "core-switch-01",
                "schedule_type": "daily",
                "time": "23:00",
                "enabled": True
            }
        }


class TemplateModel(BaseModel):
    """Model representing a device template."""
    name: str
    device_type: DeviceType
    backup_commands: List[str]
    connection_settings: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "cisco-ios-template",
                "device_type": "cisco_ios",
                "backup_commands": ["terminal length 0", "show running-config", "show version"],
                "connection_settings": {"timeout": 60, "fast_cli": True},
                "description": "Standard template for Cisco IOS devices"
            }
        }


class SimilarityFactorModel(BaseModel):
    """Model representing a similarity factor in device consolidation."""
    factor: str
    score: float
    details: Optional[Dict[str, Any]] = None


class ConsolidationDeviceModel(BaseModel):
    """Model representing a device in a consolidation group."""
    device_id: int
    device_name: str
    role: Optional[str] = None
    is_primary: bool = False


class ConfigDifferenceModel(BaseModel):
    """Model representing configuration differences between devices."""
    device1_id: int
    device2_id: int
    sections: Dict[str, Any]
    categories: Dict[str, List[str]]


class ConsolidationBenefitModel(BaseModel):
    """Model representing estimated benefits of a consolidation."""
    cost_savings: Optional[float] = None
    space_savings: Optional[float] = None
    power_savings: Optional[float] = None
    management_savings: Optional[float] = None
    complexity_reduction: Optional[float] = None


class ConsolidationGroupModel(BaseModel):
    """Model representing a group of similar devices for consolidation."""
    id: str
    name: str
    devices: List[ConsolidationDeviceModel]
    similarity_score: float = 0.0
    similarity_factors: Dict[str, float] = Field(default_factory=dict)
    proposed_strategy: Optional[ConsolidationStrategyEnum] = None
    config_differences: List[ConfigDifferenceModel] = Field(default_factory=list)
    estimated_benefits: Optional[ConsolidationBenefitModel] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "group-123456",
                "name": "Access Switch Group 1",
                "devices": [
                    {"device_id": 1, "device_name": "switch-a-01", "is_primary": True},
                    {"device_id": 2, "device_name": "switch-a-02", "is_primary": False}
                ],
                "similarity_score": 0.85,
                "similarity_factors": {
                    "device_type": 1.0,
                    "software_version": 0.9,
                    "hardware_model": 1.0
                },
                "proposed_strategy": "standardization",
                "estimated_benefits": {
                    "cost_savings": 5000,
                    "complexity_reduction": 0.3
                }
            }
        }


class ConsolidationPlanModel(BaseModel):
    """Model representing a consolidation plan."""
    id: str
    name: str
    description: Optional[str] = None
    status: ConsolidationStatusEnum = ConsolidationStatusEnum.DRAFT
    creator: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    groups: List[ConsolidationGroupModel] = Field(default_factory=list)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "plan-123456",
                "name": "Campus Network Consolidation",
                "description": "Plan to consolidate redundant access switches",
                "status": "planned",
                "creator": "admin",
                "created_at": "2025-02-25T13:44:00",
                "updated_at": "2025-02-26T09:15:00",
                "groups": []
            }
        }


class SimilarityAnalysisRequestModel(BaseModel):
    """Model for requesting similarity analysis between devices."""
    threshold: Optional[float] = 0.7
    device_type: Optional[str] = None
    location: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "threshold": 0.7,
                "device_type": "cisco_ios",
                "location": "datacenter-a"
            }
        }


class DeviceSimilarityModel(BaseModel):
    """Model representing similarity between two devices."""
    device1_id: int
    device2_id: int
    overall_similarity: float
    factors: Dict[str, SimilarityFactorModel]
    config_differences: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "device1_id": 1,
                "device2_id": 2,
                "overall_similarity": 0.85,
                "factors": {
                    "device_type": {
                        "factor": "device_type",
                        "score": 1.0,
                        "details": {"device1": "cisco_ios", "device2": "cisco_ios"}
                    }
                },
                "config_differences": {
                    "sections": {
                        "interfaces": ["interface GigabitEthernet1/0/1", "interface GigabitEthernet1/0/2"]
                    }
                }
            }
        }


class ConsolidationPlanCreateModel(BaseModel):
    """Model for creating a new consolidation plan."""
    name: str
    description: Optional[str] = None
    device_groups: List[List[int]]
    creator: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Campus Network Consolidation",
                "description": "Plan to consolidate redundant access switches",
                "device_groups": [[1, 2, 3], [4, 5]],
                "creator": "admin"
            }
        } 