/*
 * NAME: cli.c
 * FUNCTION: Collection of functions implement the command line shell
 * AUTHOR: Muthucumaru Maheswaran, Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

#include "cli.h"

extern FILE *rl_instream;

Map *cli_map;
Mapper *cli_mapper;
int cli_active = 1; // this is set to false by exitCmd();
static char *cur_line = (char *) NULL; // static variable for holding the line

// should have come from <readline/readline.h>
// some errors in those files prevented from including them!
//#include <readline/readline.h>
//#include <readline/history.h>
char *readline(char *prompt);
void add_history(char *line);

//=======================================================
//       FUNCTION: IniCli
//=======================================================
void IniCli() {
	pthread_t threadID;
	if (prog_verbosity_level() == 3) {
		printf("[IniCli]:: Initialize the command shell of the system ... ");
	}
	pthread_create(&threadID, NULL, (void *) cli_handler, NULL);
	if (prog_verbosity_level() == 3) {
		printf("[ OK ]\n");
	}
}

//=======================================================
//       FUNCTION: cli_handler
//=======================================================
void cli_handler() {
	//create a new cli_map
	if (!(cli_map = map_create(free))) {
		printf("IniCli(): Error, can not create the cli_map!");
		exit(1);
	}

	// register all the commands here...
	registerCLI("help", helpCmd, SHELP_HELP, USAGE_HELP, LHELP_HELP);
	registerCLI("halt", haltCmd, SHELP_HALT, USAGE_HALT, LHELP_HALT);
	registerCLI("exit", exitCmd, SHELP_EXIT, USAGE_EXIT, LHELP_EXIT);
	registerCLI("ch", chCmd, SHELP_CH, USAGE_CH, LHELP_CH);
	registerCLI("mac", macCmd, SHELP_MAC, USAGE_MAC, LHELP_MAC);
	registerCLI("ant", antCmd, SHELP_ANT, USAGE_ANT, LHELP_ANT);
	registerCLI("mov", movCmd, SHELP_MOV, USAGE_MOV, LHELP_MOV);
	registerCLI("wcard", wcardCmd, SHELP_WCARD, USAGE_WCARD, LHELP_WCARD);
	registerCLI("energy", energyCmd, SHELP_ENERGY, USAGE_ENERGY, LHELP_ENERGY);
	registerCLI("sys", sysCmd, SHELP_SYS, USAGE_SYS, LHELP_SYS);
	registerCLI("stats", statsCmd, SHELP_STATS, USAGE_STATS, LHELP_STATS);
	registerCLI("about", aboutCmd, SHELP_ABOUT, USAGE_ABOUT, LHELP_ABOUT);

	//show shell preamble
	printCLIShellPreamble();

	//chdir(wgnconfig.config_dir);
	if (wgnconfig.config_file != NULL) {
		FILE *ifile = fopen(wgnconfig.config_file, "r");
		printf("\n\n\nLoad the configuration file of '%s' ...\n",
				wgnconfig.config_file);
		rl_instream = ifile; // redirect the input stream
		processCLI(ifile);
		rl_instream = stdin;
		printf("\n");
	}
	if (wgnconfig.cli_flag != 0) {
		processCLI(stdin);
	}
}

void registerCLI(char *key, void(*handler)(), char *shelp, char *usage,
		char *lhelp) {
	cli_entry_t *clie = (cli_entry_t *) malloc(sizeof(cli_entry_t));

	clie->handler = handler;
	strcpy(clie->long_helpstr, lhelp);
	strcpy(clie->usagestr, usage);
	strcpy(clie->short_helpstr, shelp);
	strcpy(clie->keystr, key);

	map_add(cli_map, key, clie);
}

void parseCmd(char *str) {
	char *token;
	cli_entry_t *clie;
	char orig_str[MAX_TMPBUF_LEN];

	strcpy(orig_str, str);
	token = strtok(str, " \n");
	if ((clie = map_get(cli_map, token)) != NULL)
		clie->handler();
	else
		system(orig_str);
}

void printCLIHelp() {
	cli_entry_t *clie;

	printf(
			"\n#######################################################################\n");
	printf("\nWireless GINI Shell");
	printf("\nVersion: %s\n", prog_version());
	printf("\n%s", HELP_PREAMPLE);
	printf(
			"\n#######################################################################\n");
	if (!(cli_mapper = mapper_create(cli_map))) {
		map_destroy(&cli_map);
		return;
	}
	while (mapper_has_next(cli_mapper) == 1) {

		const Mapping *cli_mapping = mapper_next_mapping(cli_mapper);

		clie = (cli_entry_t *) mapping_value(cli_mapping);
		printf("%s:: \t%s\n\t%s\n", clie->keystr, clie->usagestr,
				clie->short_helpstr);
	}
	printf(
			"#######################################################################\n\n");

}

void printCLIShellPreamble()
{
	printf("\n#######################################################################\n");
	printf("\nWireless GINI Shell");
	printf("\nVersion: %s\n", prog_version());
	printf("\n%s", HELP_PREAMPLE);
	printf("\n#######################################################################\n\n\n\n");
}

void printCLIAbout()
{
	printf("\n#########################################################################\n");
	printf("\n%s", prog_desc());
	printf("\nVersion: %s", prog_version());
    printf("\nAuthor: %s", prog_author());
    printf("\nWeb link: %s", prog_url());
	printf("\nRelease date: %s", prog_date());
	printf("\nAll rights reserved.\n");
	printf("\n#########################################################################\n\n");
}

/*
 * Read a string, and return a pointer to it.
 * Returns NULL on EOF.
 */
char *rlGets (char *prompt)
{

	if (cur_line)
	{
		free (cur_line);
		cur_line = (char *)NULL;
	}

	// Get a line from the user.
	cur_line = readline(prompt);

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

void processCLI(FILE *fp)
{
	int state = PROGRAM;
	char full_line[MAX_BUF_LEN];
	int lineno = 0;
	full_line[0] = '\0';


	// NOTE: the input stream for readline is already redirected
	// when processCLI is called from the "source" command.
	while ((cli_active == 1) &&
	       ((cur_line = rlGets("WGINI $ ")) != NULL))
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
			else if (cur_line[strlen(cur_line)-2] == CONTINUE_CHAR)
			{
				state = JOIN;
				strcat(full_line, cur_line);
			}
			else
			{
				strcat(full_line, cur_line);
				if (strlen(full_line) > 0)
					parseCmd(full_line);
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
					parseCmd(full_line);
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
						parseCmd(full_line);
					full_line[0] = '\0';
				}
			}
			break;
			lineno++;

		}
	}
}

void helpCmd() {
	char *pchToken = strtok(NULL, " \n");
	cli_entry_t *n_clie;

	if (pchToken == NULL)
		printCLIHelp();
	else
	{
		n_clie = (cli_entry_t *)map_get(cli_map, pchToken);
		if (n_clie == NULL)
			printf("ERROR! No help for command: %s \n", pchToken);
		else
		{
			printf("\n%s:: %s\n", n_clie->keystr, n_clie->usagestr);
			printf("%s\n", n_clie->long_helpstr);
		}
	}
}

void haltCmd() {
	char ans[MAX_TMPBUF_LEN];

	printf("\nWARNING!! You want to really halt the router? (yes/no)");
	scanf("%s", ans);
	if (!strcmp(ans, "yes"))
	{
		verbose(0, "[haltCmd]:: Wireless GINI is shutting down. ");
		exit(1);
	}
}

void exitCmd() {
	verbose(0, "[exitCmd]:: Wireless GINI shell is closed. ");
	cli_active = 0;
}

void aboutCmd() {
    printCLIAbout();
}

