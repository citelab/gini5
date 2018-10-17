/*
 * NAME: mobility.c 
 * FUNCTION: Collection of functions to emulate the node movement. 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 * NOTE:   The algorithm of the "RandomWayPoint" is written by taking J-sim 
 *              as reference. 
 */

//=======================================================
//       File Name :  mobility.c
//======================================================= 
  #include "mobility.h"

//=======================================================
//       FUNCTION:  PrintMobility
//       PURPOSE:   Record the node mobility
//=======================================================  
void PrintMobility(char *FILENAME, double x, double y, double z) { 
  FILE* in;  
  in = fopen(FILENAME, "a+");

  if(in==NULL) {
     printf("[PrintMobility]:: Error, can't create file.\n");
     return;
  }
  
  fprintf (in, "The coordinator is:  %f   %f   %f", x,y,z);
  fprintf (in, "\n");
  
  fclose(in);
}	  

//=======================================================
//       FUNCTION:  DisComp
//       PURPOSE:   Compute the distance between two points
//======================================================= 
double DistComp(NodePosition *Pos_1, NodePosition *Pos_2) {
	double dX,dY,dZ;      //  the coordinator difference between the two points
	double dist;
	
	//here we assume that the location of the mobile node 
	//is the same as the corresponding antenna!
	dX = Pos_1->x - Pos_2->x;
	dY = Pos_1->y - Pos_2->y;
	dZ = Pos_1->z - Pos_2->z;
	
	/*compute the distance between two points*/
	dist = sqrt(dX * dX + dY * dY + dZ * dZ);

	return(dist);
}

//=======================================================
//       FUNCTION: SetMovStrPtr
//       PURPOSE:  Set the movStrPtr of the node based on the mobility 
//                             type when Initialize the node's mobility parameters.
//======================================================= 
  void SetMovStrPtr(MobileNode *node) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       ((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->MovChSign = TRUE;
       ((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->EndSign = FALSE;
	   ((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->UpdateTimeUnit 
	   = SYS_INFO->time_info->Mob_timeunit;
    }
    else if (mobtype == TrajectoryBased) {     
	   printf ("[SetMovStrPtr]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[SetMovStrPtr]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
        printf ("[SetMovStrPtr]:: Unrecongnized mobility type.\n");
		exit (1);
	}
  }

//=======================================================
//       FUNCTION: SetAPPos
//       PURPOSE:  Set the AP position based on the mobility type.
//======================================================= 
  void SetAPPos(MobileNode *node) {
    RWP_SetAPPos(node);
  }

//=======================================================
//       FUNCTION: SetStartPointLoc
//       PURPOSE:  Set the movStrPtr of the node based on the mobility 
//======================================================= 
  void SetStartPointLoc(MobileNode *node) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       RWP_SetStartPointLoc(node);
    }
    else if (mobtype == TrajectoryBased) {     
	   printf ("[SetStartPointLoc]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[SetStartPointLoc]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
       printf ("[SetStartPointLoc]:: Unrecongnized mobility type.\n");
	   exit (1);
	}
  }

//=======================================================
//       FUNCTION:  IniNodeCurLoc
//       PURPOSE:   Set current location for the node when the first time to 
//                              move.
//======================================================= 
   void IniNodeCurLoc(MobileNode *node) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       return (RWP_IniNodeCurLoc(node));
    }
    else if (mobtype == TrajectoryBased) {    
	   printf ("[IniNodeCurLoc]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[IniNodeCurLoc]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
        printf ("[IniNodeCurLoc]:: Unrecongnized mobility type.\n");
		exit (1);
	}
  }

//=======================================================
//       FUNCTION: SetNodeSpd
//       PURPOSE:  Set the movStrPtr of the node based on the mobility 
//                             type.
//======================================================= 
  void SetNodeSpd(MobileNode *node) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       RWP_SetNodeSpd(node);
    }
    else if (mobtype == TrajectoryBased) {     
	   printf ("[SetNodeSpd]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[SetNodeSpd]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
       printf ("[SetNodeSpd]:: Unrecongnized mobility type.\n");
	   exit (1);
	}
  }

//=======================================================
//       FUNCTION:  GetEndSign
//       PURPOSE:   Get the EndSign of the movStrPtr of the node based 
//                              on the mobility type.
//======================================================= 
   WGNflag GetEndSign(MobileNode *node) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       return (RWP_GetEndSign(node));
    }
    else if (mobtype == TrajectoryBased) {    
	   printf ("[GetEndSign]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[GetEndSign]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
        printf ("[GetEndSign]:: Unrecongnized mobility type.\n");
		exit (1);
	}
  }

//=======================================================
//       FUNCTION:  SetEndSign
//       PURPOSE:   Set the EndSign of the movStrPtr of the node based 
//                              on the mobility type.
//======================================================= 
   void SetEndSign(MobileNode *node, WGNflag flag) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       RWP_SetEndSign(node,flag);
    }
    else if (mobtype == TrajectoryBased) {    
	   printf ("[SetEndSign]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[SetEndSign]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
        printf ("[SetEndSign]:: Unrecongnized mobility type.\n");
		exit (1);
	}
  }

