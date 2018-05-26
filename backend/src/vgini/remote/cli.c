#include <stdio.h>
#include <strings.h>
#include <slack/err.h>
#include <slack/std.h>
#include <slack/prog.h>
#include <slack/err.h>
#include <stdlib.h>
#include <readline/readline.h>
#include <readline/history.h>
#include <ctype.h>

#include "packet.h"
#include "cli.h"


Map *cli_map;
Mapper *cli_mapper;
static char *cur_line = (char *)NULL;       // static variable for holding the line
extern FILE *rl_instream;

/*
 * This is the main routine of the CLI. Everything starts here.
 * The CLI registers and commands into a hash table and forks a thread to
 * handle the command line.
 */

int CLIInit(pthread_t *val)
{
	int stat, *jstat;
	pthread_t *cli_thread = val;

	if (!(cli_map = map_create(free)))
		return EXIT_FAILURE;

	/*
	 * Disable certain signals such as Ctrl+C.. make the shell a little stable
	 */
	redefineSignalHandler(SIGINT, dummyFunction);
	redefineSignalHandler(SIGQUIT, dummyFunction);
	redefineSignalHandler(SIGTSTP, dummyFunction);

	verbose(2, "[cliHandler]:: Registering CLI commands in the command table ");
	/*
	 * Register the commands allowed in the CLI. Each command is implemented by a
	 * function. The function is inserted into the command registary and picked up
	 * when the leading string is typed in the CLI.
	 */
	registerCLI("setip", setipCmd, SHELP_SETIP, USAGE_SETIP, LHELP_SETIP);  // Check
	registerCLI("setnm", setnmCmd, SHELP_SETNM, USAGE_SETNM, LHELP_SETNM);  // Check
	registerCLI("showip", showipCmd, SHELP_SHOWIP, USAGE_SHOWIP, LHELP_SHOWIP);  // Check
	registerCLI("shownm", shownmCmd, SHELP_SHOWNM, USAGE_SHOWNM, LHELP_SHOWNM);  // Check
	registerCLI("quitt", quitCmd, SHELP_QUIT, USAGE_QUIT, LHELP_QUIT);  // Check

	rl_instream = stdin;

	stat = pthread_create(cli_thread, NULL, CLIProcessCmdsInteractive, (void *)stdin);

	pthread_join(*cli_thread, (void **)&jstat);
	verbose(2, "[cliHandler]:: Destroying the CLI datastructures ");
	CLIDestroy();
}



/*
 * This function is called by the thread that is spawned to handle the CLI.
 * It reads the console and invokes the handlers to process the commands typed
 * by the user at the GINI router.
 */

void *CLIProcessCmdsInteractive(void *arg)
{
	FILE *fp = (FILE *)arg;

	CLIPrintHelpPreamble();
	CLIProcessCmds(fp, 1);
}



/*
 * managing the signals: first an ignore function.
 */
void dummyFunction(int sign)
{
	printf("Signal [%d] is ignored \n", sign);
}



void parseACLICmd(char *str)
{
	char *token;
	cli_entry_t *clie;
	char orig_str[MAX_TMPBUF_LEN];

	int ret;

	strcpy(orig_str, str);
	token = strtok(str, " \n");
	if ((clie = map_get(cli_map, token)) != NULL)
		clie->handler((void *)clie);
	else
	{
		printf("%s not a gRouter command\n", token);
		//ret = system(orig_str);
	}
}


void CLIPrintHelpPreamble()
{
	printf("\nGINI Router Shell, version: %s", prog_version());
	printf("\n%s\n", HELP_PREAMPLE);
}


void CLIPrintHelp() {
	cli_entry_t *clie;

	CLIPrintHelpPreamble();
	if (!(cli_mapper = mapper_create(cli_map)))
	{
		map_destroy(&cli_map);
		return;
	}
	while (mapper_has_next(cli_mapper) == 1)
	{

		const Mapping *cli_mapping = mapper_next_mapping(cli_mapper);

		clie = (cli_entry_t *) mapping_value(cli_mapping);
		printf("%s:: \t%s\n\t%s\n", clie->keystr, clie->usagestr,
				clie->short_helpstr);
	}

}


/*
 * Read a string, and return a pointer to it.
 * Returns NULL on EOF.
 */
char *rlGets(int online)
{
	char prompt[MAX_TMPBUF_LEN];

	if (cur_line != NULL)
	{
		free (cur_line);
		cur_line = (char *)NULL;
	}

	sprintf(prompt, "GINI-REMOTE-$ ");

	do
	{
		// Get a line from the user.
		cur_line = readline(prompt);
	} while (online && (cur_line == NULL));

	// If the line has any text in it,
	// save it on the history.
	if (cur_line && *cur_line)
		add_history (cur_line);

	return (cur_line);
}



/*
 * process CLI. The file pointer fp already points to an open stream. The
 * boolean variable online indicates whether processCLI is operating with
 * a terminal or from a batch input. For batch input, it should be FALSE.
 */

