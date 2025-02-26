"""API Server for PulsarNet.

This module provides a FastAPI implementation for the PulsarNet application,
allowing programmatic access to device management, backup operations, and
scheduling functionalities through a REST API.
"""

import asyncio
import logging
import os
import sys
import uvicorn
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import time
from datetime import datetime, timedelta

from .models import DeviceModel, GroupModel, BackupModel, ScheduleModel, TemplateModel

from ..device_management import DeviceManager, Device, DeviceGroup, DeviceTemplateManager
from ..database import DatabaseManager
from ..scheduler import DBScheduleManager
from ..verification import BackupVerifier
from ..backup_operations import BackupManager
from ..utils.logging_config import LoggingManager, AuditLogger


class APIServer:
    """API Server for exposing PulsarNet functionality via REST endpoints."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        database_path: Optional[str] = None,
        log_level: str = "info"
    ):
        """Initialize the API server.
        
        Args:
            host: Host address to bind the server to
            port: Port to use for the server
            database_path: Path to the SQLite database file
            log_level: Logging level (debug, info, warning, error, critical)
        """
        self.host = host
        self.port = port
        self.database_path = database_path
        self.log_level = log_level.upper()
        
        # Initialize FastAPI application
        self.app = FastAPI(
            title="PulsarNet API",
            description="REST API for managing network device backups and configurations",
            version="1.0.0"
        )
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize managers
        self.db_manager = None
        self.device_manager = None
        self.template_manager = None
        self.backup_manager = None
        self.schedule_manager = None
        self.backup_verifier = None
        self.logging_manager = None
        self.audit_logger = None
        
        # Setup routes
        self._setup_routes()
    
    async def initialize(self):
        """Initialize the backend managers and connect to the database."""
        # Setup logging
        self.logging_manager = LoggingManager()
        self.logging_manager.configure(
            console=True,
            file=True,
            syslog=False,
            log_level=self.log_level
        )
        self.audit_logger = self.logging_manager.get_audit_logger()
        
        # Initialize database manager
        self.db_manager = DatabaseManager(database_path=self.database_path)
        await self.db_manager.initialize()
        
        # Initialize other managers
        self.device_manager = DeviceManager()
        await self.device_manager.initialize(db_manager=self.db_manager)
        
        self.template_manager = DeviceTemplateManager()
        await self.template_manager.initialize(db_manager=self.db_manager)
        
        self.backup_manager = BackupManager()
        await self.backup_manager.initialize(db_manager=self.db_manager)
        
        self.schedule_manager = DBScheduleManager()
        await self.schedule_manager.initialize(
            db_manager=self.db_manager,
            backup_manager=self.backup_manager
        )
        
        self.backup_verifier = BackupVerifier()
        await self.backup_verifier.initialize(db_manager=self.db_manager)
    
    def _setup_routes(self):
        """Set up the API routes."""
        app = self.app
        
        # Health check
        @app.get("/health")
        async def health_check():
            """Check if the API server is running."""
            return {"status": "ok", "timestamp": datetime.now().isoformat()}
        
        # Device routes
        @app.get("/devices", response_model=List[DeviceModel])
        async def get_devices():
            """Get all devices."""
            devices = await self.device_manager.get_devices()
            return [device.to_dict() for device in devices]
        
        @app.get("/devices/{device_name}", response_model=DeviceModel)
        async def get_device(device_name: str = Path(..., description="Name of the device")):
            """Get a specific device by name."""
            try:
                device = await self.device_manager.get_device(device_name)
                if not device:
                    raise HTTPException(status_code=404, detail=f"Device {device_name} not found")
                return device.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/devices", response_model=DeviceModel)
        async def add_device(device: DeviceModel):
            """Add a new device."""
            try:
                new_device = Device(
                    name=device.name,
                    ip_address=device.ip_address,
                    device_type=device.device_type,
                    username=device.username,
                    password=device.password,
                    enable_password=device.enable_password,
                    port=device.port,
                    custom_settings=device.custom_settings
                )
                await self.device_manager.add_device(new_device)
                self.audit_logger.log_action("add_device", f"Added device {device.name}")
                return new_device.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.put("/devices/{device_name}", response_model=DeviceModel)
        async def update_device(
            device: DeviceModel,
            device_name: str = Path(..., description="Name of the device to update")
        ):
            """Update an existing device."""
            try:
                existing_device = await self.device_manager.get_device(device_name)
                if not existing_device:
                    raise HTTPException(status_code=404, detail=f"Device {device_name} not found")
                
                updated_device = Device(
                    name=device.name,
                    ip_address=device.ip_address,
                    device_type=device.device_type,
                    username=device.username,
                    password=device.password or existing_device.password,
                    enable_password=device.enable_password or existing_device.enable_password,
                    port=device.port,
                    custom_settings=device.custom_settings
                )
                
                await self.device_manager.update_device(device_name, updated_device)
                self.audit_logger.log_action("update_device", f"Updated device {device_name}")
                return updated_device.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.delete("/devices/{device_name}")
        async def delete_device(device_name: str = Path(..., description="Name of the device to delete")):
            """Delete a device."""
            try:
                await self.device_manager.delete_device(device_name)
                self.audit_logger.log_action("delete_device", f"Deleted device {device_name}")
                return {"status": "success", "message": f"Device {device_name} deleted"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Group routes
        @app.get("/groups", response_model=List[GroupModel])
        async def get_groups():
            """Get all device groups."""
            groups = await self.device_manager.get_groups()
            return [group.to_dict() for group in groups]
        
        @app.get("/groups/{group_name}", response_model=GroupModel)
        async def get_group(group_name: str = Path(..., description="Name of the group")):
            """Get a specific device group by name."""
            try:
                group = await self.device_manager.get_group(group_name)
                if not group:
                    raise HTTPException(status_code=404, detail=f"Group {group_name} not found")
                return group.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/groups", response_model=GroupModel)
        async def add_group(group: GroupModel):
            """Add a new device group."""
            try:
                new_group = DeviceGroup(
                    name=group.name,
                    description=group.description,
                    device_names=group.device_names
                )
                await self.device_manager.add_group(new_group)
                self.audit_logger.log_action("add_group", f"Added group {group.name}")
                return new_group.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Template routes
        @app.get("/templates", response_model=List[TemplateModel])
        async def get_templates():
            """Get all device templates."""
            templates = await self.template_manager.get_templates()
            return templates
        
        @app.get("/templates/{device_type}", response_model=TemplateModel)
        async def get_template(device_type: str = Path(..., description="Type of device for the template")):
            """Get a template for a specific device type."""
            try:
                template = await self.template_manager.get_template(device_type)
                if not template:
                    raise HTTPException(status_code=404, detail=f"Template for {device_type} not found")
                return template
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/templates", response_model=TemplateModel)
        async def add_template(template: TemplateModel):
            """Add a new device template."""
            try:
                await self.template_manager.add_template(
                    device_type=template.device_type,
                    backup_commands=template.backup_commands,
                    connection_settings=template.connection_settings,
                    name=template.name,
                    description=template.description
                )
                self.audit_logger.log_action("add_template", f"Added template for {template.device_type}")
                return template
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Backup operations
        @app.post("/backups/start")
        async def start_backup(
            device_name: Optional[str] = Query(None, description="Name of the device to backup"),
            group_name: Optional[str] = Query(None, description="Name of the device group to backup"),
            background_tasks: BackgroundTasks = BackgroundTasks()
        ):
            """Start a backup operation for a device or group."""
            try:
                if not device_name and not group_name:
                    raise HTTPException(status_code=400, detail="Must specify either device_name or group_name")
                
                if device_name and group_name:
                    raise HTTPException(status_code=400, detail="Cannot specify both device_name and group_name")
                
                # Define a background task function
                async def run_backup():
                    try:
                        if device_name:
                            await self.backup_manager.backup_device(device_name)
                            self.audit_logger.log_action("backup_device", f"Backed up device {device_name}")
                        else:
                            await self.backup_manager.backup_group(group_name)
                            self.audit_logger.log_action("backup_group", f"Backed up group {group_name}")
                    except Exception as e:
                        logging.error(f"Backup failed: {str(e)}")
                
                # Add the task to background tasks
                background_tasks.add_task(run_backup)
                
                return {
                    "status": "started",
                    "message": f"Backup job started for {'device '+device_name if device_name else 'group '+group_name}"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/backups", response_model=List[BackupModel])
        async def get_backups(
            device_name: Optional[str] = Query(None, description="Filter backups by device name"),
            limit: int = Query(100, description="Maximum number of backups to return")
        ):
            """Get a list of backups."""
            try:
                backups = await self.backup_manager.get_backups(device_name=device_name, limit=limit)
                return backups
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/backups/verify/{backup_id}")
        async def verify_backup(backup_id: int = Path(..., description="ID of the backup to verify")):
            """Verify the integrity of a backup."""
            try:
                result = await self.backup_verifier.verify_backup(backup_id)
                return {
                    "status": "success" if result else "failed",
                    "backup_id": backup_id,
                    "verified": result
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Schedule routes
        @app.get("/schedules", response_model=List[ScheduleModel])
        async def get_schedules():
            """Get all backup schedules."""
            try:
                schedules = await self.schedule_manager.get_schedules()
                return schedules
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/schedules", response_model=ScheduleModel)
        async def add_schedule(schedule: ScheduleModel):
            """Add a new backup schedule."""
            try:
                await self.schedule_manager.add_schedule(
                    name=schedule.name,
                    device_name=schedule.device_name,
                    group_name=schedule.group_name,
                    schedule_type=schedule.schedule_type,
                    time=schedule.time,
                    days=schedule.days,
                    enabled=schedule.enabled
                )
                self.audit_logger.log_action("add_schedule", f"Added schedule {schedule.name}")
                return schedule
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    async def start(self):
        """Start the API server."""
        await self.initialize()
        
        # Run the server
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level=self.log_level.lower()
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run(self):
        """Run the API server synchronously."""
        asyncio.run(self.start()) 