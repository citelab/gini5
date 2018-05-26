/*
 * info.h (header file for information display subsystem)
 * These routines control what information is sent to the external performance
 * visualizer and how the information is formatted.
 *
 */


#ifndef __INFO_H__
#define __INFO_H__


#include "grouter.h"
#include <slack/list.h>

typedef struct _info_config_t
{
	int id;                        // FIFO id
	char path[MAX_NAME_LEN];       // FIFO path
	pthread_t threadid;            // thread for the info handler

	int rawtimemode;               // if TRUE output time as sec otherwise human friendly
	int updateinterval;            // seconds between subsequent info. updates

	List *qtargets;

} info_config_t;


typedef struct _queue_target_t
{
	int active;
	char targetname[MAX_NAME_LEN];
	simplequeue_t *queue;
} queue_target_t;



void infoHandler();
void addTarget(char *name, simplequeue_t *tgrt);
void activeTarget(char *name);
void deactiveTarget(char *name);
void printTimeMode();
void setTimeMode(int rawmode);
int getTimeMode();
void infoList();
void infoInit(char *rpath, char *rname);

#endif




