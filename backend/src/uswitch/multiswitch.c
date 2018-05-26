/*
 * Julien Villemure, julien@cs.mcgill.ca
 * Student ID: 260151677
 *
 * COMP 535 Final Project, Fall 2009
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/time.h>
#include <arpa/inet.h>

#include "multiswitch.h"
#include "uswitch.h"
#include "cleanup.h"


/*
 * Representation of a switch port, in a linked list fashion.
 */

struct _switch_t;
typedef struct _switch_t switch_t;

struct _switch_t {

    uint32_t id;                // locally unique identifier
    struct sockaddr_un sun;        // socket address used to communicate to the remote switch
    uint8_t blocked;                // boolean: if true, no data is forwarded through the port
    bpdu_t bpdu;                // used for STP
    switch_t *next;                // next port

};


//
// Global variables
//

char ms_sock_path[1024];        // path to local socket file
int ms_sock;                        // local socket
struct sockaddr_un local_sun;        // local sockaddr_un

struct packet local_pkt;  // used in STP for sending BPDUs
bpdu_t *local_bpdu = (bpdu_t *)(local_pkt.data);
int pkt_len = sizeof(local_pkt.header) + sizeof(bpdu_t);

switch_t *ms_list = NULL;        // switch port list
switch_t *root_switch = NULL;        // next hop towards the root


//
// Local Functions
//

/*
 * Insert a switch port in ms_list
 */
void ms_list_insert (switch_t *s) {

    s->next = ms_list;
    ms_list = s;

}

/*
 * Clear the switch port list, destroying all ports
 */
void ms_list_clear () {

    switch_t *s = ms_list;
    switch_t *t;

    while (s != NULL) {
        t = s;
        s = s->next;
        free(t);
    }

}

/*
 * Return the switch port in the list that matches the given sockaddr_un.
 * If no port is found, NULL is returned.
 */
switch_t *ms_list_find (struct sockaddr_un *sun) {

    switch_t *s;

    for (s = ms_list; s != NULL; s = s->next) {
        if (strcmp(s->sun.sun_path, sun->sun_path) == 0)
            break;
    }

    return s;

}

/*
 * To be called as part of the cleanup routine in uswitch.c.
 */
void ms_cleanup () {

    ms_list_clear();
    close(ms_sock);
    unlink(ms_sock_path);

}

/*
 * Send the BPDU packet to all switch ports.
 */
void ms_broadcast_bpdu () {

    switch_t *s;

    for (s = ms_list; s != NULL; s = s->next) {
        local_bpdu->port = s->id;
        sendto(ms_sock, &local_pkt, pkt_len, 0, (struct sockaddr *) &(s->sun), sizeof(s->sun));
    }

}

/*
 * Check whether the given BPDU contains better information that what we currently
 * have. Return true/false.
 */
int ms_bpdu_supersedes (bpdu_t *bpdu) {

    int c = memcmp(bpdu->root.id, local_bpdu->root.id, 8);

    if (c < 0)
        return 1;        // the BPDU has a better root

    if (c == 0) {
        if (bpdu->cost < local_bpdu->cost) {
            return 1;        // the BPDU has the same root but a better cost
        }
        if (bpdu->cost == local_bpdu->cost) {
            if (memcmp(bpdu->bridge.id, local_bpdu->gateway.id, 8) < 0) {
                // The BPDU has the same root and cost, but the sender has a higher
                // priority than our current gateway.
                return 1;
            }
        }
    }

    return 0;        // our current information is better than the BPDU's

}

/*
 * Handle a BPDU received from some sender port. The information we have regarding
 * STP computation will be updated accordingly.
 */
void ms_receive_bpdu (switch_t *sender, bpdu_t *bpdu) {

    switch_t *s;

    // Update the last received BPDU in the sender's state
    memcpy(&(sender->bpdu), bpdu, sizeof(bpdu_t));

    // (cost to root through sender) = (bpdu cost) + (cost of link between us and sender)
    // Right now we assume the cost of all links is 1. This could be modified to a link-
    // specific value passed to uswitch by a command-line parameter.
    (bpdu->cost)++;

    // If the BPDU contains better information
    if (ms_bpdu_supersedes(bpdu)) {

        // Update our root, cost, and gateway
        memcpy(local_bpdu->root.id, bpdu->root.id, 8);
        local_bpdu->cost = bpdu->cost;
        memcpy(local_bpdu->gateway.id, bpdu->bridge.id, 8);
        root_switch = sender;

        // Send this updated information to everyone
        ms_broadcast_bpdu();

    }

    // Update the open/blocked state of all switch ports
    for (s = ms_list; s != NULL; s = s->next) {
        if ((s != root_switch) && (memcmp(s->bpdu.gateway.id, local_bpdu->bridge.id, 8)))
            s->blocked = 1;
        else
            s->blocked = 0;
    }

}