void chCmd() {
	char *pchToken;
	int i, sid, did;
	int oscnumber;
	int verbose;

    if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
		return;
	}

	//parse command group of 'ch set ...'
    if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
			return;
		}
		//parse: ch set fad switch <on/off>
		if (!strcmp(pchToken, "fad")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "switch")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
			    }
				if (!strcmp(pchToken, "on")) {
					if (GetRayleighSign() == ON) {
						//printf ("[chCmd]:: The Rayleigh fading is already ON!");
						return;
					}
					else {
						verbose = prog_verbosity_level();
	                    prog_set_verbosity_level(0);
					    IniChannelFading();
						SetRayleighSign(ON);
                        prog_set_verbosity_level(verbose);
						//IniFadMatrix();
						//PrintLine ();
						//printf ("[chCmd]:: Set Rayleigh Fading ON successfully!\n");
						//PrintLine ();
						return;
					}
				}
				else if (!strcmp(pchToken, "off")) {
					if (GetRayleighSign() == OFF) {
						//printf ("[chCmd]:: The Rayleigh is already OFF!");
						return;
					}
					else {
						SetRayleighSign(OFF);
						//PrintLine ();
						//printf ("[chCmd]:: Set Rayleigh Fading OFF successfully!\n");
						//PrintLine ();
						return;
				    }
				}
  				else {
					printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "oscnum")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
			    }
				if (GetRayleighSign() == ON) {
					verbose = prog_verbosity_level();
	                prog_set_verbosity_level(0);
					SetRayleighSign(OFF);
					oscnumber=atoi(pchToken);
					if (oscnumber<=0) {
						printf ("[chCmd]:: Error, this parameter can only be set while the fading switch is on!\n");
						return;
					}
					FinalizeChannelFading();
					oscnum=oscnumber;
					IniChannelFading();
					SetRayleighSign(ON);
					prog_set_verbosity_level(verbose);
					return;
				}
				else {
				    printf ("[chCmd]:: Error, this parameter can only be set while the fading switch is on!\n");
					return;
				}
			}
			else {
			   printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
			   return;
			}
        }

		//parse: ch set awgn switch <on/off>
        //            ch set awgn mode <pwr/snr>
		else if (!strcmp(pchToken, "awgn")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
				return;
			}
            if (!strcmp(pchToken, "switch")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
					if (GetAwgnSign() == ON) {
						//printf ("[chCmd]:: The AWGN is already ON!");
						return;
					}
					else {
						SetAwgnSign(ON);
						//IniFadMatrix();
						//PrintLine ();
						//printf ("[chCmd]:: Set AWGN ON successfully!\n");
						//PrintLine ();
						return;
					}
				}
				else if (!strcmp(pchToken, "off")) {
					if (GetAwgnSign() == OFF) {
						//printf ("[chCmd]:: The AWGN is already OFF!");
						return;
					}
					else {
						SetAwgnSign(OFF);
						//PrintLine ();
						//printf ("[chCmd]:: Set AWGN OFF successfully!\n");
						//PrintLine ();
						return;
					}
				}
  				else {
					printf ("[chCmd]1:: command not found.. type 'help ch' for usage.\n");
					return;
				}
			}
		    else if (!strcmp(pchToken, "mode")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
				}
				if (GetAwgnSign()==OFF) {
					printf ("[chCmd]:: Error! You can only do this operation when AWGN is ON!");
					return;
				}
				if (!strcmp(pchToken, "snr")) {
					if (GetAwgnMode() == SNR) {
						//printf ("[chCmd]:: The AWGN is already in 'snr' mode!");
					}
					else {
						GetAwgnMode(SNR);
						//printf ("[chCmd]:: Set AWGN to 'snr' mode successfully!");
					}
				}
				else if (!strcmp(pchToken, "pwr")) {
					if (GetAwgnMode() == PWR) {
						//printf ("[chCmd]:: The AWGN is already in 'pwr' mode!");
					}
					else {
						GetAwgnMode(PWR);
						//printf ("[chCmd]:: Set AWGN to 'pwr' mode successfully!");
					}
				}
  				else {
					printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
					return;
				}
			}
            else if (!strcmp(pchToken, "para")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "noise")) {
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
						return;
					}
					if (GetAwgnSign()==ON && GetAwgnMode()==PWR) {
						Channel->channelAwgn->noise = (double)atof(pchToken);
						// if the mac status is MAC_RECV, change the status to MAC_IDLE
						for (i=1; i<=TotNodeNo; i++) {
							  rx_resume(WGNnode(i));
							  CheckBFTimer(WGNnode(i));
						}
 						//PrintLine ();
						//printf ("[chCmd]:: Change the awgn channel noise to be %f dbm!\n", noise);
						//PrintLine ();
						return;
					}
					else {
						printf ("[chCmd]:: Error! You can only do this operation when channel type is AWGN and mode is 'pwr'!\n");
						return;
					}
				}
				else if (!strcmp(pchToken, "ratio")) {
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
						return;
					}
					if (GetAwgnSign()==ON && GetAwgnMode()==SNR) {
						Channel->channelAwgn->snr = (double)atof(pchToken);
 						//PrintLine ();
						//printf ("[chCmd]:: Change the awgn channel snr to be %f !\n", snr_Eb_N0);
						//PrintLine ();
						return;
					}
					else
						printf ("[chCmd]:: Error! You can only do this operation when channel type is AWGN and mode is 'snr'!\n");
				}
				else {
					printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
					return;
				}
			}
			else {
			   printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
			   return;
			}
        }

		//parse: ch set prop mode <F/T/S>
		else if (!strcmp(pchToken, "prop")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
				return;
			}
		    if (!strcmp(pchToken, "mode")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "F")) {
					if (GetPropType() == FreeSpace) {
						//printf ("[chCmd]:: The channel has already in this mode!");
					}
					else	{
						SetPropType(FreeSpace);
						//PrintLine ();
						//printf ("[chCmd]:: Change the channel mode to FreeSpace successfully!\n");
						//PrintLine ();
					}
					return;
				}
				else if (!strcmp(pchToken, "T")) {
					if (GetPropType() == TwoRayGround) {
						//printf ("[chCmd]:: The channel has already in this mode!");
					}
					else	{
						SetPropType(TwoRayGround);
						//PrintLine ();
						//printf ("[chCmd]:: Change the channel mode to TwoRayGround successfully!\n");
						//PrintLine ();
					}
					return;
				}
				else if (!strcmp(pchToken, "S")) {
					if (GetPropType() == Shadowing) {
						//printf ("[chCmd]:: The channel has already in this mode!");
					}
					else	{
						SetPropType(Shadowing);
						//PrintLine ();
						//printf ("[chCmd]:: Change the channel mode to Shadowing successfully!\n");
						//PrintLine ();
					}
					return;
				}
				else {
					printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
					return;
				}
			}
            else if (!strcmp(pchToken, "para")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "exp")) {
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
						return;
					}
					if (GetPropType() == Shadowing) {
						Channel->channelProp->pathlossexp = (double)atof(pchToken);
 						//PrintLine ();
						//printf ("[chCmd]:: Change the channel path-loss exponential parameter to be %03f!\n", pathlossexp);
						//PrintLine ();
						return;
					}
					else {
						printf ("[chCmd]:: Error! You can only do this operation when channel is in SHADOWING mode!\n");
						return;
					}
				}
				else if (!strcmp(pchToken, "std")) {
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
						return;
					}
					if (GetPropType() == Shadowing) {
						Channel->channelProp->dev_db = (double)atof(pchToken);
 						//PrintLine ();
						//printf ("[chCmd]:: Change the channel deviation parameter to be %03f!\n", dev_db);
						//PrintLine ();
						return;
					}
					else
						printf ("[chCmd]:: Error! You can only do this operation when channel is in SHADOWING mode!\n");
				}
				else if (!strcmp(pchToken, "refdist")) {
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
						return;
					}
					if (GetPropType() == Shadowing) {
						Channel->channelProp->dist0 = (double)atof(pchToken);
 						//PrintLine ();
						//printf ("[chCmd]:: Change the channel deviation parameter to be %03f!\n", dev_db);
						//PrintLine ();
						return;
					}
					else
						printf ("[chCmd]:: Error! You can only do this operation when channel is in SHADOWING mode!\n");
				}
				else {
					printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
					return;
				}
			}
			else {
				printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
				return;
			}
        }
		else {
		   printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
           return;
		}
	}
    else if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[chCmd]:: missing parameters.. type 'help ch' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "info")) {
		    PrintLine ();
			printf ("Channel Information:\n");
			PrintLine ();
			switch(GetPropType()) {
				case FreeSpace:
					printf ("Propogation Mode: FreeSpace\n");
					break;
				case TwoRayGround:
					printf ("Propogation Mode: TwoRayGround\n");
					break;
				case Shadowing:
					printf ("Propagation Mode: Shadowing\n");
				    printf ("Propagation reference distance:  %0.2f m\n", Channel->channelProp->dist0);
				    printf ("Channel path-loss exponential parameter:  %0.2f\n", Channel->channelProp->pathlossexp);
					printf ("Channel standard deviation parameter:  %0.2f\n", Channel->channelProp->dev_db);
					break;
			    default:
					printf ("Invalid Propogation Mode.\n");
			}

			if (GetRayleighSign() == ON) {
				printf ("Rayleigh fading: ON \n");
				printf ("Emulated multi-path number is: %d \n",Channel->channelFad->N);
		    }
			else {
				printf ("Rayleigh Fading: OFF \n");
		    }

			if (GetAwgnSign() == ON) {
				printf ("AWGN: ON \n");
                if (GetAwgnMode() == SNR) {
					printf ("AWGN mode: snr \n");
					printf ("AWGN snr:  %0.2f\n", Channel->channelAwgn->snr);
                }
				else if (GetAwgnMode() == PWR) {
                    printf ("AWGN mode: pwr \n");
					printf ("AWGN noise:  %0.2f dB\n", Channel->channelAwgn->noise);
				}
			}
			else {
				printf ("AWGN: OFF \n");
			}
			PrintLine ();
			printf("\n");
            PrintLine ();
			printf("Link State Matrix: \n");
            printf("-R: In receiving communication range.\n");
			printf("-C: In carrier sense range.\n");
			printf("-N: Out of carrier sense range.\n");
			PrintLine ();
			LinkStateComp();
			for (did=1; did<=TotNodeNo; did++) {
				   printf ("\tNode %d:", did);
			}
			printf("\n");
			for (sid=1; sid<=TotNodeNo; sid++) {
				    printf ("Node %d:", sid);
					for (did=1; did<=TotNodeNo; did++) {
							if (sid==did)
								printf("\t  -");
							else {
								if (Channel->linkmatrix[sid-1][did-1] == 1) {
                                     printf("\t  %s","N");
								}
								else if (Channel->linkmatrix[sid-1][did-1] == 2) {
                                     printf("\t  %s","C");
								}
								else if (Channel->linkmatrix[sid-1][did-1] == 3) {
                                     printf("\t  %s","R");
								}
							}
					}
                    printf ("\n");
			}
			PrintLine ();
		    return;
		}
		else {
		   printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
           return;
		}
	}
	else {
       printf ("[chCmd]:: command not found.. type 'help ch' for usage.\n");
       return;
	}
}

