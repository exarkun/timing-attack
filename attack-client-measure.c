#include <sys/socket.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static __inline__ unsigned long long rdtsc(void)
{
  unsigned hi, lo;
  __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
  return ( (unsigned long long)lo)|( ((unsigned long long)hi)<<32 );
}

int main(int argc, char **argv) {
  int fd = atoi(argv[1]);
  char *value = argv[2];
  int len = strlen(value);
  char buf[1024];
  unsigned long long before, after;

  send(fd, value, len, 0);
  before = rdtsc();
  recv(fd, buf, 1024, 0);
  after = rdtsc();

  printf("%lld\n%s\n", after - before, buf);
  return 0;
}
