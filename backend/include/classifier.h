/*
 * classifier.h (include file for the packet classifier)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: June 27, 2008
 */

#ifndef __CLASSIFIER_H__
#define __CLASSIFIER_H__

#include <slack/list.h>
#include "grouter.h"
#include "classspec.h"
#include "message.h"

typedef struct _classdef_t
{
	ip_spec_t *srcspec;
	ip_spec_t *dstspec;
	port_range_t *srcports;
	port_range_t *dstports;
	int prot;
	int tos;
	char cname[MAX_NAME_LEN];
	int cdefid;
} classdef_t;


typedef struct _classlist_t
{
	List *deftab;
	int defcnt;
} classlist_t;



// Function prototypes

classlist_t *createClassifier();
int addClassDef(classlist_t *clas, char *cname);
int delClassDef(classlist_t *clas, char *cname);
int classDefExists(classlist_t *clas, char *cname);
classdef_t *getClassDef(classlist_t *clas, char *cname);
void printClassDef(classdef_t *cr);
void printClassifier(classlist_t *cl);

int insertIPSpec(classlist_t *clas, char *cname, int srcside, ip_spec_t *ipspec);
int insertPortRangeSpec(classlist_t *clas, char *cnarm, int srcside, port_range_t *prspec);
int insertProtSpec(classlist_t *clas, char *cname, int prot);
int insertTOSSpec(classlist_t *clas, char *cname, int tos);

int isRuleMatching(classdef_t *cdef, gpacket_t *in_pkt);

#endif
