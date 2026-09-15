// Linux-only setup and spawning-thread lifetime probe, not an rnx patch.
#include <sys/prctl.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *mode;
static void *spawn(void *unused) {
 (void)unused;
 pid_t parent=getpid();
 pid_t child=fork();
 if(child<0) abort();
 if(child==0) {
  if((!strcmp(mode,"race") || !strcmp(mode,"thread-race"))) usleep(200000);
  if(prctl(PR_SET_PDEATHSIG,SIGKILL)<0) _exit(91);
  if(getppid()!=parent) _exit(92);
  printf("{\"child\":%d,\"armed\":true}\n",getpid());fflush(stdout);
  for(;;) pause();
 }
 printf("{\"spawned\":%d}\n",child);fflush(stdout);
 if(!strcmp(mode,"race")) _exit(0);
 if(!strcmp(mode,"thread-race")) {usleep(50000);return NULL;}
 if(!strcmp(mode,"thread")) {usleep(300000);return NULL;}
 for(;;) pause();
}
int main(int argc,char **argv) {
 mode=argc>1?argv[1]:"normal";
 if(!strcmp(mode,"thread") || !strcmp(mode,"thread-race")) {pthread_t t;if(pthread_create(&t,NULL,spawn,NULL))abort();for(;;)pause();}
 spawn(NULL);
}
