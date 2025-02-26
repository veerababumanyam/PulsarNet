from datetime import datetime, timedelta
import json
import os
import logging
from enum import Enum
from typing import List, Dict, Optional, Union, Tuple

class ScheduleType(Enum):
    """Types of backup schedules."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    CUSTOM = "Custom"

class TargetType(Enum):
    """Types of backup targets."""
    DEVICE = "Device"
    GROUP = "Group"

class BackupSchedule:
    """Represents a backup schedule configuration."""
    def __init__(self, 
                 name: str,
                 schedule_type: ScheduleType,
                 target_type: TargetType = TargetType.DEVICE,
                 devices: List[str] = None,
                 groups: List[str] = None,
                 time: str = "00:00",  # HH:MM format
                 days: List[int] = None,  # 0-6 for weekly, None for daily
                 enabled: bool = True,
                 last_run: Optional[datetime] = None,
                 next_run: Optional[datetime] = None):
        self.name = name
        self.schedule_type = schedule_type
        self.target_type = target_type
        self.devices = devices if devices else []
        self.groups = groups if groups else []
        self.time = time
        self.days = days if days else []
        self.enabled = enabled
        self.last_run = last_run
        self.next_run = self._calculate_next_run()
        
    def _calculate_next_run(self) -> datetime:
        """Calculate the next run time based on schedule type."""
        now = datetime.now()
        
        try:
            hour, minute = map(int, self.time.split(':'))
            
            # Validate hour and minute
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                logging.warning(f"Invalid time format in schedule {self.name}: {self.time}. Using default (00:00).")
                hour, minute = 0, 0
                
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if next_run <= now:
                next_run += timedelta(days=1)
                
            if self.schedule_type == ScheduleType.DAILY:
                return next_run
                
            elif self.schedule_type == ScheduleType.WEEKLY and self.days:
                # Handle empty or invalid days list
                valid_days = [d for d in self.days if 0 <= d <= 6]
                if not valid_days:
                    logging.warning(f"No valid days specified for weekly schedule {self.name}. Defaulting to next day.")
                    return next_run
                    
                days_ahead = 7
                for day in valid_days:
                    days_until = (day - now.weekday()) % 7
                    if days_until < days_ahead:
                        days_ahead = days_until
                
                # If today is selected but time has passed, use next week
                if days_ahead == 0 and next_run <= now:
                    days_ahead = 7
                    
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
            
            # Default for custom or other types
            return next_run
            
        except Exception as e:
            logging.error(f"Error calculating next run time for schedule {self.name}: {str(e)}")
            # Fallback to tomorrow at midnight
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
    def to_dict(self) -> dict:
        """Convert schedule to dictionary for serialization."""
        return {
            'name': self.name,
            'schedule_type': self.schedule_type.value,
            'target_type': self.target_type.value,
            'devices': self.devices,
            'groups': self.groups,
            'time': self.time,
            'days': self.days,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'BackupSchedule':
        """Create schedule from dictionary."""
        # Handle legacy schedules that only have devices
        target_type = TargetType.DEVICE
        if 'target_type' in data:
            target_type = TargetType(data['target_type'])
        
        return cls(
            name=data['name'],
            schedule_type=ScheduleType(data['schedule_type']),
            target_type=target_type,
            devices=data.get('devices', []),
            groups=data.get('groups', []),
            time=data['time'],
            days=data.get('days', []),
            enabled=data.get('enabled', True),
            last_run=datetime.fromisoformat(data['last_run']) if data.get('last_run') else None,
            next_run=datetime.fromisoformat(data['next_run']) if data.get('next_run') else None
        )

class ScheduleManager:
    """Manages backup schedules."""
    def __init__(self):
        self.schedules: Dict[str, BackupSchedule] = {}
        self.config_file = os.path.expanduser("~/.pulsarnet/schedules.json")
        self.load_schedules()
        
    def add_schedule(self, schedule: BackupSchedule) -> None:
        """Add a new backup schedule."""
        if schedule.name in self.schedules:
            raise ValueError(f"Schedule with name '{schedule.name}' already exists")
        self.schedules[schedule.name] = schedule
        self.save_schedules()
        
    def update_schedule(self, schedule: BackupSchedule) -> None:
        """Update an existing schedule."""
        if schedule.name not in self.schedules:
            raise ValueError(f"Schedule '{schedule.name}' not found")
        self.schedules[schedule.name] = schedule
        self.save_schedules()
        
    def remove_schedule(self, name: str) -> None:
        """Remove a schedule."""
        if name not in self.schedules:
            raise ValueError(f"Schedule '{name}' not found")
        del self.schedules[name]
        self.save_schedules()
        
    def get_due_schedules(self) -> List[BackupSchedule]:
        """Get schedules that are due for execution."""
        now = datetime.now()
        return [
            schedule for schedule in self.schedules.values()
            if schedule.enabled and schedule.next_run <= now
        ]
        
    def update_schedule_time(self, name: str) -> None:
        """Update last run time and calculate next run for a schedule."""
        if name not in self.schedules:
            return
            
        schedule = self.schedules[name]
        schedule.last_run = datetime.now()
        schedule.next_run = schedule._calculate_next_run()
        self.save_schedules()
        
    def save_schedules(self) -> None:
        """Save schedules to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(
                    {name: schedule.to_dict() for name, schedule in self.schedules.items()},
                    f,
                    indent=4
                )
        except Exception as e:
            logging.error(f"Failed to save schedules: {e}")
            
    def load_schedules(self) -> None:
        """Load schedules from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.schedules = {
                        name: BackupSchedule.from_dict(schedule_data)
                        for name, schedule_data in data.items()
                    }
        except Exception as e:
            logging.error(f"Failed to load schedules: {e}")