void macCmd() {
	char *pchToken;
	unsigned int uiMac[6];
	double prob;
	int thres;
	int id;
	int i;

    if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
		return;
	}

	//parse command group of 'mac set ...'
    if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[macCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "txprob")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
					return;
				}
				if (SYS_INFO->mac_info->macType != CSMA) {
					printf ("[macCmd]:: Error: MAC mode is not CSMA currently. This parameter can only be used in CSMA mode.\n");
					return;
				}
				prob = (double)atof(pchToken);
				if (prob<=0 || prob>1.0) {
					printf ("[macCmd]:: Error: The value of the Tx probability should in range of (0,1]!\n");
					return;
				}
				WGNnode(id)->nodeMac->txprob = prob;
				//printf ("[macCmd]:: Set Tx probability successfully!");
			}
		    else if (!strcmp(pchToken, "addr")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
					return;
				}
				sscanf(pchToken, "%x:%x:%x:%x:%x:%x", &uiMac[0], &uiMac[1], &uiMac[2], &uiMac[3], &uiMac[4], &uiMac[5]);
		        for (i = 0; i<MAC_ADDR_LEN; i++) {
			           WGNnode(id)->nodeMac->mac_addr[i] = uiMac[i];
				}
		        memcpy(AddrToIDMap[id-1].mac_addr, WGNnode(id)->nodeMac->mac_addr, MAC_ADDR_LEN);
			}
			else if (!strcmp(pchToken, "rtsthres")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
					return;
				}
				if (SYS_INFO->mac_info->macType != DCF_802_11) {
					printf ("[macCmd]:: Error: MAC mode is not DCF_802_11 currently. This parameter can only be used in DCF_802_11 mode.");
					return;
				}
				thres = atoi(pchToken);
				if (thres<0) {
					printf ("[macCmd]:: Error: The value of the threshold should be equal or greater than 0!");
					return;
				}
				SYS_INFO->mac_info->MAC_RTSThreshold = thres;
				//printf ("[macCmd]:: Set MAC_RTSThreshold successfully!");
			}
			else if (!strcmp(pchToken, "mode")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "N")) {
					if (SYS_INFO->mac_info->macType == NONE) {
						return;
					}
					else	{
						ChMacMode(NONE);
					}
					return;
				}
				else if (!strcmp(pchToken, "C")) {
					if (SYS_INFO->mac_info->macType == CSMA) {
						return;
					}
					else	{
						ChMacMode(CSMA);
					}
				}
				else if (!strcmp(pchToken, "D11")) {
					if (SYS_INFO->mac_info->macType == DCF_802_11) {
						return;
					}
					else	{
						ChMacMode(DCF_802_11);
					}
				}
				else{
					printf ("[macCmd]:: command not found.. type 'help mac' for usage.\n");
					return;
				}
			}
			else {
				printf ("[macCmd]:: command not found.. type 'help mac' for usage.\n");
				return;
			}
		}
	    else {
			printf ("[macCmd]:: command not found.. type 'help mac' for usage.\n");
			return;
		}
	}
	else if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[macCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[macCmd]:: missing parameters.. type 'help mac' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "info")) {
		        PrintLine ();
			    printf ("MAC Layer Information of Node %d:\n", id);
		 	    PrintLine ();
				switch(SYS_INFO->mac_info->macType) {
					case NONE:
							 printf("Mac Mode:  NONE\n");
						break;
					case CSMA:
							 printf("Mac Mode:  P-PRESISTENT CSMA\n");
				        break;
					case DCF_802_11:
							 printf("Mac Mode:  DCF_802_11\n");
						break;
				}
				if (SYS_INFO->mac_info->macType == CSMA) {
		        	printf ("The Tx Probability is:  %0.2f\n", WGNnode(id)->nodeMac->txprob);
				}
				if (SYS_INFO->mac_info->macType == DCF_802_11) {
				    printf ("The RTS_Threshold is:  %d\n", SYS_INFO->mac_info->MAC_RTSThreshold);
					printf ("The Current CW is:  %d \n", WGNnode(id)->nodeMac->cw);
				}
				PrintLine ();
			}
			else {
				printf ("[macCmd]:: command not found.. type 'help mac' for usage.\n");
				return;
			}
		}
		else {
			printf ("[macCmd]:: command not found.. type 'help mac' for usage.\n");
			return;
		}
	}
	else {
       printf ("[macCmd]:: command not found.. type 'help mac' for usage.\n");
       return;
	}
}

