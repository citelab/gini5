# Makefile to build monte_pi_sprng program
# --- macros
CC=cc
CFLAGS=-O2 -g -DHAVE_PTHREAD_RWLOCK=1 -DHAVE_GETOPT_LONG
SRC=proxy.c packet.c utils.c vpl.c
OBJECTS=$(SRC:.c=.o)
LIBS=-lpthread -lslack -lreadline

# --- targets
all:    vtproxy
vtproxy:   $(OBJECTS) 
	$(CC)  -o vtproxy $(OBJECTS) $(LIBS)

%.o: %.h %.c
	$(CC) $(CFLAGS) -c -o $*.o $*.c 


# --- remove binary and executable files
clean:
	rm -f vtproxy $(OBJECTS)

