/*
 * qdisc.c
 *
 * Created on: 25-Oct-2009
 * Author: Muthucumaru Maheswaran
 *
 */

#include "qdisc.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

qdisctable_t *initQDiscTable()
{
	qdisctable_t *qdiscs;

	qdiscs = (qdisctable_t *) malloc(sizeof(qdisctable_t));
	qdiscs->qdiscnums = 0;

	return qdiscs;
}


void printQdiscs(qdisctable_t *qdiscs)
{
	int j;

	printf("Queueing disciplines defined at the gRouter \n");
	for (j = 0; j < qdiscs->qdiscnums; j++)
	{
		printf("[%d]\t%s", j, qdiscs->qentry[j].name);
		if (!strcmp(qdiscs->qentry[j].name, "red"))
			printf("\t-min %f -max %f -pmax %f",
					qdiscs->qentry[j].minval, qdiscs->qentry[j].maxval, qdiscs->qentry[j].pmaxval);
		else
			printf("\n");
	}
	printf("\n");
}


int lookupQDisc(qdisctable_t *qdiscs, char *name)
{
	int j;

	for (j = 0; j < qdiscs->qdiscnums; j++)
	{
		if (!strcmp(qdiscs->qentry[j].name, name))
			return j;
	}

	return -1;
}


qentrytype_t *getqdiscEntry(qdisctable_t *qdiscs, char *name)
{
	int indx;

	indx = lookupQDisc(qdiscs, name);
	if (indx < 0)
		return NULL;
	else
		return &(qdiscs->qentry[indx]);
}


void addSimplePolicy(qdisctable_t *qdiscs, char *name)
{

	if (lookupQDisc(qdiscs, name) < 0)
	{
		strcpy(qdiscs->qentry[qdiscs->qdiscnums].name, name);
		qdiscs->qdiscnums++;

	} else
		printf("ERROR!! Queueing discipline: %s already defined!\n", name);
}




void addRED(qdisctable_t *qdiscs, double minl, double maxl, double pmax)
{
	int indx;

	/*
	 * overwrite existing entry.. otherwise add a new entry.. only one entry
	 * per discipline.
	 */
	if ((indx = lookupQDisc(qdiscs, "red")) < 0)
	{
		indx = qdiscs->qdiscnums;
		qdiscs->qdiscnums++;
	}

	strcpy(qdiscs->qentry[indx].name, "red");
	qdiscs->qentry[indx].minval = minl;
	qdiscs->qentry[indx].maxval = maxl;
	qdiscs->qentry[indx].pmaxval = pmax;


}

