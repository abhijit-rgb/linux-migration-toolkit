#!/usr/bin/env python3
"""
scan_porting_issues.py
Scans C and Fortran code for Solaris-specific patterns
that need to be ported to Linux.
Author: Abhijit
"""

import os
import sys

# Solaris-specific C patterns and their Linux fixes
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

# Solaris-specific Fortran patterns and their Linux fixes
FORTRAN_PATTERNS = {
    "f90":               "Compiler changed — use gfortran instead of f90/f95",
    "f95":               "Compiler changed — use gfortran instead of f90/f95",
    "REAL*4":            "Use REAL or REAL(KIND=4) for portability with gfortran",
    "REAL*8":            "Use DOUBLE PRECISION or REAL(KIND=8) for portability",
    "INTEGER*4":         "Use INTEGER or INTEGER(KIND=4) for portability",
    "INTEGER*8":         "Use INTEGER(KIND=8) for portability",
    "COMPLEX*8":         "Use COMPLEX or COMPLEX(KIND=4) for portability",
    "COMPLEX*16":        "Use COMPLEX(KIND=8) for portability",
    "%VAL(":             "Sun Studio extension — use ISO_C_BINDING instead",
    "%REF(":             "Sun Studio extension — use ISO_C_BINDING instead",
    "%LOC(":             "Sun Studio extension — use LOC() or C_LOC() instead",
    "INCLUDE 'mpif.h'":  "Use USE mpi module instead for modern gfortran",
    "IMPLICIT REAL":     "Remove — gfortran is stricter, use IMPLICIT NONE",
    "PAUSE":             "PAUSE statement deprecated in gfortran — use READ(*,*)",
    "ENCODE(":           "Sun extension — use WRITE to internal file instead",
    "DECODE(":           "Sun extension — use READ from internal file instead",
    "NAMELIST":          "Check syntax — gfortran handles differently than Sun",
}

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
    all_issues = []
    extensions = (".c", ".h", ".f", ".f90", ".f95", ".for", ".F", ".F90")
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(extensions):
                filepath = os.path.join(root, filename)
                all_issues.extend(scan_file(filepath))
    return all_issues

def print_report(issues):
    if not issues:
        print("No Solaris-specific patterns found. Code looks portable!")
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
    print(f"Total issues : {len(issues)} across "
          f"{len(set(i['file'] for i in issues))} file(s)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.exists(target):
        print(f"Error: path '{target}' does not exist")
        sys.exit(1)
    print(f"Scanning: {target}")
    issues = scan_directory(target)
    print_report(issues)
