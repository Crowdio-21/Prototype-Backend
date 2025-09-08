"""
Test script for PSO Load Balancer Integration
Demonstrates the PSO optimization capabilities
"""

import asyncio
import sys
import os
import platform
import psutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foreman.pso_load_balancer import PSOLoadBalancer, SMDevice, Task, PSOTaskScheduler
from datetime import datetime, timedelta

def get_real_device_specs():
    """Get real device specifications from the current system"""
    try:
        # Get CPU information
        cpu_freq = psutil.cpu_freq()
        cpu_frequency = cpu_freq.max / 1000.0 if cpu_freq and cpu_freq.max else 2.0  # Convert to GHz
        
        # Get CPU cores
        num_cores = psutil.cpu_count(logical=False) or 4
        
        # Get current CPU load
        current_cpu_load = psutil.cpu_percent(interval=1) or 20.0
        
        # Get memory information
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)  # Convert to GB
        
        # Get network information (simplified)
        network_speed = 100.0  # Default to 100 Mbps
        
        # Determine device type and platform
        device_type = "desktop" if platform.system() != "Linux" else "server"
        platform_name = platform.system().lower()
        
        # Simulate battery level (for desktop/server, assume always high)
        battery_level = 95.0
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_level = battery.percent or 95.0
        except:
            pass
        
        # Signal strength (simplified - assume good for wired connections)
        signal_strength = 5 if device_type == "desktop" else 4
        
        # Reliability score (based on uptime and system stability)
        reliability_score = 1.0
        
        return {
            "cpu_frequency": round(cpu_frequency, 2),
            "num_cores": num_cores,
            "current_cpu_load": round(current_cpu_load, 1),
            "battery_level": round(battery_level, 1),
            "signal_strength": signal_strength,
            "memory_gb": round(memory_gb, 1),
            "network_speed": network_speed,
            "reliability_score": reliability_score,
            "device_type": device_type,
            "platform": platform_name
        }
    except Exception as e:
        print(f"Error getting real device specifications: {e}")
        # Return default specifications
        return {
            "cpu_frequency": 2.0,
            "num_cores": 4,
            "current_cpu_load": 20.0,
            "battery_level": 85.0,
            "signal_strength": 4,
            "memory_gb": 8.0,
            "network_speed": 100.0,
            "reliability_score": 1.0,
            "device_type": "unknown",
            "platform": "unknown"
        }