void movCmd() {
	char *pchToken;
	int id;
	double maxspd, minspd;
	double x,y,z;

	if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
		return;
	}
	//parse command group of 'mov set ...'
    if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[movCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "switch")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
					if (GetEndSign(WGNnode(id)) == FALSE) {
						//printf ("[movCmd]:: The node has already in this status!");
						return;
					}
					else {
						SetEndSign(WGNnode(id), FALSE);
						//PrintLine ();
						//printf ("[movCmd]:: Set node %d movement to be ON successfully!\n", id);
						MovResume(WGNnode(id));
						//PrintLine ();
						return;
					}
				}
				else if (!strcmp(pchToken, "off")) {
					if (GetEndSign(WGNnode(id)) == TRUE) {
						//printf ("[movCmd]:: The node has already in this status!");
						return;
					}
					else {
						SetEndSign(WGNnode(id), TRUE);
						MovStop(WGNnode(id));
						//PrintLine ();
						//printf ("[movCmd]:: Set node %d movement to be OFF successfully!\n", id);
						//PrintLine ();
						return;
					}
				}
				else{
					printf ("[movCmd]:: command not found.. type 'help mov' for usage.\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "location")) {
				if (GetEndSign(WGNnode(id)) == FALSE) {
					printf ("[movCmd]:: This command can only be used when the node is stationary! you should stop the node movement first!\n");
				    return;
				}
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
					return;
				}
				x = atoi(pchToken);
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
					return;
				}
				y = atoi(pchToken);
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
					return;
				}
                z = atoi(pchToken);
				if (x>SYS_INFO->map_info->x_width||
					y>SYS_INFO->map_info->y_width||
					z>SYS_INFO->map_info->z_width) {
					printf ("[movCmd]:: Error: the value can not exceed the map size of (%0.2f, %0.2f, %0.2f)!\n",
						       SYS_INFO->map_info->x_width,
						       SYS_INFO->map_info->y_width,
						       SYS_INFO->map_info->z_width);
					return;
				}
				WGNnode(id)->nodePhy->nodeMobility->curPosition->x	 = x;
				WGNnode(id)->nodePhy->nodeMobility->curPosition->y	 = y;
				WGNnode(id)->nodePhy->nodeMobility->curPosition->z	 = z;
				//printf ("[movCmd]:: Set the location successfully! \n");
				//printf ("[movCmd]:: Now the new location of node %d is (%f, %f, %f)!\n", id, x, y, z);
			}
			else if (!strcmp(pchToken, "spd")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "max")) {
 					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
						return;
					}
					maxspd = atof(pchToken);

					if (maxspd < WGNnode(id)->nodePhy->nodeMobility->MinSpd) {
						printf ("movCmd]:: Error: maxmium speed should be greater than minimum speed!");
						return;
					}
					else {
						WGNnode(id)->nodePhy->nodeMobility->MaxSpd = maxspd;
						//PrintLine ();
						//printf ("movCmd]:: Set maximum speed to be %f! \n", maxspd);
						//PrintLine ();
					}
				}
				else if (!strcmp(pchToken, "min")) {
 					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
						return;
					}
     				minspd = atof(pchToken);

					if (minspd > WGNnode(id)->nodePhy->nodeMobility->MaxSpd) {
						printf ("movCmd]:: Error: minimum speed should be less than maximum speed!");
						return;
					}
					else {
						WGNnode(id)->nodePhy->nodeMobility->MinSpd = minspd;
						//PrintLine ();
						//printf ("movCmd]:: Set minimum speed to be %f! \n", minspd);
						//PrintLine ();
					}
				}
				else{
					printf ("[movCmd]:: command not found.. type 'help mov' for usage.\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "mode")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "R")) {
					if (WGNnode(id)->nodePhy->nodeMobility->mobilityType == RandomWayPoint) {
						//printf ("[movCmd]:: The node has already in this status!");
					}
					else	{
						WGNnode(id)->nodePhy->nodeMobility->mobilityType = RandomWayPoint;
						//PrintLine ();
						//printf ("[movCmd]:: Change node %d movement mode to RandomWayPoint successfully!\n", id);
						//PrintLine ();
					}
					return;
				}
				else if (!strcmp(pchToken, "T")) {
					printf ("[movCmd]:: This mode is not implemented at this monment!'");
					return;
				}
				else if (!strcmp(pchToken, "M")) {
					printf ("[movCmd]:: This mode is not implemented at this monment!'");
					return;
				}
				else{
					printf ("[movCmd]:: command not found.. type 'help mov' for usage.\n");
					return;
				}
			}
			else {
				printf ("[movCmd]:: command not found.. type 'help mov' for usage.\n");
				return;
			}
		}
		else {
			printf ("[movCmd]:: command not found.. type 'help mov' for usage.\n");
			return;
		}
	}
	else if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[movCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[movCmd]:: missing parameters.. type 'help mov' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "info")) {
		        PrintLine ();
			    printf ("Movement Information of Node %d:\n", id);
		 	    PrintLine ();
				x = WGNnode(id)->nodePhy->nodeMobility->curPosition->x;
				y = WGNnode(id)->nodePhy->nodeMobility->curPosition->y;
				z = WGNnode(id)->nodePhy->nodeMobility->curPosition->z;
				if (GetEndSign(WGNnode(id)) == TRUE) {
					printf ("Mobility Switch:  OFF\n");
					printf ("Current Location is:  (%0.2f, %0.2f, %0.2f) \n", x,y,z);
				}
				else {
					printf ("Mobility Switch:  ON\n");
					switch(WGNnode(id)->nodePhy->nodeMobility->mobilityType) {
						case RandomWayPoint:
							printf ("Mobility Mode:  RandomWayPoint \n");
							break;
						case TrajectoryBased:
							printf ("Mobility Mode:  TrajectoryBased \n");
							break;
						case Manual:
							printf ("Mobility Mode:  Manual \n");
							break;
					}
					printf ("Current Location is:  (%0.2f, %0.2f, %0.2f) \n", x,y,z);
					printf ("Current Speed is:  %0.2f  m/s \n", WGNnode(id)->nodePhy->nodeMobility->nodeSpd->spd_tot);
					printf ("Min/Max Speed are:  %0.2f m/s/%0.2f m/s\n", WGNnode(id)->nodePhy->nodeMobility->MinSpd, WGNnode(id)->nodePhy->nodeMobility->MaxSpd);
				}
				PrintLine ();
			}
			else {
				printf ("[movCmd]:: command not found.. type 'help energy' for usage.\n");
				return;
			}
		}
	}
	else {
       printf ("[movCmd]:: command not found.. type 'help mov' for usage.\n");
       return;
	}
}