//=======================================================
//       FUNCTION: IniNodeMobility
//       PURPOSE:  Initialize the mobility parameters of all nodes. 
//======================================================= 
  void IniNodeMobility(NodeType type) {
    int i;
    if (prog_verbosity_level()==2){
        printf("[IniNodeMobility]:: Initializing mobility module ... ");
    }	
    if (type == NORMAL) {
	for ( i=0; i<TotNodeNo; i++)
    {  
	   	  WGNnode(i+1)->nodePhy->nodeMobility =
		  (NodeMobility *)malloc(sizeof(NodeMobility));
		  if( WGNnode(i+1)->nodePhy->nodeMobility == NULL ){
		  printf("[IniMobNode]:: nodeMobility malloc error");
		  exit(1);
		  }
          /*malloc for  movStrPtr*/
		  if (MobilityTypeArray[i] == RandomWayPoint) {
			 WGNnode(i+1)->nodePhy->nodeMobility->movStrPtr =
		     (RWP_StrPtr *)malloc(sizeof(RWP_StrPtr)); 
			 if( WGNnode(i+1)->nodePhy->nodeMobility->movStrPtr == NULL ){
		     printf("[IniMobNode]:: RWP_StrPtr malloc error");
		     exit(1);
			 }
		  }
          else if (MobilityTypeArray[i] == TrajectoryBased) {
             printf ("[IniMobNode]:: TrajectoryBased is not implemented at this moment.\n");
	         exit (1); 
          }
		  else if (MobilityTypeArray[i] == Manual) {
             printf ("[IniMobNode]:: Manual is not implemented at this moment.\n");
	         exit (1); 
		  }
		  else {
			 printf ("[IniMobNode]:: Unrecongnized mobility type.\n");
		     exit (1);
		  }
		  /*malloc for  srcPosition*/
		  WGNnode(i+1)->nodePhy->nodeMobility->srcPosition =
		  (NodePosition *)malloc(sizeof(NodePosition));
		  if( WGNnode(i+1)->nodePhy->nodeMobility->srcPosition == NULL ){
		  printf("[IniMobNode]:: srcPosition malloc error");
		  exit(1);
		  }
		  /*malloc for  dstPosition*/
		  WGNnode(i+1)->nodePhy->nodeMobility->dstPosition =
		  (NodePosition *)malloc(sizeof(NodePosition));
		  if( WGNnode(i+1)->nodePhy->nodeMobility->dstPosition == NULL ){
		  printf("[IniMobNode]:: dstPosition malloc error");
		  exit(1);
		  }
		  /*malloc for  curPosition*/
		  WGNnode(i+1)->nodePhy->nodeMobility->curPosition =
		  (NodePosition *)malloc(sizeof(NodePosition));
		  if( WGNnode(i+1)->nodePhy->nodeMobility->curPosition == NULL ){
		  printf("[IniMobNode]:: curPosition malloc error");
		  exit(1);
		  }
		  /*malloc for   nodeSpd*/
		  WGNnode(i+1)->nodePhy->nodeMobility->nodeSpd =
		  (NodeSpd *)malloc(sizeof(NodeSpd));
		  if( WGNnode(i+1)->nodePhy->nodeMobility->srcPosition == NULL ){
		  printf("[IniMobNode]:: nodeSpd malloc error");
		  exit(1);
	      }      
       	  
		  WGNnode(i+1)->nodePhy->nodeMobility->mov_rep_name = NULL;
	      WGNnode(i+1)->nodePhy->nodeMobility->mobilityType = MobilityTypeArray[i];
	      SetMovStrPtr(WGNnode(i+1));                    //chose the movement structure ptr based on the type
	      SetStartPointLoc(WGNnode(i+1));              //set the start location of the node
	      IniNodeCurLoc(WGNnode(i+1));                 //set the current loc to be the same as the src loc.
	      WGNnode(i+1)->nodePhy->nodeMobility->MaxSpd = MaxSpdArray[i];
          WGNnode(i+1)->nodePhy->nodeMobility->MinSpd = MinSpdArray[i];
    }
	}//end of if
	if (prog_verbosity_level()==2){
		printf("[ OK ]\n");
	}
  }

