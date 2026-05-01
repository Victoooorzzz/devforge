import os
import glob
import re

apps_dir = r'c:\Users\victor\Downloads\microsaas\devforge\apps'

def replace_in_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    orig = content
    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)
        
    if orig != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {path}')

replacements = [
    (r'\$12', '$9.99'),
    (r'\$25', '$9.99'),
    (r'\$19/mo', '$9.99/mo'),
    (r'\$19/month', '$9.99/month'),
    (r'\$19', '$9.99'),
    (r'\$49', '$9.99'),
    (r'\$15', '$9.99'),
    (r'\$29', '$9.99'),
    (r'\$9\b', '$9.99'),
    (r'\$0', '$9.99'),
    (r'\$9–19', '$9.99'),
    (r'14-Day', '7-Day'),
    (r'14-day', '7-day'),
]

for page_file in glob.glob(os.path.join(apps_dir, '*', 'frontend', 'src', 'app', 'page.tsx')):
    replace_in_file(page_file, replacements)

for register_file in glob.glob(os.path.join(apps_dir, '*', 'frontend', 'src', 'app', 'register', 'page.tsx')):
    replace_in_file(register_file, replacements)
