/*
 * filter.h (include file for the packet filter)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: October 1, 2008
 *
 * These routines implement the packet filter.
 */

#ifndef __FILTER_H__
#define __FILTER_H__

#include <slack/list.h>
#include "grouter.h"
#include "classspec.h"
#include "message.h"
#include "classifier.h"

#define MAX_FILTER_RULES                   64

typedef struct _filterrule_t
{
	int type;                           // deny or allow
	char cname[MAX_NAME_LEN];
	int passes;
	int failures;
} filterrule_t;


typedef struct _filtertab_t
{
	filterrule_t *ruletab[MAX_FILTER_RULES];
	int rulecnt;
	int filteron;
	classlist_t *clist;
} filtertab_t;



// Function prototypes

filtertab_t *createFilter(classlist_t *clist, int state);

void printFilterStats(filtertab_t *ft);
void printFilter(filtertab_t *ft);

void moveRule(filtertab_t *ft, int rulenum, char *dir);

void delFilterRule(filtertab_t *ft, int rulenum);
int addFilterRule(filtertab_t *ft, int type, char *cname);

int filteredPacket(filtertab_t *ft, gpacket_t *in_pkt);

void flushFilter(filtertab_t *ft);
#endif
