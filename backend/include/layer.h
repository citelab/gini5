/*
 * layer.h (include file for the Layer library)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: December 11, 2004
 *
 */

#ifndef __LAYER_H__
#define __LAYER_H__


#include <slack/std.h>
#include <slack/map.h>

#include "grouter.h"
#include "message.h"
#include "msgqueue.h"


// define message handling modes for the layer
#define  NORMAL                          0
#define  SNOOP                           1
#define  DIVERT                          2

#define MAX_LAYERS                       10




typedef struct _typemapentry_t 
{
	uint dummy;
	uint mode;
	uint  count;
} typemapentry_t;


typedef struct _modulemapentry_t
{
	int count;
	uint types[MAX_TYPES_PER_MODULE];
	uint modes[MAX_TYPES_PER_MODULE];
	int snoopid;
} modulemapentry_t;


// main structure for the layer. this structure has several
// field defining bookkeeping variables and other control
// variables for layers.
typedef struct _layer_t
{
	char name[MAX_NAME_LEN];
	char rname[MAX_NAME_LEN];
	int level;
	uint layerid;
	Map *modulemap;
	messagequeue_t *msgqueue;
	Map *typemap;

} layer_t;


// Function prototypes
_begin_decls
layer_t *createLayer(char *rpath, char *rname, char *name, int level);
int destroyLayer(layer_t *layer, int force);
int registerModuleHook(int layerid, int moduleid, uint type, uint mode);
int deregisterModuleHook(int layerid, int moduleid, uint type);
int writeLayer(layer_t *layer, int type, void *data, int size);
int readLayer(layer_t *layer, int moduleid, int type, void *data);


modulemapentry_t *createModuleMapEntry(uint type, uint mode, int snoopid);
void printModuleMapEntry(modulemapentry_t *m);
uint getModeFromModuleEntry(modulemapentry_t *m, uint type);
modulemapentry_t *addModule2MapEntry(modulemapentry_t *mentry, uint type, uint mode, int snoopid);

int sendMessage(layer_t *layer, uint type, void *data, int size);
int recvMessage(layer_t *layer, uint type, void *msgbuf);
_end_decls
#endif
