/*
 * device.h (include file for the device template)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: December 13, 2004
 * VERSION: 1.0
 * 
 * The device template provides all the key functions needed
 * to package the key functionalities of the router into minimally
 * interacting components.
 *
 */

#ifndef __DEVICE_H__
#define __DEVICE_H__

#include "grouter.h"
#include <pthread.h>
#include "layer.h"


// a device has name, handlers for I/O
typedef struct _device_t 
{
	char devname[MAX_DNAME_LEN];				// device name
	char devdesc[MAX_NAME_LEN];					// device description
	void * (*fromdev)(void *arg);
	void * (*todev)(void *arg);
	int dbglevel;
} device_t;


// device information
typedef struct _devicedirectory_t
{
	char devname[MAX_DNAME_LEN];				// device name
	char devdesc[MAX_NAME_LEN];					// device description
	void * (*fromdev)(void *arg);
	void * (*todev)(void *arg);

} devicedirectory_t;


typedef struct _devicearray_t
{
	int count;
	device_t *elem;

} devicearray_t;


#endif
