import codecs

file_path = 'app/api/rescue.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 1. Add fields to Pydantic Schema
    if 'triggers_reevaluation: bool' in line and 'statutory_basis' not in line:
        new_lines.append('    statutory_basis: str | None = None\n')
        new_lines.append('    complexity: str | None = None\n')
        new_lines.append('    estimated_days_min: int | None = None\n')
        new_lines.append('    estimated_days_max: int | None = None\n')
    
    # 2. Add fields to Serializer
    if 'triggers_reevaluation=step.triggers_reevaluation,' in line and 'statutory_basis=' not in line:
        new_lines.append('        statutory_basis=getattr(step, "statutory_basis", None),\n')
        new_lines.append('        complexity=getattr(step, "complexity", None),\n')
        new_lines.append('        estimated_days_min=getattr(step, "estimated_days_min", None),\n')
        new_lines.append('        estimated_days_max=getattr(step, "estimated_days_max", None),\n')
        
    new_lines.append(line)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.writelines(new_lines)
print('SUCCESS: Bulletproof schema fix applied to rescue.py!')
