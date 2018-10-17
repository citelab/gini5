/*
 * NAME: antenna.c 
 * FUNCTION: Collection of functions in antenna module
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  antenna.c
//======================================================= 
 #include "antenna.h"

//=======================================================
//       Function Part
//======================================================= 

//=======================================================
//       FUNCTION: IniNodeAntenna
//       PURPOSE:  Initialize the node antenna. 
//======================================================= 
void IniNodeAntenna(NodeType type) {
   int id;
   if (prog_verbosity_level()==2){
       printf("[IniNodeAntenna]:: Initializing antenna module ... ");
   }	
   if (type == NORMAL) {
		for ( id=1; id<=TotNodeNo; id++) {	
	   			WGNnode(id)->nodePhy->nodeAntenna = (NodeAntenna *)malloc(sizeof(NodeAntenna));
				if( WGNnode(id)->nodePhy->nodeAntenna == NULL ){
					printf("[IniNodeAntenna]:: nodeAntenna malloc error.\n");
					exit(1);
		        }
				SetAntType(WGNnode(id));
				SetAntGain(WGNnode(id));
				SetAntHeight(WGNnode(id));
				SetAntSysLos(WGNnode(id));    
				WGNnode(id)->nodePhy->nodeAntenna->intPwr = 0;              
			    WGNnode(id)->nodePhy->nodeAntenna->jamInt = 0;
		}
   }
   if (prog_verbosity_level()==2){
	   printf("[ OK ]\n");
   }
}

//=======================================================
//       FUNCTION: FinalizeNodeAntenna
//======================================================= 
void FinalizeNodeAntenna(NodeType type) {
   int id;
   if (prog_verbosity_level()==2){
       printf("[FinalizeNodeAntenna]:: Finalizing antenna module ... ");
   }
   if (type == NORMAL) {
		for ( id=1; id<=TotNodeNo; id++) {	
	   			free(WGNnode(id)->nodePhy->nodeAntenna);
		}
   }
   if (prog_verbosity_level()==2){
       printf("[ OK ].\n");
   }
}

//=======================================================
//       FUNCTION: SetAntType
//       PURPOSE:  Set the type of the antenna of the node. 
//======================================================= 
void SetAntType( MobileNode *node ) {
  if (node->nodeType == NORMAL) {
	  node->nodePhy->nodeAntenna->AntType = AntTypeArray[(node->Id)-1];
  } 
  /*else if (node->nodeType == AP) {
	  node->nodePhy->nodeAntenna->AntType = APAntTypeArray[(node->Id)-1];
  }*/
  if (((node->nodePhy->nodeAntenna->AntType)!=OmniDirectionalAnt) &&
	  ((node->nodePhy->nodeAntenna->AntType)!=SwitchedBeamAnt) &&
	  ((node->nodePhy->nodeAntenna->AntType)!=AdaptiveArrayAnt)) {
      printf ("[SetAntType]:: Error, Unrecognized Antenna type.");
	  exit (1);
  }
}

//=======================================================
//       FUNCTION: SetAntGain
//       PURPOSE:  Set the gain of the antenna of the node. 
//======================================================= 
void SetAntGain( MobileNode *node ) {
  if ( node->nodePhy->nodeAntenna->AntType == OmniDirectionalAnt ) {
	   node->nodePhy->nodeAntenna->Gain_dBi =1.0;
	}
	else if ( node->nodePhy->nodeAntenna->AntType == SwitchedBeamAnt ) {
	   printf ("[SetAntGain]:: SwitchedBeamAnt not implemented yet.\n");
	   exit (1);
	}
    else if ( node->nodePhy->nodeAntenna->AntType == AdaptiveArrayAnt ) {
	   printf ("[SetAntGain]:: AdaptiveArrayAnt not implemented yet.\n");
	   exit (1);
	}
	else {
       printf ("[SetAntGain]:: Unrecognized Antenna type.\n");
	   exit (1);
	}		
}

//=======================================================
//       FUNCTION: SetAntHeight
//       PURPOSE:  Set the height of the antenna of the node. 
//======================================================= 
void SetAntHeight( MobileNode *node )
{ 
  if (node->nodeType == NORMAL) {
	  node->nodePhy->nodeAntenna->Height = AntHeightArray[(node->Id)-1];
  } 
  /*else if (node->nodeType == AP) {
	  node->nodePhy->nodeAntenna->Height = APAntHeightArray[(node->Id)-1];
  }*/   
  if ( (node->nodePhy->nodeAntenna->Height) <= 0 ) {
	   printf ("[SetAntHeight]:: Height of antenna can not be less than zero.\n");
	   exit (1);
  }	
}

//=======================================================
//       FUNCTION: SetAntSysLos
//       PURPOSE:  Set the system loss of the antenna of the node. 
//======================================================= 
void SetAntSysLos( MobileNode *node )
{ 
  if (node->nodeType == NORMAL) {
	  node->nodePhy->nodeAntenna->SysLoss = AntSysLosArray[(node->Id)-1];
  } 
  /*else if (node->nodeType == AP) {
	  node->nodePhy->nodeAntenna->SysLoss = APAntSysLosArray[(node->Id)-1];
  }*/      
}


//=======================================================
//       FUNCTION: GetAntType
//       PURPOSE:  Get the type of the antenna of the node. 
//======================================================= 
Antenna_type GetAntType( MobileNode *node )
{ 
   return (node->nodePhy->nodeAntenna->AntType);
}

//=======================================================
//       FUNCTION: GetAntGain
//       PURPOSE:  Get the gain of the antenna of the node. 
//======================================================= 
double GetAntGain( MobileNode *node )
{
   return (node->nodePhy->nodeAntenna->Gain_dBi);
}

//=======================================================
//       FUNCTION: GetAntHeight
//       PURPOSE:  Get the height of the antenna of the node. 
//======================================================= 
double GetAntHeight( MobileNode *node )
{ 
   return (node->nodePhy->nodeAntenna->Height);
}

//=======================================================
//       FUNCTION: GetAntSysLos
//       PURPOSE:  Get the system loss of the antenna of the node. 
//======================================================= 
double GetAntSysLos( MobileNode *node )
{ 
   return (node->nodePhy->nodeAntenna->SysLoss); 
}