void CLIProcessCmds(FILE *fp, int online)
{
	int state = PROGRAM;
	char full_line[MAX_BUF_LEN];
	int lineno = 0;
	full_line[0] = '\0';

	// NOTE: the input stream for readline is already redirected
	// when processCLI is called from the "source" command.
	while ((cur_line = rlGets(online)) != NULL)
	{
		switch (state)
		{
		case PROGRAM:
			if (cur_line[0] == CARRIAGE_RETURN)
				break;
			if (cur_line[0] == LINE_FEED)
				break;
			if (cur_line[0] == COMMENT_CHAR)
				state = COMMENT;
			else if ((strlen(cur_line) > 2) && (cur_line[strlen(cur_line)-2] == CONTINUE_CHAR))
			{
				state = JOIN;
				strcat(full_line, cur_line);
			}
			else
			{
				strcat(full_line, cur_line);
				if (strlen(full_line) > 0)
					parseACLICmd(full_line);
				full_line[0] = '\0';
			}
			lineno++;
			break;
		case JOIN:
			full_line[strlen(full_line)-2] = '\0';
			if (cur_line[strlen(cur_line)-2] == CONTINUE_CHAR)
				strcat(full_line, cur_line);
			else
			{
				state = PROGRAM;
				strcat(full_line, cur_line);
				if (strlen(full_line) > 0)
					parseACLICmd(full_line);
				full_line[0] = '\0';
			}
			break;
		case COMMENT:
			if (cur_line[0] != COMMENT_CHAR)
			{
				if (cur_line[strlen(cur_line)-2] == CONTINUE_CHAR)
				{
					state = JOIN;
					strcat(full_line, cur_line);
				} else
				{
					state = PROGRAM;
					strcat(full_line, cur_line);
					if (strlen(full_line) > 0)
						parseACLICmd(full_line);
					full_line[0] = '\0';
				}
			}
			break;
			lineno++;
		}
	}
}




void CLIDestroy()
{
	mapper_destroy(&cli_mapper);
	map_destroy(&cli_map);
}


void registerCLI(char *key, void (*handler)(),
		 char *shelp, char *usage, char *lhelp)
{
	cli_entry_t *clie = (cli_entry_t *) malloc(sizeof(cli_entry_t));

	clie->handler = handler;
	strcpy(clie->long_helpstr, lhelp);
	strcpy(clie->usagestr, usage);
	strcpy(clie->short_helpstr, shelp);
	strcpy(clie->keystr, key);

	verbose(2, "adding command %s.. to cli map ", key);
	map_add(cli_map, key, clie);

}


/*------------------------------------------------------------------
 *               C L I  H A N D L E R S
 *-----------------------------------------------------------------*/


// some macro defintions...
#define GET_NEXT_PARAMETER(X, Y)			if (((next_tok = strtok(NULL, " \n")) == NULL) ||  \
												(strcmp(next_tok, X) != 0)) { error(Y); return; }; \
												next_tok = strtok(NULL, " \n")
#define GET_THIS_PARAMETER(X, Y)           	if (((next_tok = strtok(NULL, " \n")) == NULL) ||  \
												(strstr(next_tok, X) == NULL)) { error(Y); return; }
#define GET_THIS_OR_THIS_PARAMETER(X, Z, Y) if (((next_tok = strtok(NULL, " \n")) == NULL) ||  \
												((strstr(next_tok, X) == NULL) && \
												 (strstr(next_tok, Z) == NULL))) { error(Y); return; }

int isIP(char *val)
{
	int i, j;
	int sum;
	int pos = 0;
	int temp = 0;

	for (i = 0; i < 4; i++)
	{
		while (isdigit(val[temp]) != 0)
			temp++;

		if ((val[temp] != '.') && (i != 3))
			return 0;

		sum = 0;
		for (j = pos; j < temp; j++)
		{
			sum *= 10;
			sum += val[j] - '0';
		}
		if((sum < 0) || (sum > 255))
			return 0;

		temp++;
		pos = temp;
	}

	return 1;
}

void setipCmd()
{
	char *next_tok;
	uchar mac_addr[6], ip_addr[4], gw_addr[4];
	int mtu, ret;
	uchar tmpbuf[MAX_TMPBUF_LEN];

	bzero(gw_addr, 4);
	mtu = DEFAULT_MTU;

	next_tok = strtok(NULL, " \n");

	if (next_tok == NULL)
	{
		printf("[ifconfigCmd]:: missing action parameter.. type help ifconfig for usage.\n");
		return;
	}
	if (isIP(next_tok) == 0)
		return;

	IP2Dot(next_tok, ip_addr);

	sprintf(tmpbuf, "/sbin/ifconfig tap0 %s", next_tok);

	ret = system(tmpbuf);

	return;
}

void setnmCmd()
{
	return;
}

void showipCmd()
{
	return;
}

void shownmCmd()
{
	return;
}

void quitCmd()
{
	int ret;
	char* cmd;
	cmd = malloc(512);
	if (buf_ipfo != NULL)
		sprintf(cmd, "/bin/echo %s > /proc/sys/net/ipv4/ip_forward", buf_ipfo);
	else
		sprintf(cmd, "/bin/rm -f /proc/sys/net/ipv4/ip_forward");
	ret = system(cmd);
	if (buf_parp != NULL)
		sprintf(cmd, "/bin/echo %s > /proc/sys/net/ipv4/conf/%s/proxy_arp", buf_parp, buf_interface);
	else
		sprintf(cmd, "/bin/rm -f /proc/sys/net/ipv4/conf/%s/proxy_arp",buf_interface);
	ret = system(cmd);
	if (buf_sysc != NULL)
	{
		sprintf(cmd, "/sbin/sysctl -w net.ipv6.conf.all.forwarding=%s", buf_sysc);
		ret = system(cmd);
	}
	sprintf(cmd, "/usr/sbin/arp -i %s -d %s", buf_interface, gini_ip);
	ret = system(cmd);

	exit(0);
}


