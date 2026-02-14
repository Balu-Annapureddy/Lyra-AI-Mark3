import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lyra.planning.execution_planner import ExecutionPlanner
from lyra.execution.execution_gateway import ExecutionGateway

planner = ExecutionPlanner()
plan = planner.create_plan('Read file.txt')
print(f'Plan: {plan.plan_id}')
print(f'Steps: {len(plan.steps)}')
for s in plan.steps:
    print(f'  - {s.tool_required}: {s.risk_level}')

gateway = ExecutionGateway()
errors = gateway._validate_plan(plan)
if errors:
    print(f'Validation errors:')
    for e in errors:
        print(f'  - {e.reason}')
else:
    print('Validation passed')

result = gateway.execute_plan(plan, confirmed=True)
print(f'Success: {result.success}')
print(f'Error: {result.error}')
