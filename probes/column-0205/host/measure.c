#include <valgrind/callgrind.h>
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
int step_cycles_open(void) {
    struct perf_event_attr a;
    memset(&a,0,sizeof(a));
    a.type=PERF_TYPE_HARDWARE;a.size=sizeof(a);a.config=PERF_COUNT_HW_CPU_CYCLES;
    a.disabled=1;a.exclude_kernel=1;a.exclude_hv=1;
    a.read_format=PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING;
    return syscall(__NR_perf_event_open,&a,0,-1,-1,0);
}
void step_begin(int fd) {
    CALLGRIND_START_INSTRUMENTATION;
    CALLGRIND_ZERO_STATS;
    if(fd>=0){ioctl(fd,PERF_EVENT_IOC_RESET,0);ioctl(fd,PERF_EVENT_IOC_ENABLE,0);}
}
void step_end(int fd, uint64_t *out) {
    if(fd>=0){ioctl(fd,PERF_EVENT_IOC_DISABLE,0);if(read(fd,out,24)!=24)out[0]=out[1]=out[2]=0;}
    CALLGRIND_DUMP_STATS;
    CALLGRIND_STOP_INSTRUMENTATION;
}
void step_close(int fd) {if(fd>=0)close(fd);}