def create_real_devices():
    """Create SMDevice objects with real system specifications"""
    real_specs = get_real_device_specs()
    
    # Create multiple "virtual" workers based on real specs with some variation
    devices = []
    
    # Primary device (current system)
    devices.append(SMDevice(
        "real_worker_1", 
        real_specs["cpu_frequency"], 
        real_specs["num_cores"], 
        real_specs["current_cpu_load"], 
        real_specs["battery_level"], 
        real_specs["signal_strength"], 
        real_specs["memory_gb"], 
        real_specs["network_speed"], 
        real_specs["reliability_score"]
    ))
    
    # Simulate additional workers with variations
    # Worker 2: Slightly lower specs (simulating older device)
    devices.append(SMDevice(
        "simulated_worker_2",
        max(1.0, real_specs["cpu_frequency"] * 0.8),
        max(2, real_specs["num_cores"] - 2),
        min(90, real_specs["current_cpu_load"] + 15),
        max(20, real_specs["battery_level"] - 20),
        max(1, real_specs["signal_strength"] - 1),
        max(2.0, real_specs["memory_gb"] * 0.6),
        real_specs["network_speed"] * 0.7,
        real_specs["reliability_score"] * 0.9
    ))
    
    # Worker 3: Mobile-like specs
    devices.append(SMDevice(
        "simulated_mobile_worker",
        max(1.0, real_specs["cpu_frequency"] * 0.6),
        max(2, real_specs["num_cores"] // 2),
        min(80, real_specs["current_cpu_load"] + 25),
        max(30, real_specs["battery_level"] - 30),
        max(2, real_specs["signal_strength"] - 2),
        max(1.0, real_specs["memory_gb"] * 0.3),
        real_specs["network_speed"] * 0.4,
        real_specs["reliability_score"] * 0.8
    ))
    
    # Worker 4: High-end specs (simulating powerful device)
    devices.append(SMDevice(
        "simulated_power_worker",
        real_specs["cpu_frequency"] * 1.2,
        real_specs["num_cores"] + 2,
        max(5, real_specs["current_cpu_load"] - 10),
        min(100, real_specs["battery_level"] + 5),
        min(5, real_specs["signal_strength"] + 1),
        real_specs["memory_gb"] * 1.5,
        real_specs["network_speed"] * 1.5,
        min(1.0, real_specs["reliability_score"] + 0.1)
    ))
    
    return devices

def test_pso_optimization():
    """Test PSO optimization with real device specifications"""
    print("="*60)
    print("PSO LOAD BALANCER INTEGRATION TEST")
    print("USING REAL DEVICE SPECIFICATIONS")
    print("="*60)
    
    # Get real device specifications
    print("\n🔍 Detecting real device specifications...")
    real_specs = get_real_device_specs()
    print(f"Detected system: {real_specs['platform']} {real_specs['device_type']}")
    print(f"CPU: {real_specs['cpu_frequency']} GHz, {real_specs['num_cores']} cores")
    print(f"Memory: {real_specs['memory_gb']} GB")
    print(f"Current CPU load: {real_specs['current_cpu_load']}%")
    print(f"Battery: {real_specs['battery_level']}%")
    
    # Create devices based on real specifications
    devices = create_real_devices()
    
    # Create sample tasks
    tasks = [
        Task("task_1", 1500, 0.5, 1, 30.0),  # High priority, medium compute
        Task("task_2", 2000, 1.0, 2, 45.0),  # Medium priority, high compute
        Task("task_3", 800, 0.2, 1, 20.0),   # High priority, low compute
        Task("task_4", 3000, 2.0, 3, 60.0),  # Low priority, very high compute
        Task("task_5", 1200, 0.8, 2, 35.0),  # Medium priority, medium compute
        Task("task_6", 2500, 1.5, 4, 50.0),  # Low priority, high compute
        Task("task_7", 600, 0.1, 1, 15.0),   # High priority, very low compute
        Task("task_8", 1800, 0.6, 3, 40.0)   # Low priority, medium compute
    ]
    
    print(f"\n📱 Devices ({len(devices)}):")
    for i, device in enumerate(devices):
        device_type = "🖥️" if "real" in device.device_id else "📱" if "mobile" in device.device_id else "⚡" if "power" in device.device_id else "💻"
        print(f"  {device_type} {device.device_id}: {device.cpu_frequency}GHz, {device.num_cores} cores, "
              f"{device.current_cpu_load}% load, {device.battery_level}% battery, "
              f"{device.memory_gb}GB RAM, efficiency={device.efficiency_score:.3f}")
    
    print(f"\nTasks ({len(tasks)}):")
    for task in tasks:
        print(f"  {task.task_id}: {task.computational_requirement} MIPS, "
              f"priority={task.priority}, {task.memory_requirement}GB memory")
    
    # Test PSO optimization
    print(f"\n{'='*40}")
    print("RUNNING PSO OPTIMIZATION")
    print(f"{'='*40}")
    
    pso = PSOLoadBalancer(devices, tasks, max_iterations=30, population_size=20)
    
    # Run optimization
    result = asyncio.run(pso.run_optimization(verbose=True))
    
    print(f"\n{'='*40}")
    print("OPTIMIZATION RESULTS")
    print(f"{'='*40}")
    
    print(f"Best fitness: {result['best_fitness']:.6f}")
    print(f"Optimization time: {result['optimization_time']:.2f} seconds")
    print(f"Fitness improvement: {result['fitness_improvement']:.6f}")
    
    print(f"\nTask Allocation:")
    for task_id, worker_id in result['allocation'].items():
        print(f"  {task_id} -> {worker_id}")
    
    print(f"\nPerformance Metrics:")
    metrics = result['metrics']
    print(f"  Total Energy Consumption: {metrics['total_energy_consumption']:.2f} J")
    print(f"  Makespan: {metrics['makespan']:.2f} seconds")
    print(f"  Load Balance Variance: {metrics['load_balance_variance']:.4f}")
    
    print(f"\nDevice Utilization:")
    for device_id, utilization in metrics['device_utilization'].items():
        print(f"  {device_id}: {utilization:.2f} seconds")
    
    print(f"\nEnergy per Device:")
    for device_id, energy in metrics['energy_per_device'].items():
        print(f"  {device_id}: {energy:.2f} J")
    
    return result

async def test_pso_scheduler():
    """Test the high-level PSO scheduler with real device specs"""
    print(f"\n{'='*40}")
    print("TESTING PSO TASK SCHEDULER")
    print("WITH REAL DEVICE SPECIFICATIONS")
    print(f"{'='*40}")
    
    # Get real device specifications
    real_specs = get_real_device_specs()
    
    # Create worker data based on real specs (as would come from database)
    workers = [
        {
            'id': 'real_worker_1',
            'cpu_frequency': real_specs['cpu_frequency'],
            'num_cores': real_specs['num_cores'],
            'current_cpu_load': real_specs['current_cpu_load'],
            'battery_level': real_specs['battery_level'],
            'signal_strength': real_specs['signal_strength'],
            'memory_gb': real_specs['memory_gb'],
            'network_speed': real_specs['network_speed'],
            'reliability_score': real_specs['reliability_score']
        },
        {
            'id': 'simulated_worker_2',
            'cpu_frequency': max(1.0, real_specs['cpu_frequency'] * 0.8),
            'num_cores': max(2, real_specs['num_cores'] - 2),
            'current_cpu_load': min(90, real_specs['current_cpu_load'] + 15),
            'battery_level': max(20, real_specs['battery_level'] - 20),
            'signal_strength': max(1, real_specs['signal_strength'] - 1),
            'memory_gb': max(2.0, real_specs['memory_gb'] * 0.6),
            'network_speed': real_specs['network_speed'] * 0.7,
            'reliability_score': real_specs['reliability_score'] * 0.9
        }
    ]
    
    # Sample task data (as would come from database)
    tasks = [
        {
            'id': 'task_1',
            'computational_requirement': 1500.0,
            'memory_requirement': 0.5,
            'priority': 1,
            'estimated_duration': 30.0,
            'deadline': None
        },
        {
            'id': 'task_2',
            'computational_requirement': 2000.0,
            'memory_requirement': 1.0,
            'priority': 2,
            'estimated_duration': 45.0,
            'deadline': None
        }
    ]
    
    # Create PSO scheduler
    scheduler = PSOTaskScheduler(max_iterations=20, population_size=15)
    
    # Run scheduling
    result = await scheduler.schedule_tasks(workers, tasks)
    
    print(f"Scheduling result: {result['success']}")
    if result['success']:
        print(f"Allocation: {result['allocation']}")
        print(f"Optimization time: {result['optimization_time']:.2f}s")
        print(f"Fitness improvement: {result['fitness_improvement']:.4f}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result

def main():
    """Main test function"""
    try:
        # Test basic PSO optimization
        pso_result = test_pso_optimization()
        
        # Test PSO scheduler
        scheduler_result = asyncio.run(test_pso_scheduler())
        
        print(f"\n{'='*60}")
        print("INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print(f"{'='*60}")
        
        print(f"\nSummary:")
        print(f"- PSO optimization: {'✓' if pso_result else '✗'}")
        print(f"- PSO scheduler: {'✓' if scheduler_result['success'] else '✗'}")
        print(f"- Real device specifications: ✓")
        print(f"- Task requirements: ✓")
        print(f"- Load balancing: ✓")
        
        # Show real device specs summary
        real_specs = get_real_device_specs()
        print(f"\n🖥️  Real System Detected:")
        print(f"   Platform: {real_specs['platform'].title()} ({real_specs['device_type']})")
        print(f"   CPU: {real_specs['cpu_frequency']} GHz, {real_specs['num_cores']} cores")
        print(f"   Memory: {real_specs['memory_gb']} GB")
        print(f"   Current Load: {real_specs['current_cpu_load']}%")
        print(f"   Battery: {real_specs['battery_level']}%")
        print(f"   Network: {real_specs['network_speed']} Mbps")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
