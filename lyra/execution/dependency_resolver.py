"""
Dependency Resolver - Phase 4C
Resolves step dependencies and execution order
Detects circular dependencies
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from lyra.planning.planning_schema import PlanStep
from lyra.core.logger import get_logger


@dataclass
class DependencyNode:
    """Node in dependency graph"""
    step_id: str
    step: PlanStep
    depends_on: List[str]
    dependents: List[str]


class DependencyResolver:
    """
    Resolves step dependencies and execution order
    Uses topological sort for ordering
    Detects circular dependencies
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def resolve_execution_order(self, steps: List[PlanStep]) -> List[PlanStep]:
        """
        Resolve execution order based on dependencies
        
        Args:
            steps: List of execution steps
        
        Returns:
            Steps in execution order
        
        Raises:
            ValueError: If circular dependencies detected
        """
        # Build dependency graph
        graph = self._build_graph(steps)
        
        # Detect circular dependencies
        cycle = self._detect_cycle(graph)
        if cycle:
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        # Topological sort
        ordered = self._topological_sort(graph)
        
        self.logger.info(f"Resolved execution order: {[s.step_id for s in ordered]}")
        
        return ordered
    
    def _build_graph(self, steps: List[PlanStep]) -> Dict[str, DependencyNode]:
        """Build dependency graph from steps"""
        graph = {}
        
        # Create nodes
        for step in steps:
            graph[step.step_id] = DependencyNode(
                step_id=step.step_id,
                step=step,
                depends_on=step.depends_on.copy(),
                dependents=[]
            )
        
        # Build edges (dependents)
        for step_id, node in graph.items():
            for dep_id in node.depends_on:
                if dep_id in graph:
                    graph[dep_id].dependents.append(step_id)
                else:
                    raise ValueError(f"Step {step_id} depends on unknown step {dep_id}")
        
        return graph
    
    def _detect_cycle(self, graph: Dict[str, DependencyNode]) -> Optional[List[str]]:
        """
        Detect circular dependencies using DFS
        
        Returns:
            Cycle path if found, None otherwise
        """
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str, path: List[str]) -> Optional[List[str]]:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            node = graph[node_id]
            for dep_id in node.depends_on:
                if dep_id not in visited:
                    cycle = dfs(dep_id, path.copy())
                    if cycle:
                        return cycle
                elif dep_id in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep_id)
                    return path[cycle_start:] + [dep_id]
            
            rec_stack.remove(node_id)
            return None
        
        for node_id in graph:
            if node_id not in visited:
                cycle = dfs(node_id, [])
                if cycle:
                    return cycle
        
        return None
    
    def _topological_sort(self, graph: Dict[str, DependencyNode]) -> List[PlanStep]:
        """
        Topological sort using Kahn's algorithm
        
        Returns:
            Steps in execution order
        """
        # Calculate in-degrees
        in_degree = {node_id: len(node.depends_on) for node_id, node in graph.items()}
        
        # Queue of nodes with no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        
        result = []
        
        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            
            # Process node with no dependencies
            node_id = queue.pop(0)
            node = graph[node_id]
            result.append(node.step)
            
            # Reduce in-degree of dependents
            for dependent_id in node.dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        # Check if all nodes processed (should be, cycle already detected)
        if len(result) != len(graph):
            raise ValueError("Topological sort failed (should not happen)")
        
        return result
    
    def substitute_outputs(self, step: PlanStep, 
                          context: Dict[str, Any]) -> PlanStep:
        """
        Substitute output references in step validated_input
        
        Args:
            step: Execution step
            context: Execution context with previous outputs
        
        Returns:
            Step with substituted validated_input
        """
        # Create copy of step
        import copy
        step_copy = copy.deepcopy(step)
        
        # Substitute validated_input
        for param_name, param_value in step_copy.validated_input.items():
            if isinstance(param_value, str) and param_value.startswith("${") and param_value.endswith("}"):
                # Extract reference (e.g., "${step1.output}")
                ref = param_value[2:-1]
                parts = ref.split(".")
                
                if len(parts) == 2:
                    ref_step_id, ref_field = parts
                    
                    # Look up in context
                    if ref_step_id in context and ref_field in context[ref_step_id]:
                        step_copy.validated_input[param_name] = context[ref_step_id][ref_field]
                        self.logger.info(f"Substituted {param_name}: {param_value} -> {context[ref_step_id][ref_field]}")
                    else:
                        raise ValueError(f"Cannot resolve reference: {param_value}")
        
        return step_copy
