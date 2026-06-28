import sys

def resolve_conflicts_line_by_line(filepath, prefer_ours=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    resolved_lines = []
    ours_lines = []
    theirs_lines = []
    
    # States: 'NORMAL', 'OURS', 'THEIRS'
    state = 'NORMAL'
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('<<<<<<<'):
            state = 'OURS'
            ours_lines = []
            theirs_lines = []
        elif stripped.startswith('======='):
            state = 'THEIRS'
        elif stripped.startswith('>>>>>>>'):
            if prefer_ours:
                resolved_lines.extend(ours_lines)
            else:
                resolved_lines.extend(theirs_lines)
            state = 'NORMAL'
        else:
            if state == 'NORMAL':
                resolved_lines.append(line)
            elif state == 'OURS':
                ours_lines.append(line)
            elif state == 'THEIRS':
                theirs_lines.append(line)
                
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(resolved_lines)
        
    print(f"Resolved conflicts in {filepath} preferring {'ours' if prefer_ours else 'theirs'}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python resolve_json_conflicts.py <filepath>")
        sys.exit(1)
    resolve_conflicts_line_by_line(sys.argv[1])
