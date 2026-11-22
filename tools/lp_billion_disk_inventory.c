/* Exact apparent-byte inventory: no symlinks/directories, hardlinks counted once.
 * Replaces Python per-entry allocation overhead, not the storage ceiling/cadence. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
struct key { uint64_t dev, ino; bool used; };
static struct key *table;
static size_t capacity, count;
static uint64_t bytes;
static void die(const char *what) { perror(what); exit(2); }
static uint64_t mix(uint64_t x) {
    x ^= x >> 30; x *= UINT64_C(0xbf58476d1ce4e5b9);
    x ^= x >> 27; x *= UINT64_C(0x94d049bb133111eb);
    return x ^ (x >> 31);
}
static size_t slot(uint64_t dev, uint64_t ino) {
    size_t i = (size_t)mix(ino ^ mix(dev)) & (capacity-1);
    while (table[i].used && (table[i].dev != dev || table[i].ino != ino))
        i = (i+1) & (capacity-1);
    return i;
}
static void grow(void) {
    struct key *old = table; size_t n = capacity;
    if (capacity > SIZE_MAX/2/sizeof(*table)) { errno=EOVERFLOW; die("inventory table"); }
    capacity = capacity ? capacity*2 : 16384;
    table = calloc(capacity,sizeof(*table)); if (!table) die("inventory allocation");
    for (size_t j=0;j<n;++j) if (old[j].used) table[slot(old[j].dev,old[j].ino)]=old[j];
    free(old);
}
static void add(const struct stat *s) {
    if (!capacity || count >= capacity/2) grow();
    size_t i=slot((uint64_t)s->st_dev,(uint64_t)s->st_ino);
    if (table[i].used) return;
    if (s->st_size < 0 || UINT64_MAX-bytes < (uint64_t)s->st_size) {
        errno=EOVERFLOW; die("inventory size");
    }
    table[i]=(struct key){(uint64_t)s->st_dev,(uint64_t)s->st_ino,true};
    bytes+=(uint64_t)s->st_size; ++count;
}
static void walk(int fd) {
    DIR *dir=fdopendir(fd); if (!dir) { close(fd); die("inventory directory"); }
    for (;;) {
        errno=0; struct dirent *entry=readdir(dir);
        if (!entry) { if (errno) die("inventory readdir"); break; }
        if (!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..") || entry->d_type==DT_LNK) continue;
        struct stat s; bool directory=entry->d_type==DT_DIR;
        if (!directory) {
            if (fstatat(dirfd(dir),entry->d_name,&s,AT_SYMLINK_NOFOLLOW)) {
                if (errno==ENOENT) continue;
                die("inventory stat");
            }
            if (S_ISLNK(s.st_mode)) continue;
            directory=S_ISDIR(s.st_mode);
        }
        if (directory) {
            int child=openat(dirfd(dir),entry->d_name,O_RDONLY|O_CLOEXEC|O_DIRECTORY|O_NOFOLLOW);
            if (child<0) { if (errno==ENOENT) continue; die("inventory open directory"); }
            walk(child);
        } else add(&s);
    }
    if (closedir(dir)) die("inventory close directory");
}
int main(int argc,char **argv) {
    if (argc!=2) { fputs("usage: inventory ROOT\n",stderr); return 2; }
    int fd=open(argv[1],O_RDONLY|O_CLOEXEC|O_DIRECTORY|O_NOFOLLOW);
    if (fd<0) { if (errno!=ENOENT) die("inventory root"); }
    else walk(fd);
    printf("{\"bytes\":%" PRIu64 ",\"files\":%zu}\n",bytes,count);
    free(table);return 0;
}
