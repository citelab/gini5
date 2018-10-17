//=======================================================
//       File Name :  stats.h
//======================================================= 
#ifndef __STATS_H_
#define __STATS_H_

 #include <stdio.h>
 #include <stdio.h>      
 #include <sys/socket.h>
 #include <arpa/inet.h>
 #include <stdlib.h>     
 #include <string.h>    
 #include <unistd.h>     
 #include <math.h>
 #include <pthread.h>
  
 #include "gwcenter.h"
 #include "event.h"
 #include "errmodel.h"
 #include "wcard.h"

 char pkt_rep_name[MAX_REPORT_NAME_LEN];
 
 void IniNodeStats(NodeType type);
 void FinalizeNodeStats(NodeType type);
 void StatsPrintOut(int id, char* file);
 void StatsComp(int id);
 void ResetStats(int id);
 void FileNameGen(int id, char* type, char* filename);
 WGNflag IsFileValid(char* filename);

 #endif
