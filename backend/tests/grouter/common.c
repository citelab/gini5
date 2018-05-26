simplequeue_t *outputQ, *workQ, *openflowWorkQ, *qtoa;
outputQ = createSimpleQueue("outputQueue", INFINITE_Q_SIZE, 0, 1);
workQ = createSimpleQueue("work Queue", INFINITE_Q_SIZE, 0, 1);
openflowWorkQ = createSimpleQueue("Work queue for OpenFlow", INFINITE_Q_SIZE, 0, 1);
GNETInit(0, "", "test", outputQ);
ARPInit();
IPInit();
classifier = createClassifier();
filter = createFilter(classifier, 0);