//=======================================================
//       FUNCTION: FinalizeNodeMobility
//======================================================= 
  void FinalizeNodeMobility(NodeType type) {
    int i;
	if (prog_verbosity_level()==2){
	    printf("[FinalizeNodeMobility]:: Finalizing mobility module ... ");
    }
	if (type == NORMAL) {
		for ( i=0; i<TotNodeNo; i++) {  
			    SetEndSign(WGNnode(i+1), TRUE); 
				free(WGNnode(i+1)->nodePhy->nodeMobility->movStrPtr);
				free(WGNnode(i+1)->nodePhy->nodeMobility->srcPosition);
				free(WGNnode(i+1)->nodePhy->nodeMobility->dstPosition);
				free(WGNnode(i+1)->nodePhy->nodeMobility->curPosition);
				free(WGNnode(i+1)->nodePhy->nodeMobility->nodeSpd);
				free(WGNnode(i+1)->nodePhy->nodeMobility);
		}
	}
	if (prog_verbosity_level()==2){
         printf("[ OK ]\n");
	}
  }

//=======================================================
//       FUNCTION:   MobilityUpdate
//       PURPOSE:    Update the mobility parameters of the node.
//======================================================= 
   void MobilityUpdate(MobileNode *node) {
    Mobility_type mobtype;
	mobtype = node->nodePhy->nodeMobility->mobilityType;
    if (mobtype == RandomWayPoint) {
       // the node will continue to move
	   if (GetEndSign(node) == FALSE)
       {  
		  // start a new sub movement
          if (RWP_GetMovChSign(node) == TRUE){
             RWP_SetEndPointLoc(node);
			 SetNodeSpd(node);
			 if (GetRayleighSign() == ON) {
				 UpdateIcrMatrix(node->Id); //change the fading para which is related to the speed of the node
		     }				 
			 RWP_SetMovChSign(node, FALSE);
			 RWP_UpdatePosition(node);  
          }
		  else {
			 RWP_UpdatePosition(node);
		  }
       } //end of if (GetEndSign(node) == FALSE)
	   else
		   return;
    }
    else if (mobtype == TrajectoryBased) {    
	   printf ("[MobilityUpdate]:: TrajectoryBased is not implemented at this moment.\n");
	   exit (1); 
    }
    else if (mobtype == Manual) {
       printf ("[MobilityUpdate]:: Manual is not implemented at this moment.\n");
	   exit (1); 
	}
    else {
        printf ("[MobilityUpdate]:: Unrecongnized mobility type.\n");
		exit (1);
	}
  }

//=======================================================
//       FUNCTION: MobilityProcess
//       PURPOSE:  Process the procedures over all the running time of the 
//                             program. 
//======================================================= 
  void MobilityProcess() {
	  int i;
		  //int j;
	  for (i=0; i<TotNodeNo; i++){
	      if ((GetPowSwitch(WGNnode(i+1)) == ON)&&(GetEndSign(WGNnode(i+1)) == FALSE)) 
              MobilityUpdate(WGNnode(i+1));
      }//end of for   
  }

                /*====================================*/
                /*       RandomWayPoint mode FUNCTIONS       */
                /*====================================*/
				
