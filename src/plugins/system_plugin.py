
"""
System information plugin for monitoring system resources.
"""

import logging
import platform
import psutil
from datetime import datetime
from typing import Dict, Any


class SystemPlugin:
    """System information and monitoring plugin."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def can_handle(self, text: str) -> bool:
        """Check if this plugin can handle the given text."""
        system_indicators = [
            'system', 'computer', 'memory', 'ram', 'cpu',
            'disk', 'storage', 'process', 'performance',
            'usage', 'status', 'information', 'stats'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in system_indicators)
    
    def process(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process system information request."""
        try:
            text_lower = text.lower()
            
            if 'memory' in text_lower or 'ram' in text_lower:
                return self._get_memory_info()
            elif 'cpu' in text_lower or 'processor' in text_lower:
                return self._get_cpu_info()
            elif 'disk' in text_lower or 'storage' in text_lower:
                return self._get_disk_info()
            elif 'process' in text_lower:
                return self._get_process_info()
            elif 'temperature' in text_lower:
                return self._get_temperature_info()
            else:
                return self._get_general_info()
                
        except Exception as e:
            self.logger.error(f"System plugin error: {e}")
            return {
                "success": False,
                "response": f"System information error: {str(e)}"
            }
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            response = (
                f"Memory usage: {memory.percent}% "
                f"({memory.used // (1024**3)} GB used of {memory.total // (1024**3)} GB total). "
                f"Swap usage: {swap.percent}%"
            )
            
            return {
                "success": True,
                "response": response,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used // (1024**3),
                "memory_total_gb": memory.total // (1024**3),
                "swap_percent": swap.percent
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Error getting memory information: {str(e)}"
            }
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU usage information."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            response = (
                f"CPU usage: {cpu_percent}% "
                f"({cpu_count} cores)"
            )
            
            if cpu_freq:
                response += f", frequency: {cpu_freq.current:.0f} MHz"
            
            return {
                "success": True,
                "response": response,
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_frequency": cpu_freq.current if cpu_freq else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Error getting CPU information: {str(e)}"
            }
    
    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage information."""
        try:
            disk = psutil.disk_usage('/')
            
            response = (
                f"Disk usage: {disk.percent}% "
                f"({disk.used // (1024**3)} GB used of {disk.total // (1024**3)} GB total)"
            )
            
            return {
                "success": True,
                "response": response,
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used // (1024**3),
                "disk_total_gb": disk.total // (1024**3)
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Error getting disk information: {str(e)}"
            }
    
    def _get_process_info(self) -> Dict[str, Any]:
        """Get running process information."""
        try:
            process_count = len(psutil.pids())
            
            # Get top 5 processes by CPU usage
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            top_processes = processes[:5]
            
            response = f"Running processes: {process_count}. "
            if top_processes:
                top_names = [p['name'] for p in top_processes if p['name']]
                response += f"Top processes: {', '.join(top_names[:3])}"
            
            return {
                "success": True,
                "response": response,
                "process_count": process_count,
                "top_processes": top_processes
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Error getting process information: {str(e)}"
            }
    
    def _get_temperature_info(self) -> Dict[str, Any]:
        """Get system temperature information."""
        try:
            # Temperature monitoring is platform-specific and may not be available
            temps = psutil.sensors_temperatures()
            
            if not temps:
                return {
                    "success": False,
                    "response": "Temperature sensors not available on this system."
                }
            
            temp_info = []
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current:
                        temp_info.append(f"{name}: {entry.current}°C")
            
            if temp_info:
                response = "System temperatures: " + ", ".join(temp_info[:3])
            else:
                response = "No temperature readings available."
            
            return {
                "success": True,
                "response": response,
                "temperatures": temps
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": "Temperature monitoring not available on this system."
            }
    
    def _get_general_info(self) -> Dict[str, Any]:
        """Get general system information."""
        try:
            # System info
            system_info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "processor": platform.processor()
            }
            
            # Resource usage
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            # Boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            response = (
                f"System: {system_info['platform']} {system_info['platform_release']}, "
                f"CPU: {cpu_percent}%, Memory: {memory.percent}%, "
                f"Disk: {disk.percent}%, Uptime: {uptime.days} days"
            )
            
            return {
                "success": True,
                "response": response,
                "system_info": system_info,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "uptime_days": uptime.days
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Error getting system information: {str(e)}"
            }
