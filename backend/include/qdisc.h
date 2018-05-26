/*
 * qdisc.h
 *
 *  Created on: 25-Oct-2009
 *  Author: Muthucumaru Maheswaran
 */

#ifndef QDISC_H_
#define QDISC_H_

#include "grouter.h"


typedef struct _qentrytype_t
{
	char name[MAX_NAME_LEN];
	double pmaxval;
	double minval, maxval;

} qentrytype_t;


typedef struct _qdisctable_t
{
	qentrytype_t qentry[MAX_QDISC_TYPES];
	int qdiscnums;

} qdisctable_t;


qdisctable_t *initQDiscTable();
void printQdiscs(qdisctable_t *qdiscs);
int lookupQDisc(qdisctable_t *qdiscs, char *name);
qentrytype_t *getqdiscEntry(qdisctable_t *qdiscs, char *name);
void addSimplePolicy(qdisctable_t *qdiscs, char *name);
void addRED(qdisctable_t *qdiscs, double minl, double maxl, double pmax);

#endif /* QDISC_H_ */