//=======================================================
//       FUNCTION: RWP_SetAPPos (RandomWayPoint mode)
//       PURPOSE:  Set the location for the Acess Point.
//======================================================= 
  void RWP_SetAPPos(MobileNode *AP) {
      AP->nodePhy->nodeMobility->curPosition->x = (double)SYS_INFO->map_info->x_width / 2;
      AP->nodePhy->nodeMobility->curPosition->y = (double)SYS_INFO->map_info->y_width / 2;
      AP->nodePhy->nodeMobility->curPosition->z = (double)SYS_INFO->map_info->z_width / 2;  
	  AP->nodePhy->nodeMobility->srcPosition->x = (double)SYS_INFO->map_info->x_width / 2;
      AP->nodePhy->nodeMobility->srcPosition->y = (double)SYS_INFO->map_info->y_width / 2;
      AP->nodePhy->nodeMobility->srcPosition->z = (double)SYS_INFO->map_info->z_width / 2;          
	  AP->nodePhy->nodeMobility->dstPosition->x = (double)SYS_INFO->map_info->x_width / 2;
      AP->nodePhy->nodeMobility->dstPosition->y = (double)SYS_INFO->map_info->y_width / 2;
      AP->nodePhy->nodeMobility->dstPosition->z = (double)SYS_INFO->map_info->z_width / 2;          
  }

//=======================================================
//       FUNCTION: RWP_SetNodeRanSrcLoc (RandomWayPoint mode)
//       PURPOSE:  Generate the random src location for the mobile node.
//======================================================= 
  void RWP_SetStartPointLoc(MobileNode *node) {
      node->nodePhy->nodeMobility->srcPosition->x = UnitUniform() * SYS_INFO->map_info->x_width;
      node->nodePhy->nodeMobility->srcPosition->y = UnitUniform() * SYS_INFO->map_info->y_width;
      node->nodePhy->nodeMobility->srcPosition->z = UnitUniform() * SYS_INFO->map_info->z_width;              
  }

//=======================================================
//       FUNCTION: RWP_SetNodeRanDstLoc (RandomWayPoint mode)
//       PURPOSE:  Generate the random dst location for the mobile node.
//======================================================= 
  void RWP_SetNodeRanDstLoc(MobileNode *node) {
      node->nodePhy->nodeMobility->dstPosition->x = UnitUniform() * SYS_INFO->map_info->x_width;
      node->nodePhy->nodeMobility->dstPosition->y = UnitUniform() * SYS_INFO->map_info->y_width;
      node->nodePhy->nodeMobility->dstPosition->z = UnitUniform() * SYS_INFO->map_info->z_width;              
  }

//=======================================================
//       FUNCTION: RWP_NodeSrcDstIsSame (RandomWayPoint mode)
//       PURPOSE:  To tell if the src and the dst of the node is the same. 
//======================================================= 
  WGNflag RWP_NodeSrcDstIsSame(MobileNode *node){
      
	  double dstX,srcX,dstY,srcY,dstZ,srcZ;
	  
	  srcX = node->nodePhy->nodeMobility->srcPosition->x;
	  srcY = node->nodePhy->nodeMobility->srcPosition->y;
	  srcZ = node->nodePhy->nodeMobility->srcPosition->z;
	  dstX = node->nodePhy->nodeMobility->dstPosition->x;
      dstY = node->nodePhy->nodeMobility->dstPosition->y;
	  dstZ = node->nodePhy->nodeMobility->dstPosition->z;

      if ((srcX==dstX)&&(srcY==dstY)&&(srcZ==dstZ))
           return TRUE;
	  else 
		   return FALSE;
  }

//=======================================================
//       FUNCTION: RWP_SetEndPointLoc
//       PURPOSE:  Set the node postion.
//======================================================= 
  void RWP_SetEndPointLoc(MobileNode *node) {
      WGNflag temp;
      temp = TRUE;

	  while (temp==TRUE) {
	        RWP_SetNodeRanDstLoc(node);
			temp = RWP_NodeSrcDstIsSame(node);
	  }
 } 

