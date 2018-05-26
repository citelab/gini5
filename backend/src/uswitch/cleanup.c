/* cleanup.c - cleanup functions */

#include <stdio.h>
#include <stdlib.h>

#include "cleanup.h"
#include "error.h"

static struct cleanup *cleanup_tbl;	/* cleanup functions go here */

/* cleans up any open stuff and exits
 * if quitting due to an error, use the CLEANUP_DO(msg) macro
 */
void
cleanup_do(int status)
{
	struct cleanup *c;
	struct cleanup *next;

	/* cleanup and exit */
	for (c = cleanup_tbl; c != NULL; c = next) {
		(c->prg)();
		next = c->next;
		free(c);
	}

	exit(status);
}

/* add function to the cleanup list */
void
cleanup_add(void (*prg)(void))
{
	struct cleanup *c;
	if ((c = malloc(sizeof(struct cleanup))) <0)
		CLEANUP_DO(ERR_MALLOC);
	c->prg = prg;
	c->next = cleanup_tbl;
	cleanup_tbl = c;
}

void
cleanup_init(void)
{
	cleanup_tbl = NULL;
}
