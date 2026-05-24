#!/usr/bin/env python3
"""
scan_porting_issues.py
Does three things:
1. Scans C and Fortran code for Solaris-specific patterns
2. Extracts all function names from C files
3. Calculates cyclomatic complexity and exports CSV report
Author: Abhijit
"""

import os
import sys
import re
import csv

# ─────────────────────────────────────────
# PATTERN DICTIONARIES
# ─────────────────────────────────────────

C_PATTERNS = {
    "sys/systeminfo.h":  "Replace with sys/utsname.h",
    "sysinfo(":          "Replace with uname()",
    "sys/procfs.h":      "Use /proc filesystem directly on Linux",
    "door_call(":        "No Linux equivalent — redesign IPC",
    "thr_create(":       "Replace with pthread_create()",
    "thr_join(":         "Replace with pthread_join()",
    "mutex_init(":       "Replace with pthread_mutex_init()",
    "rwlock_init(":      "Replace with pthread_rwlock_init()",
    "sys/lwp.h":         "Use POSIX threads instead",
    "atomic_add_32(":    "Replace with __atomic_add_fetch()",
    "atomic_cas_32(":    "Replace with __atomic_compare_exchange()",
    "gethrtime(":        "Replace with clock_gettime(CLOCK_MONOTONIC)",
    "gethrvtime(":       "Replace with clock_gettime(CLOCK_PROCESS_CPUTIME_ID)",
    "SIGPOLL":           "Replace with SIGIO on Linux",
    "sys/stropts.h":     "STREAMS not available on Linux — use sockets",
    "putmsg(":           "STREAMS not available — redesign",
    "getmsg(":           "STREAMS not available — redesign",
    "#pragma ident":     "Remove — Sun compiler pragma, not needed on GCC",
    "__sun":             "Solaris platform macro — add #ifdef __linux__ alternative",
    "__SVR4":            "Solaris SVR4 macro — add Linux alternative",
}

FORTRAN_PATTERNS = {
    "REAL*4":            "Use REAL(KIND=4) for portability with gfortran",
    "REAL*8":            "Use DOUBLE PRECISION or REAL(KIND=8)",
    "INTEGER*4":         "Use INTEGER(KIND=4) for portability",
    "INTEGER*8":         "Use INTEGER(KIND=8) for portability",
    "COMPLEX*8":         "Use COMPLEX(KIND=4) for portability",
    "COMPLEX*16":        "Use COMPLEX(KIND=8) for portability",
    "%VAL(":             "Sun Studio extension — use ISO_C_BINDING instead",
    "%REF(":             "Sun Studio extension — use ISO_C_BINDING instead",
    "%LOC(":             "Sun Studio extension — use C_LOC() instead",
    "INCLUDE 'mpif.h'":  "Use USE mpi module instead",
    "IMPLICIT REAL":     "Remove — use IMPLICIT NONE with gfortran",
    "PAUSE":             "Deprecated in gfortran — use READ(*,*)",
    "ENCODE(":           "Sun extension — use WRITE to internal file",
    "DECODE(":           "Sun extension — use READ from internal file",
}

# ─────────────────────────────────────────
# CYCLOMATIC COMPLEXITY
# ─────────────────────────────────────────

# These keywords each add 1 to complexity score
COMPLEXITY_KEYWORDS = [
    r'\bif\b',
    r'\belse\b',
    r'\bfor\b',
    r'\bwhile\b',
    r'\bcase\b',
    r'\bcatch\b',
    r'\b&&\b',
    r'\|\|',
    r'\?\s*\w',      # ternary operator
]

def calculate_complexity(lines):
    """
    Calculates cyclomatic complexity of a block of code.
    Starts at 1, adds 1 for each decision point found.
    """
    score = 1
    for line in lines:
        for keyword in COMPLEXITY_KEYWORDS:
            if re.search(keyword, line):
                score += 1
    return score

def get_risk(score):
    """Converts complexity score to human readable risk label."""
    if score <= 5:
        return "Low"
    elif score <= 10:
        return "Medium"
    else:
        return "High"

# ─────────────────────────────────────────
# FUNCTION EXTRACTION (C files)
# ─────────────────────────────────────────

def extract_functions_c(filepath):
    """
    Extracts function names and their complexity from a C file.
    Looks for pattern: return_type function_name(...) {
    """
    functions = []
    try:
        with open(filepath, "r", errors="ignore") as f:
            lines = f.readlines()

        # Regex to match C function definitions
        # Matches: word word(...) { pattern
        func_pattern = re.compile(
            r'^[\w\s\*]+\s+(\w+)\s*\([^;]*\)\s*\{'
        )

        i = 0
        while i < len(lines):
            match = func_pattern.match(lines[i].strip())
            if match:
                func_name = match.group(1)

                # Skip common false positives
                skip = ["if", "for", "while", "switch",
                        "else", "do", "return", "main"]
                if func_name not in skip:
                    # Collect function body until closing brace
                    body = []
                    brace_count = 0
                    j = i
                    while j < len(lines):
                        body.append(lines[j])
                        brace_count += lines[j].count("{")
                        brace_count -= lines[j].count("}")
                        if brace_count == 0 and j > i:
                            break
                        j += 1

                    complexity = calculate_complexity(body)
                    functions.append({
                        "file":       filepath,
                        "function":   func_name,
                        "line":       i + 1,
                        "complexity": complexity,
                        "risk":       get_risk(complexity),
                        "loc":        len(body),
                    })
            i += 1

    except Exception as e:
        print(f"Could not parse {filepath}: {e}")

    return functions

