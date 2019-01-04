#include <unistd.h>
#include <sys/times.h>

int main() {
    struct timeval tv;
    struct tms clk;
    for (;;) {
        tv.tv_sec = 0;
        tv.tv_usec = 1;
        select(0, NULL, NULL, NULL, &tv);
        times(&clk);
    }
    return 0;
}