/*
 * Print debugging information on the local switch and all switch ports to a file (debug.txt).
 */
#define ID_ARG                "%2.2X:%2.2X:%2.2X:%2.2X:%2.2X:%2.2X:%2.2X:%2.2X"
#define ID_VAL(X)        (X)[0],(X)[1],(X)[2],(X)[3],(X)[4],(X)[5],(X)[6],(X)[7]
void ms_debug_print () {

    FILE *f;
    switch_t *s;

    f = fopen("debug.txt", "w");

    // Ourselves
    fprintf(f, "=== Local Switch ===\n");
    fprintf(f, "%s\n", local_sun.sun_path);
    fprintf(f, "Bridge ID:\t"ID_ARG"\n", ID_VAL(local_bpdu->bridge.id));
    fprintf(f, "Root ID:\t"ID_ARG"\n", ID_VAL(local_bpdu->root.id));
    fprintf(f, "Gateway ID:\t"ID_ARG"\n", ID_VAL(local_bpdu->gateway.id));
    fprintf(f, "Root?\t\t%s\n", (memcmp(local_bpdu->bridge.id, local_bpdu->root.id, 8)) ? "No":"YES");
    fprintf(f, "Cost:\t\t%d\n", local_bpdu->cost);
    fprintf(f, "\n\n");

    // All switch ports
    for (s = ms_list; s != NULL; s = s->next) {
        fprintf(f, "=== Switch Port ===\n");
        fprintf(f, "%s\n", s->sun.sun_path);
        fprintf(f, "Bridge ID:\t"ID_ARG"\n", ID_VAL(s->bpdu.bridge.id));
        fprintf(f, "Root ID:\t"ID_ARG"\n", ID_VAL(s->bpdu.root.id));
        fprintf(f, "Gateway ID:\t"ID_ARG"\n", ID_VAL(s->bpdu.gateway.id));
        fprintf(f, "Root?\t\t%s\n", (s == root_switch) ? "YES":"No");
        fprintf(f, "Cost:\t\t%d\n", s->bpdu.cost);
        fprintf(f, "State:\t\t%s\n", (s->blocked) ? "BLOCKED" : "Open");
        fprintf(f, "\n\n");
    }

    fclose(f);

}


//
// Publicly declared functions
//

/*
 * To be called before any other multiswitch function is called.
 * Initialize sockets and necessary data structures.
 */
int ms_init (uint16_t priority, uint8_t *mac) {

    int len;
    FILE *f;
    int foo = 1;

    getcwd(ms_sock_path, 1024);
    /* strcpy(ms_sock_path,getenv("GINI_HOME")); */
    strcat(ms_sock_path, "/multiswitch");

    // Delete the file if it already exists
    unlink(ms_sock_path);

    // Create the socket
    if ((ms_sock = socket(AF_UNIX, SOCK_DGRAM, 0)) == -1) {
        return -1;
    }

    // Bind to SOCKET_FILE
    memset(&local_sun, 0, sizeof(struct sockaddr_un));
    local_sun.sun_family = AF_UNIX;
    strcpy(local_sun.sun_path, ms_sock_path);

    if (bind(ms_sock, (struct sockaddr *) &local_sun, sizeof(local_sun)) == -1) {
        close(ms_sock);
        return -1;
    }

    cleanup_add(ms_cleanup);

    // Set constant fields in the configuration BPDU
    memset(local_bpdu, 0, 5);  // first 5 bytes are all zero

    /*
    // Local bridge ID, random for now
    f = fopen("/dev/urandom", "r");
    fread(local_bpdu->bridge.id, 1, 8, f);
    fclose(f);
    */

    // Local bridge ID
    memcpy(&(local_bpdu->bridge.priority), &priority, 2);
    memcpy(local_bpdu->bridge.mac, mac, 6);

    // The root ID is the local ID since initially we believe we're the root
    memcpy(local_bpdu->root.id, local_bpdu->bridge.id, 8);
    local_bpdu->cost = 0;

    // The gateway to the root is ourselves
    memcpy(local_bpdu->gateway.id, local_bpdu->bridge.id, 8);

    // Initialize the Ethernet packet
    SET_BRIDGE_GROUP_ADDR(local_pkt.header.dst);
    memcpy(local_pkt.header.src, local_bpdu->bridge.mac, 6);
    memset(local_pkt.header.prot, 0, 2);  // the value for STP doesn't seem to be specific anywhere...

    return 0;

}

