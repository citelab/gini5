#ifndef TAPDEV_H
#define TAPDEV_H

int tun_alloc(char *dev);
int tap_creat(char *dev, int flags);
void *tap_rolling(void *val);

#endif	// TAPDEV_H
