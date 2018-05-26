#ifndef __CLEANUP_H__
#define __CLEANUP_H__

struct cleanup {
  void (*prg)(void);
  struct cleanup *next;
};

#define CLEANUP_DO(...)					\
	do {						\
		fprintf(stderr, "%s: ", __func__);	\
		fprintf(stderr, __VA_ARGS__);		\
		perror(" ");				\
		cleanup_do(EXIT_FAILURE);		\
	} while (0)

/* prototypes */
void cleanup_do(int);
void cleanup_add(void (*)(void));
void cleanup_init(void);

#endif /* __CLEANUP_H__ */