//=======================================================
//       FUNCTION: RWP_IniNodeCurLoc (RandomWayPoint mode)
//       PURPOSE:  Initialize the current location of the mobile node.
//======================================================= 
  void RWP_IniNodeCurLoc(MobileNode *node) {
      node->nodePhy->nodeMobility->curPosition->x = node->nodePhy->nodeMobility->srcPosition->x;
      node->nodePhy->nodeMobility->curPosition->y = node->nodePhy->nodeMobility->srcPosition->y;
      node->nodePhy->nodeMobility->curPosition->z = node->nodePhy->nodeMobility->srcPosition->z; 
  }


//=======================================================
//       FUNCTION: RWP_SetNodeSpd (RandomWayPoint mode)
//       PURPOSE:  Set the speed for the mobile node including the total spd
//                             and those on three-axles.
//======================================================= 
  void RWP_SetNodeSpd(MobileNode *node) {
	  double temp;
	  double dist;
	  double dx,dy,dz;
	  double dstX,srcX,dstY,srcY,dstZ,srcZ;
	  double speed;
	  double minspd,maxspd;
	  //temp = 0;
	  maxspd = node->nodePhy->nodeMobility->MaxSpd;
	  minspd = node->nodePhy->nodeMobility->MinSpd;
	  srcX = node->nodePhy->nodeMobility->srcPosition->x;
	  srcY = node->nodePhy->nodeMobility->srcPosition->y;
	  srcZ = node->nodePhy->nodeMobility->srcPosition->z;
	  dstX = node->nodePhy->nodeMobility->dstPosition->x;
      dstY = node->nodePhy->nodeMobility->dstPosition->y;
	  dstZ = node->nodePhy->nodeMobility->dstPosition->z;
	  
      temp = UnitUniform();
      speed = minspd + temp*(maxspd-minspd);
     
	  // Calculate the T-R distance
      dist = DistComp(node->nodePhy->nodeMobility->srcPosition, node->nodePhy->nodeMobility->dstPosition);
	  dx = dstX - srcX;
      dy = dstY - srcY;
      dz = dstZ - srcZ;
      
	  // Calculate the speed in each direction.
	  if ( RWP_NodeSrcDstIsSame(node) == FALSE ) {
            node->nodePhy->nodeMobility->nodeSpd->spd_x = dx/dist*speed;
            node->nodePhy->nodeMobility->nodeSpd->spd_y = dy/dist*speed;
            node->nodePhy->nodeMobility->nodeSpd->spd_z = dz/dist*speed;
			node->nodePhy->nodeMobility->nodeSpd->spd_tot = speed;
      }
	  else {
            printf ("[SetNodeSpd]:: The src node location should not be the same as that of the dst node.\n");
		    exit (1); 
	  }    
  }

