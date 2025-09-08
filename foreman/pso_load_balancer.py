"""
Particle Swarm Optimization (PSO) Load Balancer for CROWDio
Integrates with the existing task scheduling system to optimize task distribution
"""

import numpy as np
import random
import time
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

# Device and Task Classes for PSO
@dataclass
class SMDevice:
    device_id: str
    cpu_frequency: float  # GHz
    num_cores: int
    current_cpu_load: float  # percentage (0-100)
    battery_level: float = 100.0
    signal_strength: int = 5
    memory_gb: float = 8.0
    network_speed: float = 100.0  # Mbps
    reliability_score: float = 1.0  # Based on historical performance

    @property
    def computational_capacity(self) -> float:
        """Calculate computational capacity considering current load"""
        return self.cpu_frequency * self.num_cores * (1 - self.current_cpu_load / 100)

    @property
    def efficiency_score(self) -> float:
        """Calculate overall efficiency score for task assignment"""
        capacity_factor = self.computational_capacity
        battery_factor = self.battery_level / 100
        signal_factor = self.signal_strength / 5
        reliability_factor = self.reliability_score
        return capacity_factor * battery_factor * signal_factor * reliability_factor

    @property
    def power_efficiency(self) -> float:
        """Calculate power efficiency for energy-aware scheduling"""
        return self.computational_capacity / (self.cpu_frequency * self.num_cores * 0.2 + 0.5)

@dataclass
class Task:
    task_id: str
    computational_requirement: float  # MIPS required
    memory_requirement: float = 0.0  # GB required
    priority: int = 1  # 1-5, where 1 is highest priority
    estimated_duration: float = 0.0  # seconds
    deadline: Optional[datetime] = None

    def __str__(self):
        return f"Task({self.task_id}, req={self.computational_requirement:.0f}, priority={self.priority})"

@dataclass
class Particle:
    position: np.ndarray
    velocity: np.ndarray
    fitness: float
    best_position: np.ndarray
    best_fitness: float

