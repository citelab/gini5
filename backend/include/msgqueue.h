/*
 * msgqueue.h (include file for the Message Queue library)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: June 6, 2008
 *
 */

#ifndef __MSG_QUEUE_H__
#define __MSG_QUEUE_H__


#include <slack/std.h>
#include <slack/map.h>
#include <slack/list.h>

#include "grouter.h"


typedef struct _messagewrapper_t
{
	int size;
	void *data;
} messagewrapper_t;


// define the data types needed for the wait queue library
typedef struct _messageclass_t
{
	int waiting;
	pthread_cond_t condvar;
	pthread_mutex_t lock;
	List *msglist;
} messageclass_t;


typedef struct _messagequeue_t
{
	char name[MAX_NAME_LEN];
	Map *queue;
	pthread_cond_t qfull;
	pthread_mutex_t qlock;
	int maxsize, cursize;
	int blockonwrite;
	int blockonread;
} messagequeue_t;


// Function prototypes
_begin_decls
messagequeue_t *createMsgQueue(char *name, int maxsize, int blockonwrite, int blockonread);
int destroyMsgQueue(messagequeue_t *msgqueue);
void printMsgQueue(messagequeue_t *msgqueue, int vblevel);
int msgWrite(messagequeue_t *msgqueue, int type, void *data, int size);
int msgRead(messagequeue_t *msgqueue, int type, void *data, int *size);

_end_decls
#endif
