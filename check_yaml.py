import yaml, sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'd:\AMTCE\.github\workflows\amtce-runner.yml', 'r', encoding='utf-8') as f:
    content = f.read()
try:
    data = yaml.safe_load(content)
    jobs = list(data.get('jobs', {}).keys())
    print('YAML valid. Jobs:', jobs)
except yaml.YAMLError as e:
    print('YAML ERROR:', e)
