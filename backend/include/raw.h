/*
 * This is the low level driver for the wlan interface. 
 * It creates a wlan interface on the station and hooks up a 
 * raw socket to the interface.
 * 
 * Copyright (C) 2015 Ahmed Youssef (ahmed.youssef@mail.mcgill.ca)
 * Licensed under the GPL.
 */

#ifndef RAW_H
#define	RAW_H

#include "vpl.h"

void* toRawDev(void *arg);
void* fromRawDev(void *arg);
vpl_data_t* raw_connect(unsigned char* mac_addr, char *bridge);
int create_raw_interface(unsigned char *nw_addr);

#endif	/* RAW_H */

