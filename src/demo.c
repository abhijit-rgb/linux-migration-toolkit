#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/utsname.h>

void get_os_info() {
    struct utsname info;
    if (uname(&info) < 0) {
        perror("uname failed");
        exit(1);
    }
    printf("OS Name    : %s\n", info.sysname);
    printf("Node Name  : %s\n", info.nodename);
    printf("Release    : %s\n", info.release);
    printf("Version    : %s\n", info.version);
    printf("Machine    : %s\n", info.machine);
}

void check_memory() {
    long pages     = sysconf(_SC_PHYS_PAGES);
    long page_size = sysconf(_SC_PAGE_SIZE);
    if (pages < 0 || page_size < 0) {
        perror("sysconf failed");
        exit(1);
    }
    long total_mb = (pages * page_size) / (1024 * 1024);
    printf("Total RAM  : %ld MB\n", total_mb);
}

int main() {
    printf("=== System Information ===\n");
    get_os_info();
    check_memory();
    printf("==========================\n");
    return 0;
}
