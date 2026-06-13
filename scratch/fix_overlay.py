import re

fpath = r'D:\Youtube Automation\AMTCE-v7.1\Compiler_Modules\orchestrator.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

# Check current state around line 3216
lines = content.splitlines()
for i, line in enumerate(lines[3205:3225], start=3206):
    print(f'{i}: {repr(line)}')

# Patch: replace the fallback "Style" with empty string
old_snippet = 'or ol.get("commercial_item_name", "Style"),'
new_snippet = 'or ol.get("commercial_item_name") or "",'

if old_snippet in content:
    content = content.replace(old_snippet, new_snippet, 1)
    # Also add comment above item_name line
    old_item_line = '"item_name": ol.get("item_name")\n                             or ol.get("commercial_item_name") or "",'
    new_item_block = (
        '# [FIX] Never fall back to generic niche string - prevents "NICHE VIRAL EXPRESSION" text overlay\n'
        '                             "item_name": ol.get("item_name")\n'
        '                             or ol.get("commercial_item_name") or "",'
    )
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: item_name fallback fixed (removed "Style" default)')
else:
    # Try CRLF variant
    old_crlf = old_snippet.replace('\n', '\r\n')
    if old_crlf in content:
        content = content.replace(old_crlf, new_snippet, 1)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print('SUCCESS (CRLF): item_name fallback fixed')
    else:
        print('NOT FOUND - searching for the pattern differently...')
        idx = content.find('commercial_item_name')
        while idx != -1:
            print(f'  Found at char {idx}: {repr(content[idx-50:idx+60])}')
            idx = content.find('commercial_item_name', idx + 1)
