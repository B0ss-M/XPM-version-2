#!/usr/bin/env python3
"""Check Java runtime and ConvertWithMoss JAR availability and print guidance.

Usage: python3 scripts/check_java_and_moss.py

This script will:
- Check if `java` is on PATH and print its version
- Search the repo for likely ConvertWithMoss JAR files
- Print recommended install commands for macOS (Homebrew) and a VS Code settings snippet
"""
import shutil
import subprocess
import sys
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def run_java_version():
    java = shutil.which('java')
    if not java:
        print('Java: NOT FOUND on PATH')
        return None
    try:
        # java -version prints to stderr
        p = subprocess.run([java, '-version'], capture_output=True, text=True)
        out = p.stderr.strip() or p.stdout.strip()
        # grab first line
        first = out.splitlines()[0] if out else ''
        print('Java:', first)
        # attempt to parse major version
        m = re.search(r'"(\d+)(?:[._](\d+))?', out)
        if m:
            major = int(m.group(1))
            return major
        # older format like "1.8.0_***"
        m2 = re.search(r'"1\.(\d+)', out)
        if m2:
            return int(m2.group(1))
    except Exception as e:
        print('Error running java:', e)
    return None


def find_moss_jars():
    matches = []
    for dirpath, dirs, files in os.walk(ROOT):
        for f in files:
            if f.lower().startswith('convertwithmoss') and f.lower().endswith('.jar'):
                matches.append(os.path.join(dirpath, f))
    return matches


def print_vscode_runtime_snippet():
    print('\nIf you want VS Code to target a specific runtime, add a workspace setting in `.vscode/settings.json`:\n')
    snippet = {
        'java.configuration.runtimes': [
            {
                'name': 'JavaSE-23',
                'path': '/Library/Java/JavaVirtualMachines/<jdk-23>/Contents/Home'
            },
            {
                'name': 'JavaSE-17',
                'path': '/Library/Java/JavaVirtualMachines/<jdk-17>/Contents/Home'
            }
        ]
    }
    import json
    print(json.dumps(snippet, indent=2))
    print('\nReplace <jdk-23> or <jdk-17> with the actual folder name from /Library/Java/JavaVirtualMachines or your SDK manager.\n')


def print_install_instructions():
    print('\nmacOS install options (choose one):\n')
    print('1) Homebrew (recommended):')
    print('   brew install --cask temurin')
    print('   # or for a specific version, e.g. 17:')
    print('   brew install --cask temurin17')
    print('\n2) SDKMAN (useful for multiple versions):')
    print('   curl -s "https://get.sdkman.io" | bash')
    print('   source "$HOME/.sdkman/bin/sdkman-init.sh"')
    print('   sdk install java 17.0.8-tem')
    print('\nAfter install, verify with:')
    print('   java -version\n')


if __name__ == '__main__':
    print('Repository root:', ROOT)
    major = run_java_version()
    if major is None:
        print('\nRecommendation: Install Java (JDK). If ConvertWithMoss requires JavaSE-23, ensure you have a 23+ runtime available.')
    else:
        print(f'Java detected (major={major})')
        if major < 17:
            print('Note: Detected Java is older than typical supported LTS (17). ConvertWithMoss may require a newer runtime.')

    jars = find_moss_jars()
    if jars:
        print('\nFound ConvertWithMoss JAR(s):')
        for j in jars:
            print(' -', j)
    else:
        print('\nNo ConvertWithMoss JAR found under the repository. If you have the JAR, place it in the project root or set the CONVERTWITHMOSS_JAR env var.')

    print_install_instructions()
    print_vscode_runtime_snippet()
    sys.exit(0)