# ─────────────────────────────────────────
# PORTING ISSUE SCANNER
# ─────────────────────────────────────────

def get_patterns_for_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".f", ".f90", ".f95", ".for"):
        return FORTRAN_PATTERNS, "Fortran"
    elif ext in (".c", ".h", ".cpp"):
        return C_PATTERNS, "C"
    return {}, "Unknown"

def scan_file(filepath):
    issues = []
    patterns, filetype = get_patterns_for_file(filepath)
    try:
        with open(filepath, "r", errors="ignore") as f:
            for line_num, line in enumerate(f, start=1):
                for pattern, suggestion in patterns.items():
                    if pattern in line:
                        issues.append({
                            "file":       filepath,
                            "filetype":   filetype,
                            "line":       line_num,
                            "pattern":    pattern,
                            "suggestion": suggestion,
                            "code":       line.strip()
                        })
    except Exception as e:
        print(f"Could not read {filepath}: {e}")
    return issues

def scan_directory(directory):
    all_issues  = []
    all_funcs   = []
    extensions  = (".c", ".h", ".f", ".f90", ".f95", ".for", ".F", ".F90")

    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(extensions):
                filepath = os.path.join(root, filename)
                all_issues.extend(scan_file(filepath))

                # Extract functions only from C files
                if filename.endswith((".c", ".h")):
                    all_funcs.extend(extract_functions_c(filepath))

    return all_issues, all_funcs

# ─────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────

def print_porting_report(issues):
    if not issues:
        print("\nNo Solaris-specific patterns found. Code looks portable!")
        return

    c_issues = [i for i in issues if i["filetype"] == "C"]
    f_issues  = [i for i in issues if i["filetype"] == "Fortran"]

    print(f"\n{'='*60}")
    print(f"  PORTING SCAN REPORT")
    print(f"{'='*60}")
    print(f"  C issues      : {len(c_issues)}")
    print(f"  Fortran issues: {len(f_issues)}")
    print(f"  Total         : {len(issues)}")
    print(f"{'='*60}\n")

    current_file = None
    for issue in issues:
        if issue["file"] != current_file:
            current_file = issue["file"]
            print(f"FILE: {current_file} [{issue['filetype']}]")
            print("-" * 60)
        print(f"  Line {issue['line']:4d} | Pattern : {issue['pattern']}")
        print(f"         | Fix     : {issue['suggestion']}")
        print(f"         | Code    : {issue['code']}")
        print()

    print(f"{'='*60}")
    print(f"Total : {len(issues)} issues across "
          f"{len(set(i['file'] for i in issues))} file(s)")
    print(f"{'='*60}\n")

def print_complexity_report(funcs):
    if not funcs:
        print("No functions found.")
        return

    print(f"\n{'='*60}")
    print(f"  FUNCTION COMPLEXITY REPORT")
    print(f"{'='*60}")
    print(f"  {'Function':<25} {'Line':>5} {'LOC':>5} "
          f"{'Score':>6} {'Risk':<8} File")
    print(f"  {'-'*25} {'-'*5} {'-'*5} {'-'*6} {'-'*8} {'-'*20}")

    # Sort by complexity descending — highest risk first
    for f in sorted(funcs, key=lambda x: x["complexity"], reverse=True):
        short_file = os.path.basename(f["file"])
        print(f"  {f['function']:<25} {f['line']:>5} "
              f"{f['loc']:>5} {f['complexity']:>6} "
              f"{f['risk']:<8} {short_file}")

    high   = [f for f in funcs if f["risk"] == "High"]
    medium = [f for f in funcs if f["risk"] == "Medium"]
    low    = [f for f in funcs if f["risk"] == "Low"]

    print(f"\n  High risk   : {len(high)} function(s) — port these carefully")
    print(f"  Medium risk : {len(medium)} function(s) — review thoroughly")
    print(f"  Low risk    : {len(low)} function(s) — straightforward")
    print(f"{'='*60}\n")

def export_csv(issues, funcs, output_file="porting_report.csv"):
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Section 1 — Porting issues
        writer.writerow(["PORTING ISSUES"])
        writer.writerow(["File", "Type", "Line",
                         "Pattern", "Suggestion", "Code"])
        for i in issues:
            writer.writerow([
                i["file"], i["filetype"], i["line"],
                i["pattern"], i["suggestion"], i["code"]
            ])

        writer.writerow([])

        # Section 2 — Function complexity
        writer.writerow(["FUNCTION COMPLEXITY"])
        writer.writerow(["File", "Function", "Line",
                         "LOC", "Complexity", "Risk"])
        for f in sorted(funcs,
                        key=lambda x: x["complexity"],
                        reverse=True):
            writer.writerow([
                f["file"], f["function"], f["line"],
                f["loc"], f["complexity"], f["risk"]
            ])

    print(f"CSV report saved to: {output_file}")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."

    if not os.path.exists(target):
        print(f"Error: path '{target}' does not exist")
        sys.exit(1)

    print(f"Scanning: {target}")
    issues, funcs = scan_directory(target)

    print_porting_report(issues)
    print_complexity_report(funcs)
    export_csv(issues, funcs)
