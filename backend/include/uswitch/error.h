/* error.h - debug and error messages */
/* AUTHOR: Alexis Malozemoff */

#ifndef __ERROR_H__
#define __ERROR_H__

extern int debug_flag;

/* prints a message if matches debug level */
#define DPRINTF(LVL, ...)					\
	do {							\
		if (LVL <= debug_flag) {			\
			fprintf(stderr, "%s: ", __func__);	\
			fprintf(stderr, __VA_ARGS__);		\
		}						\
	} while (0)

/* error messages */
#define ERR_ACCEPT		"call to accept() failed"
#define ERR_CREAT		"creat() failed"
#define ERR_FCNTL		"failed changing file descriptor"
#define ERR_FREOPEN		"freopen() failed"
#define ERR_GETSOCKNAME		"getsockname() failed"
#define ERR_MALLOC		"failed to allocate space"
#define ERR_READ		"read() failed"
#define ERR_RECVFROM		"recvfrom() failed"
#define ERR_SIGACTION		"sigaction() failed"
#define ERR_SOCKET		"socket() failed"
#define ERR_UNLINK		"error unlinking file"
#define ERR_WRITE		"write() failed"

#endif /* __ERROR_H__ */