//=======================================================
//       FUNCTION: RWP_UpdatePosition (RandomWayPoint mode)
//       PURPOSE:  Update the current position of the node after a period &
//                             set the MovChSign.
//======================================================= 
   void RWP_UpdatePosition(MobileNode *node) {       
	    double spd_x,spd_y,spd_z;
	    double dstX,curX,dstY,curY,dstZ,curZ;
		double interval;

		if (PrintMovArray[node->Id-1] == TRUE) {
			chdir(getenv("GINI_HOME"));
		    PrintMobility(node->nodePhy->nodeMobility->mov_rep_name, node->nodePhy->nodeMobility->curPosition->x,node->nodePhy->nodeMobility->curPosition->y,node->nodePhy->nodeMobility->curPosition->z);
        }

		//interval = 1;
		interval = ((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr)) -> UpdateTimeUnit;
	  
	    dstX = node->nodePhy->nodeMobility->dstPosition->x;
        dstY = node->nodePhy->nodeMobility->dstPosition->y;
	    dstZ = node->nodePhy->nodeMobility->dstPosition->z;
		spd_x = node->nodePhy->nodeMobility->nodeSpd->spd_x;
        spd_y = node->nodePhy->nodeMobility->nodeSpd->spd_y;
        spd_z = node->nodePhy->nodeMobility->nodeSpd->spd_z;
        
		if ( interval == 0.0 )  return;
        
		/*update the current position of the node first*/
        (node->nodePhy->nodeMobility->curPosition->x) = 
		(node->nodePhy->nodeMobility->curPosition->x) + 
		(node->nodePhy->nodeMobility->nodeSpd->spd_x) * interval;
        
		(node->nodePhy->nodeMobility->curPosition->y) = 
		(node->nodePhy->nodeMobility->curPosition->y) + 
		(node->nodePhy->nodeMobility->nodeSpd->spd_y) * interval;

		(node->nodePhy->nodeMobility->curPosition->z) = 
		(node->nodePhy->nodeMobility->curPosition->z) + 
		(node->nodePhy->nodeMobility->nodeSpd->spd_z) * interval;

	    curX = node->nodePhy->nodeMobility->curPosition->x;
        curY = node->nodePhy->nodeMobility->curPosition->y;
	    curZ = node->nodePhy->nodeMobility->curPosition->z;

        // adjust the position if it exceed the destination point & set the MovChSign
		// set the MovChSign to TRUE to continue another movement if the node 
		//arrive the dst point.
        if ((spd_x > 0 && curX > dstX) || (spd_x < 0 && curX < dstX)) {  
			node->nodePhy->nodeMobility->curPosition->x = dstX;
			node->nodePhy->nodeMobility->curPosition->y = dstY;
			node->nodePhy->nodeMobility->curPosition->z = dstZ; 
			node->nodePhy->nodeMobility->srcPosition->x = dstX;
			node->nodePhy->nodeMobility->srcPosition->y = dstY;
			node->nodePhy->nodeMobility->srcPosition->z = dstZ; 
			((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->MovChSign = TRUE;
		    }	
    }

//=======================================================
//       FUNCTION: RWP_GetMovChSign (RandomWayPoint mode)
//       PURPOSE:  Get the MovChSign of the node. 
//======================================================= 
   WGNflag RWP_GetMovChSign(MobileNode *node) {       
		return (((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->MovChSign);
 }

//=======================================================
//       FUNCTION: RWP_SetMovChSign (RandomWayPoint mode)
//       PURPOSE:  Set the MovChSign of the node. 
//======================================================= 
   void RWP_SetMovChSign(MobileNode *node, WGNflag flag) {       
		((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->MovChSign = flag;
 }

//=======================================================
//       FUNCTION: RWP_GetEndSign (RandomWayPoint mode)
//       PURPOSE:  Get the EndSign of the node. 
//======================================================= 
   WGNflag RWP_GetEndSign(MobileNode *node) {       
		return (((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->EndSign);
 }

//=======================================================
//       FUNCTION: RWP_SetEndSign (RandomWayPoint mode)
//       PURPOSE:  Set the EndSign of the node. 
//======================================================= 
   void RWP_SetEndSign(MobileNode *node, WGNflag flag) {       
	   ((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->EndSign = flag;
 }

//=======================================================
//       FUNCTION: MovResume
//======================================================= 
   void MovResume(MobileNode *node) {       
		node->nodePhy->nodeMobility->dstPosition->x = node->nodePhy->nodeMobility->curPosition->x;
		node->nodePhy->nodeMobility->dstPosition->y = node->nodePhy->nodeMobility->curPosition->y;
		node->nodePhy->nodeMobility->dstPosition->z = node->nodePhy->nodeMobility->curPosition->z; 
		node->nodePhy->nodeMobility->srcPosition->x = node->nodePhy->nodeMobility->curPosition->x;
		node->nodePhy->nodeMobility->srcPosition->y = node->nodePhy->nodeMobility->curPosition->y;
		node->nodePhy->nodeMobility->srcPosition->z = node->nodePhy->nodeMobility->curPosition->z; 
		((RWP_StrPtr *)(node->nodePhy->nodeMobility->movStrPtr))->MovChSign = TRUE;
 }

//=======================================================
//       FUNCTION: MovStop
//======================================================= 
   void MovStop(MobileNode *node) {       
		node->nodePhy->nodeMobility->nodeSpd->spd_x = 0;
		node->nodePhy->nodeMobility->nodeSpd->spd_y = 0;
		node->nodePhy->nodeMobility->nodeSpd->spd_z = 0;
		node->nodePhy->nodeMobility->nodeSpd->spd_tot = 0;
		if (GetRayleighSign() == ON) {
    		UpdateIcrMatrix(node->Id); 
		}		
 }
