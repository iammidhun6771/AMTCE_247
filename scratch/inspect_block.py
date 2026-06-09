import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

with open('Compiler_Modules/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('editing_source"] = "none"')
print('FOUND AT:', idx)
segment = content[idx-40:idx+400]
print('REPR:', repr(segment))
