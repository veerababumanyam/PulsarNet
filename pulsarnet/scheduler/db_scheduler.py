"""Database-backed scheduler for PulsarNet.

This module provides a scheduler that uses SQLite for persistent storage,
allowing for more advanced scheduling options and better querying capabilities.
"""

import asyncio
import datetime
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from enum import Enum
import calendar
import re
import itertools

from ..database.db_manager import DatabaseManager
from ..utils.logging_config import get_logger


class ScheduleType(Enum):
    """Schedule types supported by the scheduler."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class SchedulePriority(Enum):
    """Priority levels for schedules."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class DBScheduleManager:
    """Schedule manager using SQLite for storage."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the scheduler.
        
        Args:
            db_manager: Optional database manager. If None, a new one will be created.
        """
        self.db = db_manager or DatabaseManager()
        self.logger = get_logger("scheduler")
        self._running = False
        self._schedule_task = None
        self._pre_run_callbacks = []
        self._post_run_callbacks = []
        
    async def initialize(self):
        """Initialize the scheduler.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Initialize database
            if not self.db:
                self.db = DatabaseManager()
                
            await self.db.initialize()
            
            # Update next_run for schedules that don't have it set
            await self._update_missing_next_runs()
            
            self.logger.info("Scheduler initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
            return False
            
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
            
        self._running = True
        self._schedule_task = asyncio.create_task(self._schedule_loop())
        self.logger.info("Scheduler started")
        
    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
            
        self._running = False
        if self._schedule_task:
            self._schedule_task.cancel()
            try:
                await self._schedule_task
            except asyncio.CancelledError:
                pass
            self._schedule_task = None
            
        self.logger.info("Scheduler stopped")
        
    async def _schedule_loop(self):
        """Main scheduler loop."""
        try:
            while self._running:
                try:
                    # Get due schedules
                    due_schedules = await self.db.get_due_schedules()
                    
                    if due_schedules:
                        self.logger.info(f"Found {len(due_schedules)} due schedules")
                        
                    # Process each due schedule
                    for schedule in due_schedules:
                        if not self._running:
                            break
                            
                        # Calculate next run time
                        next_run = self._calculate_next_run(schedule)
                        
                        # Update schedule last_run and next_run
                        await self.db.update_schedule_run(schedule['id'], next_run)
                        
                        # Run the schedule
                        await self._run_schedule(schedule)
                        
                except Exception as e:
                    self.logger.error(f"Error in scheduler loop: {e}")
                    
                # Sleep for a short time before checking again
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            self.logger.info("Scheduler loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Unhandled error in scheduler loop: {e}")
            
    async def _run_schedule(self, schedule: Dict[str, Any]):
        """Run a schedule.
        
        Args:
            schedule: Schedule to run
        """
        try:
            # Call pre-run callbacks
            for callback in self._pre_run_callbacks:
                try:
                    await callback(schedule)
                except Exception as e:
                    self.logger.error(f"Error in pre-run callback: {e}")
                    
            # Log schedule execution
            self.logger.info(f"Running schedule: {schedule['name']} (ID: {schedule['id']})")
            
            # Call post-run callbacks
            for callback in self._post_run_callbacks:
                try:
                    await callback(schedule, True, None)
                except Exception as e:
                    self.logger.error(f"Error in post-run callback: {e}")
        except Exception as e:
            self.logger.error(f"Error running schedule {schedule['id']}: {e}")
            
            # Call post-run callbacks with error
            for callback in self._post_run_callbacks:
                try:
                    await callback(schedule, False, str(e))
                except Exception as callback_err:
                    self.logger.error(f"Error in post-run callback: {callback_err}")
                    
    def _calculate_next_run(self, schedule: Dict[str, Any]) -> str:
        """Calculate the next run time for a schedule.
        
        Args:
            schedule: Schedule to calculate next run for
            
        Returns:
            str: Next run time in ISO format
        """
        schedule_type = schedule['schedule_type']
        now = datetime.datetime.now()
        
        if schedule_type == ScheduleType.DAILY.value:
            return self._calculate_daily_next_run(schedule, now)
        elif schedule_type == ScheduleType.WEEKLY.value:
            return self._calculate_weekly_next_run(schedule, now)
        elif schedule_type == ScheduleType.MONTHLY.value:
            return self._calculate_monthly_next_run(schedule, now)
        elif schedule_type == ScheduleType.CUSTOM.value:
            return self._calculate_custom_next_run(schedule, now)
        else:
            # Default to daily at same time tomorrow
            next_run = now + datetime.timedelta(days=1)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
            
    def _calculate_daily_next_run(self, schedule: Dict[str, Any], now: datetime.datetime) -> str:
        """Calculate next run for daily schedule.
        
        Args:
            schedule: Schedule to calculate next run for
            now: Current datetime
            
        Returns:
            str: Next run time in ISO format
        """
        # Parse the time
        try:
            time_str = schedule['start_time']
            hour, minute = map(int, time_str.split(':'))
            
            # Calculate next run time
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If next run is in the past, schedule for tomorrow
            if next_run <= now:
                next_run += datetime.timedelta(days=1)
                
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"Error calculating daily next run: {e}")
            # Default to same time tomorrow
            next_run = now + datetime.timedelta(days=1)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
            
    def _calculate_weekly_next_run(self, schedule: Dict[str, Any], now: datetime.datetime) -> str:
        """Calculate next run for weekly schedule.
        
        Args:
            schedule: Schedule to calculate next run for
            now: Current datetime
            
        Returns:
            str: Next run time in ISO format
        """
        try:
            time_str = schedule['start_time']
            hour, minute = map(int, time_str.split(':'))
            
            # Get days of week (0-6, 0 is Monday)
            days_str = schedule['days_of_week']
            if not days_str:
                # Default to Monday if no days specified
                days = [0]
            else:
                days = list(map(int, days_str.split(',')))
                
            # Sort days
            days.sort()
            
            # Current day of week (0-6, 0 is Monday)
            current_weekday = now.weekday()
            
            # Find the next day to run
            next_day = None
            for day in days:
                if day > current_weekday:
                    next_day = day
                    break
                    
            # If no day found, use the first day next week
            if next_day is None:
                next_day = days[0]
                days_ahead = 7 - current_weekday + next_day
            else:
                days_ahead = next_day - current_weekday
                
            # Calculate next run date
            next_date = now.date() + datetime.timedelta(days=days_ahead)
            
            # Combine with time
            next_run = datetime.datetime.combine(
                next_date,
                datetime.time(hour=hour, minute=minute)
            )
            
            # If it's the same day and time has passed, move to next week
            if days_ahead == 0 and next_run <= now:
                next_run += datetime.timedelta(days=7)
                
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"Error calculating weekly next run: {e}")
            # Default to same time next week
            next_run = now + datetime.timedelta(days=7)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
            
    def _calculate_monthly_next_run(self, schedule: Dict[str, Any], now: datetime.datetime) -> str:
        """Calculate next run for monthly schedule.
        
        Args:
            schedule: Schedule to calculate next run for
            now: Current datetime
            
        Returns:
            str: Next run time in ISO format
        """
        try:
            time_str = schedule['start_time']
            hour, minute = map(int, time_str.split(':'))
            
            # Get days of month (1-31)
            days_str = schedule['days_of_month']
            if not days_str:
                # Default to 1st if no days specified
                days = [1]
            else:
                days = list(map(int, days_str.split(',')))
                
            # Sort days
            days.sort()
            
            # Current day of month
            current_day = now.day
            
            # Current month and year
            year = now.year
            month = now.month
            
            # Find the next day to run in the current month
            next_day = None
            for day in days:
                if day > current_day:
                    # Check if this day exists in the current month
                    _, last_day = calendar.monthrange(year, month)
                    if day <= last_day:
                        next_day = day
                        break
                        
            # If no day found or day doesn't exist in this month, move to next month
            if next_day is None:
                # Move to next month
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                    
                # Find first valid day in next month
                _, last_day = calendar.monthrange(year, month)
                for day in days:
                    if day <= last_day:
                        next_day = day
                        break
                        
                # If no valid day found, use the last day of the month
                if next_day is None:
                    next_day = last_day
                    
            # Create next run datetime
            next_run = datetime.datetime(
                year=year,
                month=month,
                day=next_day,
                hour=hour,
                minute=minute
            )
            
            # Handle case where the calculated time is in the past
            if next_run <= now:
                # Move to next month
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                    
                # Find first valid day in next month
                _, last_day = calendar.monthrange(year, month)
                for day in days:
                    if day <= last_day:
                        next_day = day
                        break
                        
                # If no valid day found, use the last day of the month
                if next_day is None:
                    next_day = last_day
                    
                # Create next run datetime
                next_run = datetime.datetime(
                    year=year,
                    month=month,
                    day=next_day,
                    hour=hour,
                    minute=minute
                )
                
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"Error calculating monthly next run: {e}")
            # Default to same time next month
            next_month = now.month + 1
            next_year = now.year
            if next_month > 12:
                next_month = 1
                next_year += 1
                
            next_run = now.replace(year=next_year, month=next_month)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
            
    def _calculate_custom_next_run(self, schedule: Dict[str, Any], now: datetime.datetime) -> str:
        """Calculate next run for custom schedule.
        
        Args:
            schedule: Schedule to calculate next run for
            now: Current datetime
            
        Returns:
            str: Next run time in ISO format
        """
        try:
            # For custom schedules, we need to calculate the next run based on:
            # - Specific times (start_time)
            # - Specific days of week (days_of_week)
            # - Specific days of month (days_of_month)
            # - Specific months (months)
            
            # Parse the time
            time_str = schedule['start_time']
            if not time_str:
                # Default to current time
                hour, minute = now.hour, now.minute
            else:
                hour, minute = map(int, time_str.split(':'))
                
            # Get days of week (0-6, 0 is Monday)
            days_of_week_str = schedule['days_of_week']
            if days_of_week_str:
                days_of_week = list(map(int, days_of_week_str.split(',')))
            else:
                # All days
                days_of_week = list(range(7))
                
            # Get days of month (1-31)
            days_of_month_str = schedule['days_of_month']
            if days_of_month_str:
                days_of_month = list(map(int, days_of_month_str.split(',')))
            else:
                # All days
                days_of_month = list(range(1, 32))
                
            # Get months (1-12)
            months_str = schedule['months']
            if months_str:
                months = list(map(int, months_str.split(',')))
            else:
                # All months
                months = list(range(1, 13))
                
            # Start from current datetime
            candidate = now
            
            # Try for up to 2 years
            for _ in range(2 * 12 * 31):
                # Move to next day if current time has passed
                if candidate.hour > hour or (candidate.hour == hour and candidate.minute >= minute):
                    candidate += datetime.timedelta(days=1)
                    
                # Set the time
                candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Check if this candidate meets all criteria
                if (candidate.month in months and
                    candidate.day in days_of_month and
                    candidate.weekday() in days_of_week):
                    # This is a valid next run time
                    return candidate.strftime('%Y-%m-%d %H:%M:%S')
                    
                # Move to next day
                candidate += datetime.timedelta(days=1)
                
            # If we got here, we couldn't find a valid next run time
            # Default to one week from now
            next_run = now + datetime.timedelta(days=7)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"Error calculating custom next run: {e}")
            # Default to one week from now
            next_run = now + datetime.timedelta(days=7)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
            
    async def _update_missing_next_runs(self):
        """Update next_run for schedules that don't have it set."""
        try:
            # Get all schedules
            schedules = await self.db.get_schedules()
            
            now = datetime.datetime.now()
            for schedule in schedules:
                if not schedule['next_run']:
                    # Calculate next run time
                    next_run = self._calculate_next_run(schedule)
                    
                    # Update schedule
                    await self.db.update_schedule(schedule['id'], {'next_run': next_run})
                    
            self.logger.info("Updated missing next_run values")
        except Exception as e:
            self.logger.error(f"Error updating missing next_run values: {e}")
            
    async def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules.
        
        Returns:
            List[Dict[str, Any]]: List of schedules
        """
        return await self.db.get_schedules()
        
    async def get_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Optional[Dict[str, Any]]: Schedule or None if not found
        """
        return await self.db.get_schedule(schedule_id)
        
    async def add_schedule(self, schedule_data: Dict[str, Any]) -> Optional[int]:
        """Add a new schedule.
        
        Args:
            schedule_data: Schedule data
            
        Returns:
            Optional[int]: New schedule ID or None on failure
        """
        try:
            # Calculate next run time if not provided
            if 'next_run' not in schedule_data:
                # Create a temporary schedule for calculation
                temp_schedule = {
                    'schedule_type': schedule_data.get('schedule_type', 'daily'),
                    'start_time': schedule_data.get('start_time', '00:00'),
                    'days_of_week': schedule_data.get('days_of_week', ''),
                    'days_of_month': schedule_data.get('days_of_month', ''),
                    'months': schedule_data.get('months', '')
                }
                
                next_run = self._calculate_next_run(temp_schedule)
                schedule_data['next_run'] = next_run
                
            # Add schedule to database
            schedule_id = await self.db.add_schedule(schedule_data)
            
            if schedule_id:
                self.logger.info(f"Added schedule {schedule_id}: {schedule_data.get('name')}")
                
            return schedule_id
        except Exception as e:
            self.logger.error(f"Error adding schedule: {e}")
            return None
            
    async def update_schedule(self, schedule_id: int, schedule_data: Dict[str, Any]) -> bool:
        """Update a schedule.
        
        Args:
            schedule_id: Schedule ID
            schedule_data: Schedule data
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Recalculate next_run if schedule_type, start_time, days_of_week, or days_of_month changed
            if ('schedule_type' in schedule_data or 
                'start_time' in schedule_data or 
                'days_of_week' in schedule_data or 
                'days_of_month' in schedule_data or
                'months' in schedule_data):
                
                # Get current schedule
                current = await self.db.get_schedule(schedule_id)
                if not current:
                    self.logger.error(f"Schedule {schedule_id} not found")
                    return False
                    
                # Update with new values
                temp_schedule = {
                    'schedule_type': schedule_data.get('schedule_type', current['schedule_type']),
                    'start_time': schedule_data.get('start_time', current['start_time']),
                    'days_of_week': schedule_data.get('days_of_week', current['days_of_week']),
                    'days_of_month': schedule_data.get('days_of_month', current['days_of_month']),
                    'months': schedule_data.get('months', current['months'])
                }
                
                next_run = self._calculate_next_run(temp_schedule)
                schedule_data['next_run'] = next_run
                
            # Update schedule in database
            result = await self.db.update_schedule(schedule_id, schedule_data)
            
            if result:
                self.logger.info(f"Updated schedule {schedule_id}")
                
            return result
        except Exception as e:
            self.logger.error(f"Error updating schedule {schedule_id}: {e}")
            return False
            
    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            result = await self.db.delete_schedule(schedule_id)
            
            if result:
                self.logger.info(f"Deleted schedule {schedule_id}")
                
            return result
        except Exception as e:
            self.logger.error(f"Error deleting schedule {schedule_id}: {e}")
            return False
            
    async def enable_schedule(self, schedule_id: int, enabled: bool = True) -> bool:
        """Enable or disable a schedule.
        
        Args:
            schedule_id: Schedule ID
            enabled: Whether to enable or disable the schedule
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            result = await self.db.update_schedule(schedule_id, {'enabled': enabled})
            
            if result:
                status = "enabled" if enabled else "disabled"
                self.logger.info(f"{status.capitalize()} schedule {schedule_id}")
                
            return result
        except Exception as e:
            status = "enabling" if enabled else "disabling"
            self.logger.error(f"Error {status} schedule {schedule_id}: {e}")
            return False
            
    def register_pre_run_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback to be called before a schedule is run.
        
        Args:
            callback: Callback function that takes a schedule as argument
        """
        self._pre_run_callbacks.append(callback)
        
    def register_post_run_callback(self, callback: Callable[[Dict[str, Any], bool, Optional[str]], None]):
        """Register a callback to be called after a schedule is run.
        
        Args:
            callback: Callback function that takes a schedule, success flag, and error message as arguments
        """
        self._post_run_callbacks.append(callback) 