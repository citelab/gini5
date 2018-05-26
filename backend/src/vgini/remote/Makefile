# Makefile to build monte_pi_sprng program
# --- macros
CC=cc
CFLAGS=-O2 -g -DHAVE_PTHREAD_RWLOCK=1 -DHAVE_GETOPT_LONG
SRC=main.c tapdev.c packet.c cli.c utils.c
OBJECTS=$(SRC:.c=.o)
LIBS=-lpthread -lslack -lreadline

# --- targets
all:    vtap
vtap:   $(OBJECTS) 
	$(CC)  -o vtap $(OBJECTS) $(LIBS)

%.o: %.h %.c
	$(CC) $(CFLAGS) -c -o $*.o $*.c 


# --- remove binary and executable files
clean:
	rm -f vtap $(OBJECTS)