void antCmd() {
	char *pchToken;
	double height, gain, sysloss;
	double jamint;
	int id;

	if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
		return;
	}
	//parse command group of 'ant set ...'
    if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[antCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "height")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
					return;
				}
				height = (double)atof(pchToken);
				if (height <= 0) {
					printf ("[antCmd]:: Error: The height of the antenna should be postive!");
					return;
				}
				WGNnode(id)->nodePhy->nodeAntenna->Height =	height;
				//printf ("[antCmd]:: Set height for node successfully");
			}
			else if (!strcmp(pchToken, "gain")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
					return;
				}
				gain = (double)atof(pchToken);
				if (gain <= 0) {
					printf ("[antCmd]:: Error: The height of the antenna should be postive!");
					return;
				}
				WGNnode(id)->nodePhy->nodeAntenna->Gain_dBi =	gain;
			}
			else if (!strcmp(pchToken, "sysloss")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
					return;
				}
				sysloss = (double)atof(pchToken);
				if (sysloss <= 0) {
					printf ("[antCmd]:: Error: The height of the antenna should be postive!");
					return;
				}
				WGNnode(id)->nodePhy->nodeAntenna->SysLoss =	sysloss;
			}
			else if (!strcmp(pchToken, "jam")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[antCmd]:: missing parameters.. type 'help phy' for usage.\n");
					return;
				}
				if (SYS_INFO->mac_info->macType != DCF_802_11) {
					printf ("[antCmd]:: Error: 'jam' is only supported when MAC mode is DCF_802_11.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
					KillJamInt(id);
					SetJamInt(id, GetCSThreshold(WGNnode(id))+0.1/1000000000); //set default value of the jam pwr.
					//printf ("[phyCmd]:: Set the Jam interference to the default value successfully!");
				}
				else if  (!strcmp(pchToken, "off")) {
					KillJamInt(id);
					//printf ("[phyCmd]:: Remove the Jam interference successfully!");
				}
				else {
					 //if (atof(pchToken)>0) {
					KillJamInt(id);
					jamint = DBToW(atof(pchToken));
					SetJamInt(id, jamint);
					//PrintLine ();
					//printf ("[phyCmd]:: Set the Jam interference of node %d to be %f db!\n", id, atof(pchToken));
					//PrintLine ();
				}
			}
			else	{
			    printf ("[antCmd]:: command not found.. type 'help ant' for usage.\n");
			    return;
			}
		}
	}
	else if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[antCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[antCmd]:: missing parameters.. type 'help ant' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "info")) {
		        PrintLine ();
			    printf ("Antenna Information of Node %d:\n", id);
		 	    PrintLine ();
				switch(WGNnode(id)->nodePhy->nodeAntenna->AntType) {
					case OmniDirectionalAnt:
						printf ("Antenna Type:  OmniDirectional \n");
						break;
					case SwitchedBeamAnt:
						printf ("Antenna Type:  SwitchedBeam \n");
						break;
					case AdaptiveArrayAnt:
						printf ("Antenna Type:  AdaptiveArray \n");
						break;
				}
				printf ("Antenna Gain:  %0.2f \n", WGNnode(id)->nodePhy->nodeAntenna->Gain_dBi);
				printf ("Antenna System Loss:  %0.2f \n", WGNnode(id)->nodePhy->nodeAntenna->SysLoss);
				printf ("Antenna Height:  %0.2f m\n", WGNnode(id)->nodePhy->nodeAntenna->Height);
				printf("Jam interference is:  %0.2f db\n", WToDB(WGNnode(id)->nodePhy->nodeAntenna->jamInt));
				PrintLine ();
			}
			else {
				printf ("[antCmd]:: command not found.. type 'help energy' for usage.\n");
				return;
			}
		}
	}
	else {
       printf ("[antCmd]:: command not found.. type 'help ant' for usage.\n");
       return;
	}
}

void wcardCmd() {
	char *pchToken;
	int id;
	float para;

	if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
		return;
	}
    if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[wcardCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "info")) {
		        PrintLine ();
			    printf ("Wireless NIC Information of Node %d:\n", id);
		 	    PrintLine ();
				switch(WGNnode(id)->nodePhy->nodeWCard->ModType) {
					case DSSS:
						printf ("Emission Type: DSSS  \n");
						break;
					case FHSS:
						printf ("Emission Type: FHSS  \n");
						break;
				}
				if ((int)WGNnode(id)->nodePhy->nodeWCard->freq>=1000) {
                    printf ("Frequency:  %0.2f GHz\n", WGNnode(id)->nodePhy->nodeWCard->freq/1000);
				}
				else{
				    printf ("Frequency:  %d MHz\n", (int)WGNnode(id)->nodePhy->nodeWCard->freq);
				}
				printf ("Bandwidth:  %d Mbps\n", (int)WGNnode(id)->nodePhy->nodeWCard->bandwidth/MIG);
				printf ("TX Power:  %0.2f dB / %0.2f W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->Pt), WGNnode(id)->nodePhy->nodeWCard->Pt);
				printf ("Power consume of TX state:  %0.2f dB / %0.2f W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->Pt_consume), WGNnode(id)->nodePhy->nodeWCard->Pt_consume);
				printf ("Power consume of RX state:  %0.2f dB / %0.2f W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->Pr_consume), WGNnode(id)->nodePhy->nodeWCard->Pr_consume);
				printf ("Power consume of IDLE state:  %0.2f dB / %0.2f W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->P_idle), WGNnode(id)->nodePhy->nodeWCard->P_idle);
				printf ("Power consume of SLEEP state:  %0.2f dB / %0.2f W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->P_sleep), WGNnode(id)->nodePhy->nodeWCard->P_sleep);
				printf ("Power consume of OFF state:  %0.2f dB / %0.2f W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->P_off), WGNnode(id)->nodePhy->nodeWCard->P_off);
				printf ("Carrier Sense Threshold: %0.2f dB / %0.2f*10^(-8) W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->CSThresh),WGNnode(id)->nodePhy->nodeWCard->CSThresh*pow(10,8));
				printf ("Reception Threshold:  %0.2f dB / %0.2f*10^(-8) W\n", WToDB(WGNnode(id)->nodePhy->nodeWCard->RXThresh),WGNnode(id)->nodePhy->nodeWCard->RXThresh*pow(10,8));
				printf ("Capture Threshold:  %0.2f dB\n", WGNnode(id)->nodePhy->nodeWCard->CPThresh);
				if (GetCapSign(WGNnode(id)) == ON)
					printf ("Capture Effect:  ON\n");
				else
					printf ("Capture Effect:  OFF\n");
				PrintLine ();
			}
			else {
				printf ("[wcardCmd]:: command not found.. type 'help energy' for usage.\n");
				return;
			}
		}
	}
	else if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			 printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
			 return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[wcardCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "freq")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				//is it valid???
				for (id=1; id<=TotNodeNo; id++) {
					   WGNnode(id)->nodePhy->nodeWCard->freq  = para;     //MHz
				}
			}
			else if (!strcmp(pchToken, "bandwidth")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
                ChWcardBandWidth(para*pow(10,6));
			}
			else if (!strcmp(pchToken, "pt")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
				       WGNnode(id)->nodePhy->nodeWCard->Pt  = para;      //W
				}
			}
			else if (!strcmp(pchToken, "ptx")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
					   WGNnode(id)->nodePhy->nodeWCard->Pt_consume  = para;     //W
				}
			}
			else if (!strcmp(pchToken, "prx")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
					   WGNnode(id)->nodePhy->nodeWCard->Pr_consume  = para;     //W
				}
			}
			else if (!strcmp(pchToken, "pidle")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
					   WGNnode(id)->nodePhy->nodeWCard->P_idle  = para;     //W
				}
			}
			else if (!strcmp(pchToken, "psleep")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
					   WGNnode(id)->nodePhy->nodeWCard->P_sleep  = para;     //W
				}
			}
			else if (!strcmp(pchToken, "poff")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
					   WGNnode(id)->nodePhy->nodeWCard->P_off  = para;     //W
				}
			}
			else if (!strcmp(pchToken, "rxthreshold")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
				       WGNnode(id)->nodePhy->nodeWCard->RXThresh = para*pow(10,(-8));       //10^(-8)W
			    }
			}
			else if (!strcmp(pchToken, "csthreshold")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
				       WGNnode(id)->nodePhy->nodeWCard->CSThresh = para*pow(10,(-8));         //10^(-8)W
			    }
			}
			else if (!strcmp(pchToken, "cpthreshold")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				para=atof(pchToken);
				for (id=1; id<=TotNodeNo; id++) {
				       WGNnode(id)->nodePhy->nodeWCard->CPThresh = para;              //dB
			    }
			}
			else if (!strcmp(pchToken, "modtype")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[wcardCmd]:: missing parameters.. type 'help wcard' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "D")) {
					for (id=1; id<=TotNodeNo; id++) {
						  WGNnode(id)->nodePhy->nodeWCard->ModType = DSSS;              //dB
					}
				}
				else if (!strcmp(pchToken, "F")) {
					printf ("[phyCmd]:: No implementation of FHSS mode currently, sorry!\n");
				}
				else	{
					printf ("[phyCmd]:: command not found.. type 'help phy' for usage.\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "cap")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[phyCmd]:: missing parameters.. type 'help phy' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
					if (GetCapSign(WGNnode(id)) == ON) {
						//printf ("[phyCmd]:: The Capture is already ON!");
						return;
					}
					else {
						SetCapSign(WGNnode(id), ON);
						//PrintLine ();
						//printf ("[phyCmd]:: Set Capture ON successfully!\n");
						//PrintLine ();
						return;
					}
				}
				else if (!strcmp(pchToken, "off")) {
					if (GetCapSign(WGNnode(id)) == OFF) {
						//printf ("[phyCmd]:: The Capture is already OFF!");
						return;
					}
					else {
						SetCapSign(WGNnode(id), OFF);
						//PrintLine ();
						//printf ("[phyCmd]:: Set Capture OFF successfully!\n");
						//PrintLine ();
						return;
					}
				}
				else{
					printf ("[wcardCmd]:: command not found.. type 'help phy' for usage.\n");
					return;
				}
			}
			else {
				printf ("[wcardCmd]:: command not found.. type 'help wcard' for usage.\n");
				return;
			}
		}
		else {
			printf ("[wcardCmd]:: command not found.. type 'help wcard' for usage.\n");
			return;
		}
	}
	else {
       printf ("[wcardCmd]:: command not found.. type 'help wcard' for usage.\n");
       return;
	}
}

