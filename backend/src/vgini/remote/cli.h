#ifndef __CLI_H__
#define __CLI_H__

#include <string.h>
#include <stdio.h>
#include <slack/std.h>
#include <slack/map.h>


#define PROGRAM                       10
#define JOIN                          11
#define COMMENT                       12
#define COMMENT_CHAR                  '#'
#define CONTINUE_CHAR                 '\\'
#define CARRIAGE_RETURN               '\r'
#define LINE_FEED                     '\n'

#define MAX_BUF_LEN                   4096
#define MAX_LINE_LEN                  1024
#define MAX_KEY_LEN                   64

#define SHELP_SETIP                   "AA"
#define SHELP_SETNM                   "AA"
#define SHELP_SHOWIP                  "AA"
#define SHELP_SHOWNM                  "AA"
#define SHELP_QUIT                    "AA"

#define USAGE_SETIP                   "AA"
#define USAGE_SETNM                   "AA"
#define USAGE_SHOWIP                  "AA"
#define USAGE_SHOWNM                  "AA"
#define USAGE_QUIT                    "AA"

#define LHELP_SETIP                   "AA"
#define LHELP_SETNM                   "AA"
#define LHELP_SHOWIP                  "AA"
#define LHELP_SHOWNM                  "AA"
#define LHELP_QUIT                    "AA"

#define MAX_TMPBUF_LEN                256
#define HELP_PREAMPLE                 "These shell commands are defined internally. Type `help' to see \n\
this list. Type `help name' to find out more about the function `name'.\n\
Because the GINI shell uses the underlying Linux shell to run \n\
commands not recognized by it, most Linux commands can be accessed \n\
from this shell. If GINI shell reimplements a Linux command \n\
(e.g., ifconfig), then only GINI version can be accessed from the\n\
GINI shell. To access the Linux version, find the actual location\n\
of the Linux command (i.e., whereis ifconfig) and give the \n\
absolute path (e.g., /sbin/ifconfig). \n"

typedef struct _cli_entry_t
{
	char keystr[MAX_KEY_LEN];
	char long_helpstr[MAX_BUF_LEN];
	char short_helpstr[MAX_BUF_LEN];
	char usagestr[MAX_BUF_LEN];
	void (*handler)();
} cli_entry_t;


// function prototypes...
int CLIInit(pthread_t *val);
void dummyFunction();
void parseACLICmd(char *str);
void CLIProcessCmds(FILE *fp, int online);
void CLIPrintHelpPreamble();
void *CLIProcessCmdsInteractive(void *arg);
void registerCLI(char *key, void (*handler)(),
		 char *shelp, char *usage, char *lhelp);
void CLIDestroy();


void quitCmd();
void setipCmd();
void setnmCmd();
void showipCmd();
void shownmCmd();

char buf_interface[256];
char buf_ipfo[256];
char buf_parp[256];
char buf_sysc[256];
char gini_ip[20];
#endif