/*
 * Parse the switch target file generated by GINI. Each line in the file should be
 * a complete path to an adjacent switch's socket. This function builds the list
 * of switch ports. If the function is never called, we assume that there are no
 * adjacent switches.
 */
void ms_parse_file (char *path) {

    FILE *f;
    int len;
    char buf[1024];
    switch_t *s;
    int id = 1;

    if ((f = fopen(path, "r")) == NULL)
        return;

    for (;;) {

        if (fgets(buf, 1024, f) == NULL)
            break;

        len = strlen(buf);
        buf[len-1] = '\0';  // remove trailing newline

        s = malloc(sizeof(switch_t));
        s->id = id++;
        s->sun.sun_family = AF_UNIX;
        strcpy(s->sun.sun_path, buf);
        s->blocked = 0;
        s->bpdu.cost = 0;
        memcpy(s->bpdu.root.id, local_bpdu->bridge.id, 8);        // initially we think we're the root
        memcpy(s->bpdu.gateway.id, local_bpdu->bridge.id, 8);        // initially we think we're the root

        ms_list_insert(s);

    }

    fclose(f);

}

/*
 * Broadcast a given packet to all OPEN switch ports. The sender's sockaddr
 * is provided so that we may avoid sending the packet back over the incoming link.
 */
void ms_broadcast (struct packet *local_pkt, int len, struct sockaddr *sa) {

    switch_t *s;
    struct sockaddr_un *sun = (struct sockaddr_un *) sa;

    for (s = ms_list; s != NULL; s = s->next) {

        if (!strcmp(sun->sun_path, s->sun.sun_path))
            continue;

        if (s->blocked)
            continue;

        sendto(ms_sock, local_pkt, len, 0, (struct sockaddr *) &(s->sun), sizeof(s->sun));

    }

}

/*
 * Perform STP in cooperation with other switches in the topology in order to
 * build a minimum spanning tree covering the topology. Locally, the result will
 * be to decide the open & blocked switch ports.
 *
 * This function WILL BLOCK until the topology has been computed by all switches!
 * When calling this function, the switch will NOT be processing any non-STP packets!
 *
 * The algorithm is inspired by IEEE 802.1D-1998 but is significantly different.
 * Because of various assumptions made by GINI, our algorithm is much simpler.
 * In fact, the full protocol as specified by the IEEE document will NOT work!
 * See the README.txt included with my project submission for more details.
 */
void ms_stp() {

    int n;
    fd_set set;
    struct timeval tv;
    struct packet pkt;
    struct sockaddr_un sun;
    switch_t *s;
    int sunlen = sizeof(struct sockaddr_un);
    bpdu_t *bpdu = (bpdu_t *) pkt.data;

    // Time to listen for incoming configuration BPDUs
    // This is the HELLO timer and the LISTEN timer from the IEEE document.
    // We use the same value for both timers, for simplicity.
    tv.tv_sec = 2;
    tv.tv_usec = 0;

    // Give some time for all switches to come online
    usleep(2000000);  // 2 seconds

    for (;;) {

        // If we believe we're the root, send a configuration BPDU
        if (memcmp(local_bpdu->root.id, local_bpdu->bridge.id, 8) == 0) {
            ms_broadcast_bpdu();
        }

        // Listen for a while
        FD_ZERO(&set);
        FD_SET(ms_sock, &set);
        n = select(ms_sock+1, &set, NULL, NULL, &tv);

        // If there's something to read, process it
        if (FD_ISSET(ms_sock, &set)) {
            FD_CLR(ms_sock, &set);
            while (recvfrom(ms_sock, &pkt, sizeof(struct packet), MSG_DONTWAIT, (struct sockaddr *) &sun, &sunlen) >= 0) {

                // Check the destination address
                if (! IS_BRIDGE_GROUP_ADDR(pkt.header.dst))
                    continue;

                // Verify the configuration BPDU protocol, version, and type fields
                if ((bpdu->protocol != 0) || (bpdu->version != 0) || (bpdu->type != 0))
                    continue;

                // Find the switch that sent this packet
                if ((s = ms_list_find(&sun)) == NULL)
                    continue;

                // Process the configuration BPDU
                ms_receive_bpdu(s, bpdu);

            }
        }

        // There has been nothing to read for a while; assume all switches have reached a consensus.
        else
            break;

    }

    // See $GINI_HOME/data/Switch_X/debug.txt for very useful information
    ms_debug_print();

}