void energyCmd() {
	char *pchToken;
	int id;

	if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
		return;
	}
	//parse command group of 'wcard set ...'
	if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[energyCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "info")) {
		        PrintLine ();
			    printf ("Energy Information of Node %d:\n", id);
		 	    PrintLine ();
				if (WGNnode(id)->nodePhy->nodeEnergy->PowSwitch == ON) {
					printf ("Energy Switch:  ON \n");
					if (WGNnode(id)->nodePhy->nodeEnergy->PSM == ON) {
						printf ("PSM Mode:  ON \n");
					}
					else
						printf ("PSM Mode:  OFF \n");
					printf ("Energy Remain:  %01f  J\n", WGNnode(id)->nodePhy->nodeEnergy->TotalEnergy);
				}
				else
					printf ("Energy Switch:  OFF \n");
				PrintLine ();
			}
			else {
				printf ("[energyCmd]:: command not found.. type 'help energy' for usage.\n");
				return;
			}
		}
	}
	else if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[energyCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "switch")) {
 				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
				    printf ("[energyCmd]:: current wireless GINI does NOT support energy calculation. sorry!\n");
				}
				else	if (!strcmp(pchToken, "off")) {
				    printf ("[energyCmd]:: current wireless GINI does NOT support energy calculation. sorry!\n");
				}
				else {
					printf ("[energyCmd]:: command not found.. type 'help energy' for usage.\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "psm")) {
 				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
				    printf ("[energyCmd]:: current wireless GINI does NOT support energy calculation. sorry!\n");
				}
				else	if (!strcmp(pchToken, "off")) {
				    printf ("[energyCmd]:: current wireless GINI does NOT support energy calculation. sorry!\n");
				}
				else {
					printf ("[energyCmd]:: command not found.. type 'help energy' for usage.\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "totenergy")) {
 				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
				    printf ("[energyCmd]:: current wireless GINI does NOT support energy calculation. sorry!\n");
				}
				else	if (!strcmp(pchToken, "off")) {
				    printf ("[energyCmd]:: current wireless GINI does NOT support energy calculation. sorry!\n");
				}
				else {
					printf ("[energyCmd]:: command not found.. type 'help energy' for usage.\n");
					return;
				}
			}
			else {
				printf ("[energyCmd]:: command not found.. type 'help energy' for usage.\n");
				return;
			}
		}
	}
	else {
       printf ("[energyCmd]:: command not found.. type 'help energy' for usage.\n");
       return;
	}
}