class PSOLoadBalancer:
    """Particle Swarm Optimization Load Balancer for CROWDio"""
    
    def __init__(self, devices: List[SMDevice], tasks: List[Task],
                 max_iterations: int = 50, population_size: int = 30):
        self.devices = devices
        self.tasks = tasks
        self.max_iterations = max_iterations
        self.population_size = population_size
        self.num_tasks = len(tasks)
        self.num_devices = len(devices)

        # PSO parameters
        self.w_max = 0.9
        self.w_min = 0.1
        self.c1 = 2.0
        self.c2 = 2.0

        self.global_best_position = None
        self.global_best_fitness = float('inf')
        self.fitness_history = []

        # Pre-calculate device metrics for efficiency
        self.device_capacities = [device.computational_capacity for device in devices]
        self.device_efficiency = [device.efficiency_score for device in devices]
        self.device_power_efficiency = [device.power_efficiency for device in devices]

        print(f"Initialized PSO Load Balancer with {self.num_devices} devices and {self.num_tasks} tasks")

    def fitness_function(self, position: np.ndarray) -> float:
        """Calculate fitness of a task assignment solution"""
        assignment = np.clip(np.round(position), 0, self.num_devices - 1).astype(int)
        
        # Initialize metrics
        device_loads = np.zeros(self.num_devices)
        device_energy = np.zeros(self.num_devices)
        device_memory_usage = np.zeros(self.num_devices)
        total_energy = 0.0
        max_execution_time = 0.0
        priority_penalty = 0.0
        deadline_violations = 0.0

        # Calculate metrics for each task assignment
        for i, task in enumerate(self.tasks):
            device_idx = assignment[i]
            device = self.devices[device_idx]
            
            # Skip if device has no capacity
            if self.device_capacities[device_idx] <= 0:
                return float('inf')

            # Calculate execution time
            execution_time = task.computational_requirement / (self.device_capacities[device_idx] * 1000)
            device_loads[device_idx] += execution_time
            max_execution_time = max(max_execution_time, device_loads[device_idx])

            # Calculate energy consumption
            power_consumption = self.calculate_power_consumption(device, device_loads[device_idx])
            device_energy[device_idx] += power_consumption * execution_time
            total_energy += device_energy[device_idx]

            # Track memory usage
            device_memory_usage[device_idx] += task.memory_requirement

            # Priority-based penalty (higher priority tasks should get better devices)
            device_quality = self.device_efficiency[device_idx]
            priority_penalty += (6 - task.priority) * (1 / (device_quality + 0.1))

            # Deadline violation penalty
            if task.deadline and execution_time > 0:
                time_until_deadline = (task.deadline - datetime.now()).total_seconds()
                if execution_time > time_until_deadline:
                    deadline_violations += (execution_time - time_until_deadline) * 10

        # Calculate load balance variance
        load_variance = np.var(device_loads) if len(device_loads) > 1 else 0

        # Memory constraint violations
        memory_violations = 0
        for i, device in enumerate(self.devices):
            if device_memory_usage[i] > device.memory_gb:
                memory_violations += (device_memory_usage[i] - device.memory_gb) * 100

        # Weighted fitness function
        fitness = (
            0.3 * total_energy +           # Energy efficiency
            0.25 * max_execution_time +    # Makespan (total execution time)
            0.2 * load_variance +          # Load balancing
            0.15 * priority_penalty +      # Priority consideration
            0.1 * deadline_violations      # Deadline violations
        )

        # Add penalty for memory violations
        if memory_violations > 0:
            fitness += memory_violations

        return fitness

    def calculate_power_consumption(self, device: SMDevice, current_load: float) -> float:
        """Calculate power consumption for a device under current load"""
        base_power = 0.5  # Base power consumption in watts
        cpu_power = device.cpu_frequency * device.num_cores * 0.2
        load_factor = min(current_load / 5.0, 1.0)
        dynamic_power = cpu_power * load_factor
        battery_factor = 0.8 + 0.2 * (device.battery_level / 100)
        return (base_power + dynamic_power) / battery_factor

    def initialize_population(self) -> List[Particle]:
        """Initialize the particle population with diverse strategies"""
        particles = []
        
        for i in range(self.population_size):
            if i < self.population_size // 3:
                # Random initialization
                position = np.random.uniform(0, self.num_devices - 0.01, self.num_tasks)
            elif i < 2 * self.population_size // 3:
                # Round-robin initialization
                position = np.zeros(self.num_tasks)
                for j in range(self.num_tasks):
                    position[j] = (j % self.num_devices) + np.random.uniform(-0.3, 0.3)
                position = np.clip(position, 0, self.num_devices - 0.01)
            else:
                # Best-fit initialization (assign to most efficient devices)
                position = np.zeros(self.num_tasks)
                for j, task in enumerate(self.tasks):
                    # Find best device for this task based on efficiency and current load
                    best_device_idx = 0
                    best_score = 0
                    for k, device in enumerate(self.devices):
                        score = self.device_efficiency[k] / (1 + task.computational_requirement / 1000)
                        if score > best_score:
                            best_score = score
                            best_device_idx = k
                    position[j] = best_device_idx + np.random.uniform(-0.2, 0.2)
                position = np.clip(position, 0, self.num_devices - 0.01)

            velocity = np.random.uniform(-1, 1, self.num_tasks)
            fitness = self.fitness_function(position)
            particle = Particle(position.copy(), velocity, fitness, position.copy(), fitness)
            particles.append(particle)
            
            if fitness < self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best_position = position.copy()

        print(f"Initial best fitness: {self.global_best_fitness:.4f}")
        return particles

    def update_particle(self, particle: Particle, iteration: int) -> bool:
        """Update a particle's position and velocity"""
        r1, r2 = random.random(), random.random()

        # Nonlinear inertia weight decay
        self.w = self.w_min + (self.w_max - self.w_min) * np.exp(-3 * iteration / self.max_iterations)

        # Dynamic acceleration coefficients
        self.c1 = 2.5 - 2.0 * (iteration / self.max_iterations)
        self.c2 = 0.5 + 2.0 * (iteration / self.max_iterations)

        # Update velocity
        cognitive = self.c1 * r1 * (particle.best_position - particle.position)
        social = self.c2 * r2 * (self.global_best_position - particle.position)
        particle.velocity = self.w * particle.velocity + cognitive + social
        
        # Velocity clamping
        v_max = 1.5
        particle.velocity = np.clip(particle.velocity, -v_max, v_max)
        
        # Update position
        particle.position += particle.velocity
        particle.position = np.clip(particle.position, 0, self.num_devices - 0.01)

        # Mutation injection for exploration
        if random.random() < 0.1:
            particle.position += np.random.normal(0, 0.2, self.num_tasks)
            particle.position = np.clip(particle.position, 0, self.num_devices - 0.01)

        # Evaluate new fitness
        new_fitness = self.fitness_function(particle.position)
        particle.fitness = new_fitness
        
        # Update personal best
        if new_fitness < particle.best_fitness:
            particle.best_fitness = new_fitness
            particle.best_position = particle.position.copy()

        # Update global best
        improvement_found = False
        if new_fitness < self.global_best_fitness:
            self.global_best_fitness = new_fitness
            self.global_best_position = particle.position.copy()
            improvement_found = True

        return improvement_found

    async def run_optimization(self, verbose: bool = True) -> Dict:
        """Run PSO optimization to find optimal task assignment"""
        print("\nStarting PSO Optimization...")
        start_time = time.time()
        
        particles = self.initialize_population()
        self.fitness_history = [self.global_best_fitness]
        stagnation_counter = 0
        last_best = self.global_best_fitness

        for iteration in range(self.max_iterations):
            improvements = 0
            
            for particle in particles:
                if self.update_particle(particle, iteration):
                    improvements += 1
            
            self.fitness_history.append(self.global_best_fitness)
            
            # Check for stagnation
            if abs(self.global_best_fitness - last_best) < 1e-8:
                stagnation_counter += 1
            else:
                stagnation_counter = 0
                last_best = self.global_best_fitness
            
            # Restart particles if stagnated
            if stagnation_counter > 15:
                await self.restart_particles(particles)
                stagnation_counter = 0
            
            # Yield control to allow other async operations
            if iteration % 5 == 0:
                await asyncio.sleep(0)
            
            if verbose and (iteration + 1) % 10 == 0:
                print(f"Iter {iteration+1:2d}: Fitness={self.global_best_fitness:.6f}, Improvements={improvements}, w={self.w:.3f}")

        optimization_time = time.time() - start_time
        best_assignment = np.clip(np.round(self.global_best_position), 0, self.num_devices - 1).astype(int)
        
        # Create allocation mapping
        allocation = {}
        for i in range(self.num_tasks):
            task = self.tasks[i]
            device = self.devices[best_assignment[i]]
            allocation[task.task_id] = device.device_id

        # Calculate detailed metrics
        metrics = self.calculate_detailed_metrics(best_assignment)

        result = {
            'allocation': allocation,
            'best_fitness': self.global_best_fitness,
            'optimization_time': optimization_time,
            'iterations': self.max_iterations,
            'metrics': metrics,
            'assignment_array': best_assignment.tolist(),
            'fitness_improvement': self.fitness_history[0] - self.global_best_fitness
        }

        print(f"\nOptimization completed in {optimization_time:.2f} seconds")
        print(f"Final fitness: {self.global_best_fitness:.6f}")
        print(f"Total improvement: {result['fitness_improvement']:.6f}")
        
        return result

    async def restart_particles(self, particles: List[Particle]):
        """Restart particles to escape local optima"""
        # Keep best particles
        particles.sort(key=lambda p: p.fitness)
        survivors = min(3, len(particles) // 4)
        
        # Reinitialize worst particles
        for i in range(survivors, len(particles)):
            particles[i].position = np.random.uniform(0, self.num_devices - 0.01, self.num_tasks)
            particles[i].velocity = np.random.uniform(-1, 1, self.num_tasks)
            particles[i].fitness = self.fitness_function(particles[i].position)
            particles[i].best_position = particles[i].position.copy()
            particles[i].best_fitness = particles[i].fitness

    def calculate_detailed_metrics(self, assignment: np.ndarray) -> Dict:
        """Calculate detailed performance metrics for the assignment"""
        device_loads = np.zeros(self.num_devices)
        device_energy = np.zeros(self.num_devices)
        device_memory_usage = np.zeros(self.num_devices)
        
        for i, task in enumerate(self.tasks):
            device_idx = assignment[i]
            device = self.devices[device_idx]
            
            exec_time = task.computational_requirement / (self.device_capacities[device_idx] * 1000)
            device_loads[device_idx] += exec_time
            device_memory_usage[device_idx] += task.memory_requirement
            
            power = self.calculate_power_consumption(device, device_loads[device_idx])
            device_energy[device_idx] += power * exec_time

        return {
            'total_energy_consumption': float(np.sum(device_energy)),
            'makespan': float(np.max(device_loads)),
            'load_balance_variance': float(np.var(device_loads)),
            'device_utilization': {
                self.devices[i].device_id: float(device_loads[i]) 
                for i in range(self.num_devices)
            },
            'energy_per_device': {
                self.devices[i].device_id: float(device_energy[i]) 
                for i in range(self.num_devices)
            },
            'memory_usage_per_device': {
                self.devices[i].device_id: float(device_memory_usage[i]) 
                for i in range(self.num_devices)
            }
        }

    def get_convergence_data(self) -> Dict:
        """Get convergence data for monitoring"""
        return {
            'fitness_history': self.fitness_history,
            'current_best_fitness': self.global_best_fitness,
            'improvement_percentage': (
                (self.fitness_history[0] - self.global_best_fitness) / self.fitness_history[0] * 100
                if self.fitness_history[0] > 0 else 0
            )
        }


class PSOTaskScheduler:
    """High-level task scheduler that integrates PSO with CROWDio system"""
    
    def __init__(self, max_iterations: int = 50, population_size: int = 30):
        self.max_iterations = max_iterations
        self.population_size = population_size
        self.last_optimization_time = None
        self.optimization_cache = {}

    async def schedule_tasks(self, workers: List[Dict], tasks: List[Dict]) -> Dict:
        """Schedule tasks using PSO optimization"""
        try:
            # Convert workers to SMDevice objects
            devices = []
            for worker in workers:
                device = SMDevice(
                    device_id=worker['id'],
                    cpu_frequency=worker.get('cpu_frequency', 2.0),
                    num_cores=worker.get('num_cores', 4),
                    current_cpu_load=worker.get('current_cpu_load', 20.0),
                    battery_level=worker.get('battery_level', 85.0),
                    signal_strength=worker.get('signal_strength', 4),
                    memory_gb=worker.get('memory_gb', 8.0),
                    network_speed=worker.get('network_speed', 100.0),
                    reliability_score=worker.get('reliability_score', 1.0)
                )
                devices.append(device)

            # Convert tasks to Task objects
            pso_tasks = []
            for task in tasks:
                pso_task = Task(
                    task_id=task['id'],
                    computational_requirement=task.get('computational_requirement', 1000.0),
                    memory_requirement=task.get('memory_requirement', 0.1),
                    priority=task.get('priority', 3),
                    estimated_duration=task.get('estimated_duration', 0.0),
                    deadline=task.get('deadline')
                )
                pso_tasks.append(pso_task)

            # Run PSO optimization
            pso = PSOLoadBalancer(
                devices=devices,
                tasks=pso_tasks,
                max_iterations=self.max_iterations,
                population_size=self.population_size
            )

            result = await pso.run_optimization(verbose=False)
            self.last_optimization_time = time.time()

            return {
                'success': True,
                'allocation': result['allocation'],
                'metrics': result['metrics'],
                'optimization_time': result['optimization_time'],
                'fitness_improvement': result['fitness_improvement']
            }

        except Exception as e:
            print(f"Error in PSO scheduling: {e}")
            return {
                'success': False,
                'error': str(e),
                'allocation': {}
            }

    def get_scheduling_stats(self) -> Dict:
        """Get scheduling statistics"""
        return {
            'last_optimization_time': self.last_optimization_time,
            'max_iterations': self.max_iterations,
            'population_size': self.population_size,
            'cache_size': len(self.optimization_cache)
        }
