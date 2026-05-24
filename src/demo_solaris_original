#include <stdio.h>
#include <stdlib.h>
#include <sys/systeminfo.h>
#include <sys/lwp.h>
#include <thread.h>

/*
 * demo_solaris_original.c
 * Original Solaris 10 version - DO NOT USE ON LINUX
 * This file is kept for reference to show
 * what the code looked like before porting
 */

void get_os_info() {
    char buf[256];
    sysinfo(SI_SYSNAME, buf, sizeof(buf));
    printf("OS Name : %s\n", buf);
}

void create_worker_thread() {
    thread_t tid;
    thr_create(NULL, 0, NULL, NULL, 0, &tid);
    thr_join(tid, NULL, NULL);
}

void get_time() {
    hrtime_t t = gethrtime();
    printf("Time: %lld\n", t);
}

int main() {
    printf("=== Solaris System Info ===\n");
    get_os_info();
    create_worker_thread();
    get_time();
    printf("===========================\n");
    return 0;
}