void sysCmd() {
	FILE *fp;
	char *pchToken;
	int x,y,z;
	int id;
	int i, level;
	//int number;

    if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[chCmd]:: missing parameters.. type 'help sys' for usage.\n");
		return;
	}
    if (!strcmp(pchToken, "src")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
			return;
		}
		if ((fp = fopen(pchToken, "r")) == NULL) {
			printf ("[sysCmd]:: Error: can not open the configuration file.\n");
			return;
		}
		printf("Load the configuration file of '%s' ...\n", pchToken);
        rl_instream = fp;
	    processCLI(fp);
	    rl_instream = stdin;
		printf("\n");
	}
	else if (!strcmp(pchToken, "reload")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
			return;
		}
		//printf("\n\nRebooting the system ...\n\n");
		ReloadWGN();
		if ((fp = fopen(pchToken, "r")) == NULL) {
			printf ("[sysCmd]:: Error: can not open the configuration file.\n");
			return;
		}
		printf("\n\nReloading the new configuration file of '%s' ...\n", pchToken);
		rl_instream = fp;
		processCLI(fp);
		rl_instream = stdin;
		printf("\n");
	}
	else if (!strcmp(pchToken, "set")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "map")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "size")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
					return;
				}
                x = atoi(pchToken);
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
					return;
				}
                y = atoi(pchToken);
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
					return;
				}
				z = atoi(pchToken);
				SYS_INFO->map_info->x_width = x;
				SYS_INFO->map_info->y_width = y;
				SYS_INFO->map_info->z_width = z;
				//printf ("[sysCmd]:: Set the map size successfully! \n");
				//printf ("[sysCmd]:: Now the new map size is (%d, %d, %d)!\n", x, y, z);
			}
			else {
				printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
				return;
			}
		}
		else if (!strcmp(pchToken, "verbose")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
				return;
			}
			level = atoi(pchToken);
			if ((level >= 0) && (level <= 6)) {
				prog_set_verbosity_level(level);
				//printf("\nCurrent verbose level: %d \n", prog_verbosity_level());
			}
			else
				printf ("[sysCmd]:: Error! The verbose level should be in [0..6].\n");
		}
		else {
			printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
			return;
		}
	}
	else if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
			return;
		}
		if (!strcmp(pchToken, "verbose")) {
			PrintLine();
			printf("Current verbose level: %d \n", prog_verbosity_level());
			PrintLine();
			return;
		}
        else if (!strcmp(pchToken, "map")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[sysCmd]:: missing parameters.. type 'help sys' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "size")) {
				PrintLine ();
				printf ("Map Size:\n");
				PrintLine ();
				printf ("X_Width Size: %0.2f m\n", SYS_INFO->map_info->x_width);
				printf ("Y_Width Size: %0.2f m\n", SYS_INFO->map_info->y_width);
				printf ("Z_Width Size: %0.2f m\n", SYS_INFO->map_info->z_width);
				PrintLine ();
				return;
			}
			else {
				printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
				return;
			}
		}
        else if (!strcmp(pchToken, "dev")) {
			PrintLine ();
			printf ("Network Devices Information:\n");
			PrintLine ();
			printf ("Total Mobile Node Number: %d \n",TotNodeNo);
			PrintLine ();
			for (id=1; id<=TotNodeNo; id++) {
					printf ("NODE ID: %d  \n",id);
					if (WGNnode(id)->nodeType == NORMAL) {
						printf ("TYPE: NORMAL\n");
					}
					else
						printf ("TYPE: AP\n");
					printf ("MAC ADDRESS: ");
    				for(i=0; i<MAC_ADDR_LEN; i++) {
						  printf("%02x.",AddrToIDMap[id-1].mac_addr[i]);
					}
					printf("\n");
					PrintLine ();
			}
			return;
		}
        else if (!strcmp(pchToken, "time")) {
			PrintCurTime ();
			return;
		}
        else if (!strcmp(pchToken, "event")) {
			PrintEventList();
			return;
		}
        else if (!strcmp(pchToken, "timer")) {
			for (id=1; id<=TotNodeNo; id++) {
				    PrintLine ();
					printf("NODE %d : \n", id);
					PrintLine ();
					if (Timer_SwitchSign(WGNnode(id), BF_TIMER) == ON && Timer_PauseSign(WGNnode(id), BF_TIMER) == TRUE) {
						printf("BF_TIMER: ON but PAUSED\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), BF_TIMER) == ON && Timer_PauseSign(WGNnode(id), BF_TIMER) == FALSE) {
						printf("BF_TIMER: ON\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), BF_TIMER) == OFF) {
						printf("BF_TIMER: OFF\n");
					}
					if (Timer_SwitchSign(WGNnode(id), DF_TIMER) == ON) {
						printf("DF_TIMER: ON\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), DF_TIMER) == OFF) {
						printf("DF_TIMER: OFF\n");
					}
					if (Timer_SwitchSign(WGNnode(id), NAV_TIMER) == ON) {
						printf("NAV_TIMER: ON\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), NAV_TIMER) == OFF) {
						printf("NAV_TIMER: OFF\n");
					}
					if (Timer_SwitchSign(WGNnode(id), IF_TIMER) == ON) {
						printf("IF_TIMER: ON\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), IF_TIMER) == OFF) {
						printf("IF_TIMER: OFF\n");
					}
					if (Timer_SwitchSign(WGNnode(id), TX_TIMER) == ON) {
						printf("TX_TIMER: ON\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), TX_TIMER) == OFF) {
						printf("TX_TIMER: OFF\n");
					}
					if (Timer_SwitchSign(WGNnode(id), RX_TIMER) == ON) {
						printf("RX_TIMER: ON\n");
					}
					else if (Timer_SwitchSign(WGNnode(id), RX_TIMER) == OFF) {
						printf("RX_TIMER: OFF\n");
					}
					PrintLine ();
			}
		}
		else {
			printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
			return;
		}
	}
	else {
       printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
       return;
	}
}

void statsCmd() {
	char *pchToken;
	int id,i;
	char filename[MAX_REPORT_NAME_LEN];
    float period;
	WGNTime start_time, end_time;
	int throughput, tot_throughput;


	if ((pchToken = strtok(NULL, " \n")) == NULL) {
		printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
		return;
	}
	//parse command group of 'stats trace ...'
    if (!strcmp(pchToken, "trace")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
			return;
	    }
		if (!strcmp(pchToken, "ch")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "on")) {
				if (Channel->channelFadPrintSign == TRUE) {
					printf ("[statsCmd]:: WGINI is already tracing the channel states!\n");
					return;
				}
				else	{
					if (GetRayleighSign() == ON) {
						if ((pchToken = strtok(NULL, " \n")) == NULL) {
							//strcpy(ch_rep_name, REPORT_PATH_PREFIX);
							chdir(getenv("GINI_HOME"));
							strcpy(ch_rep_name, "STATS_REPORT_DIRECTORY");
							strcat(ch_rep_name, CH_REP_PREFIX);
							//getcwd(rep_path, MAX_REPORT_PATH_LEN);
							//strcat(rep_path, "/");
							//strcat(rep_path, ch_rep_name);
       						printf ("[statsCmd]:: Start tracing the channel states and generate a default output file $GINI_HOME/%s!\n", ch_rep_name);
						}
						else if (!strcmp(pchToken, ">")) {
							if ((pchToken = strtok(NULL, " \n")) == NULL) {
								printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
								return;
							}
							else	{
								if (IsFileValid(pchToken) == FALSE) {
									printf ("[statsCmd]:: Invalid destination file name for the channel fading report!\n");
									return;
								}
								strcpy(ch_rep_name, pchToken);
								printf ("[statsCmd]:: Start tracing the channel states and generate a output file %s!\n", pchToken);
							}
						}
						else {
							printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
							return;
						}
						Channel->channelFadPrintSign = TRUE;
					}
					else
						printf ("[statsCmd]:: Channel can NOT be traced at this moment, the fading is OFF!\n");
				}
			}
			else if (!strcmp(pchToken, "off")) {
				if (Channel->channelFadPrintSign == TRUE) {
					Channel->channelFadPrintSign = FALSE;
					//printf ("[statsCmd]:: Stop tracing the channel states!");
					return;
			    }
			    else {
				   printf ("[statsCmd]:: The channel has already stopped tracing!");
			       return;
			    }
			}
			else {
				printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
				return;
			}
		}
		else if (!strcmp(pchToken, "eve")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "on")) {
				if (PrintEventSign == TRUE) {
					printf ("[statsCmd]:: WGINI is already tracing the system events!\n");
					return;
				}
				else	{
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						//strcpy(eve_rep_name, REPORT_PATH_PREFIX);
						chdir(getenv("GINI_HOME"));
						strcpy(eve_rep_name, STATS_REPORT_DIRECTORY);
						strcat(eve_rep_name, EVE_REP_PREFIX);
						//getcwd(rep_path, MAX_REPORT_PATH_LEN);
						//strcat(rep_path, "/");
						//strcat(rep_path, eve_rep_name);
       					printf ("[statsCmd]:: Start tracing the system events and generate a default output file $GINI_HOME/%s!\n", eve_rep_name);
					}
					else if (!strcmp(pchToken, ">")) {
						if ((pchToken = strtok(NULL, " \n")) == NULL) {
							printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
							return;
						}
						else	{
							if (IsFileValid(pchToken) == FALSE) {
								printf ("[statsCmd]:: Invalid destination file name for the event report!\n");
								return;
							}
							strcpy(eve_rep_name, pchToken);
							printf ("[statsCmd]:: Start tracing the system events and generate a output file %s!\n", pchToken);
						}
					}
					else {
						printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
						return;
					}
					PrintEventSign = TRUE;
				}
			}
			else if (!strcmp(pchToken, "off")) {
				if (PrintEventSign == TRUE) {
					PrintEventSign = FALSE;
					//printf ("[statsCmd]:: Stop tracing the system events!");
					return;
			    }
			    else {
				   printf ("[statsCmd]:: The system has already stopped tracing events!");
			       return;
			    }
			}
			else {
				printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
				return;
			}
		}
		else if (!strcmp(pchToken, "th")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "on")) {
				if (ThroutputComSign == TRUE) {
					printf ("[statsCmd]:: WGINI is calculating the throughput now!\n");
					return;
				}
				else	{
					ThroutputComSign = TRUE;
					for (id=1; id<=TotNodeNo; id++) {
						  WGNnode(id)->nodeStats->ThCompStartTime = GetTime();
					}
					printf ("[statsCmd]:: Start calculating the throughput for all nodes!\n");
					return;
				}
			}
			else if (!strcmp(pchToken, "off")) {
				if (ThroutputComSign == FALSE) {
					printf ("[statsCmd]:: WGINI has already stopped calculating the throughput!\n");
					return;
				}
				else	{
					ThroutputComSign = FALSE;
					//printf ("[statsCmd]:: Stop calculating the throughput for all nodes!!");
					PrintLine ();
					tot_throughput = 0;
					for (id=1; id<=TotNodeNo; id++) {
						  end_time = GetTime();
						  start_time = WGNnode(id)->nodeStats->ThCompStartTime;
						  period = (end_time.tv_sec - start_time.tv_sec) +
							            (float)(end_time.tv_nsec - start_time.tv_nsec)/NFACTOR;
						  throughput = (int)(WGNnode(id)->nodeStats->TotTxByteNo)/(period*1000);
						  tot_throughput = tot_throughput + throughput;
						  WGNnode(id)->nodeStats->TotTxByteNo = 0;
						  printf("Node %d throughput: %d kB/s\n", id, throughput);
					}
					PrintLine ();
					printf("Total network throughput: %d kB/s\n", tot_throughput);
					PrintLine ();
					return;
				}
			}
			else {
				printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
				return;
			}
		}
		else if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[statsCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "mov")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
					return;
				}
				if (!strcmp(pchToken, "on")) {
					if (PrintMovArray[id-1] == TRUE) {
						printf ("[statsCmd]:: This node is already tracing the node mobility!\n");
						return;
					}
					else	{
						if ((pchToken = strtok(NULL, " \n")) == NULL) {
							WGNnode(id)->nodePhy->nodeMobility->mov_rep_name = (char*)malloc(sizeof(char)*MAX_REPORT_NAME_LEN);
							FileNameGen(id, "mob", filename);
							//strcpy(WGNnode(id)->nodePhy->nodeMobility->mov_rep_name, REPORT_PATH_PREFIX);
							strcpy(WGNnode(id)->nodePhy->nodeMobility->mov_rep_name, STATS_REPORT_DIRECTORY);
							strcat(WGNnode(id)->nodePhy->nodeMobility->mov_rep_name, filename);
							PrintMovArray[id-1] = TRUE;
							printf ("[statsCmd]:: Start tracing the mobility of this node and generate a mobility report with the name of $GINI_HOME/%s!\n", WGNnode(id)->nodePhy->nodeMobility->mov_rep_name);
						}
						else if (!strcmp(pchToken, ">")) {
							if ((pchToken = strtok(NULL, " \n")) == NULL) {
								printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
								return;
							}
							else	{
								if (IsFileValid(pchToken) == FALSE) {
									printf ("[statsCmd]:: Invalid destination file name for the mobility report!\n");
									return;
								}
							    WGNnode(id)->nodePhy->nodeMobility->mov_rep_name = pchToken;
								pchToken = NULL;
								PrintMovArray[id-1] = TRUE;
								printf ("[statsCmd]:: Start tracing the mobility of this node and generate a mobility report with the name of %s!\n", WGNnode(id)->nodePhy->nodeMobility->mov_rep_name);
							}
						}
						else {
							printf ("[sysCmd]:: command not found.. type 'help stats' for usage.\n");
							return;
						}
					}
				}
				else if (!strcmp(pchToken, "off")) {
					if (PrintMovArray[id-1] == TRUE) {
						PrintMovArray[id-1] = FALSE;
						if (WGNnode(id)->nodePhy->nodeMobility->mov_rep_name != NULL) {
							free(WGNnode(id)->nodePhy->nodeMobility->mov_rep_name);
						}
						//printf ("[statsCmd]:: Stop tracing the node movement!");
						return;
					}
					else {
						printf ("[statsCmd]:: The movement tracing of this node has already been stopped!\n");
						return;
					}
				}
				else {
					printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
					return;
				}
			}
			else {
				printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
				return;
			}
		}
		else {
			printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
			return;
		}
	}
	else if (!strcmp(pchToken, "show")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
			return;
	    }
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<0||id>TotNodeNo) {
				//PrintLine ();
				printf ("[statsCmd]:: Error: The node id should between 0 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
            if (!strcmp(pchToken, "interface")) {
				StatsComp(id);
                printf ("\ninterface0");
                printf ("\tLink encap: 802.11 Wireless   HWaddr: ");
                for(i=0; i<MAC_ADDR_LEN; i++) {
					  printf("%02x.",AddrToIDMap[id-1].mac_addr[i]);
				}
				printf ("\n\t\tTX packets:    %ld ", WGNnode(id)->nodeStats->TotPktTxed);
				printf ("\n\t\tRX packets:    %ld ", WGNnode(id)->nodeStats->TotPktRxed);
				printf ("\n\t\tRX collision rate:    %0.2f%%", WGNnode(id)->nodeStats->RecvColErrorDropRate*100);
				printf ("\n\t\tTX collision rate:    %0.2f%%", WGNnode(id)->nodeStats->RecvWhileTxErrorDropRate*100);
				printf ("\n\t\tFading error rate:    %0.2f%%", WGNnode(id)->nodeStats->RecvLowPwrErrorDropRate*100);
				printf ("\n\t\tNoise error rate:    %0.2e%%\n", WGNnode(id)->nodeStats->RecvNoiseErrorDropRate*100);
			}
			else {
				printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
				return;
			}
		}
		else {
			printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
			return;
		}
	}
	else if (!strcmp(pchToken, "clean")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
			return;
	    }
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<0||id>TotNodeNo) {
				//PrintLine ();
				printf ("[statsCmd]:: Error: The node id should between 0 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			ResetStats(id);
		}
		else {
			printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
			return;
		}
	}
	else if (!strcmp(pchToken, "report")) {
		if ((pchToken = strtok(NULL, " \n")) == NULL) {
			printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
			return;
	    }
		if (!strcmp(pchToken, "node")) {
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[energyCmd]:: missing parameters.. type 'help energy' for usage.\n");
				return;
			}
			//get the node id
			id = atoi(pchToken);
			if (id<1||id>TotNodeNo) {
				//PrintLine ();
				printf ("[statsCmd]:: Error: The node id should between 1 to %d!\n", TotNodeNo);
				//PrintLine ();
				return;
			}
			if ((pchToken = strtok(NULL, " \n")) == NULL) {
				printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
				return;
			}
			if (!strcmp(pchToken, "P")) {
				if ((pchToken = strtok(NULL, " \n")) == NULL) {
					 FileNameGen(id, "pkt", filename);
					 //strcpy(pkt_rep_name, REPORT_PATH_PREFIX);
					 chdir(getenv("GINI_HOME"));
					 strcpy(pkt_rep_name, STATS_REPORT_DIRECTORY);
					 strcat(pkt_rep_name, filename);
					 StatsComp(id);
					 StatsPrintOut(id, pkt_rep_name);
			         printf ("[statsCmd]:: Generate a packet report for node %d with the name of $GINI_HOME/%s%s.\n",id, STATS_REPORT_DIRECTORY, filename);
				}
				else if (!strcmp(pchToken, ">")) {
					if ((pchToken = strtok(NULL, " \n")) == NULL) {
						printf ("[statsCmd]:: missing parameters.. type 'help stats' for usage.\n");
						return;
					}
					else	{
						if (IsFileValid(pchToken) == FALSE) {
							printf ("[statsCmd]:: Invalid destination file name for the packet report!\n");
							return;
						}
						StatsComp(id);
						StatsPrintOut(id, pchToken);
						//FileSeqArray[id-1] += 1;
						printf ("[statsCmd]:: Generate a packet report for node %d with the name of %s!\n",id, pchToken);
					}
				}
				else {
					printf ("[sysCmd]:: command not found.. type 'help sys' for usage.\n");
					return;
				}
			   return;
			}
			else {
				printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
				return;
			}
		}
		else {
			printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
			return;
		}
	}
	else {
       printf ("[statsCmd]:: command not found.. type 'help stats' for usage.\n");
       return;
	}
}



