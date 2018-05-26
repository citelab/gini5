/*
 * tapio.h (header file the low level Tap driver)
 * AUTHOR: Muthucumaru Maheswaran
 *
 * VERSION:
 */



/*
 * function prototypes
 */

vpl_data_t *tap_connect(char *sock_name);
int tap_recvfrom(vpl_data_t *vpl, void *buf, int len);
int tap_sendto(vpl_data_t *vpl, void *buf, int len);

