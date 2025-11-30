
Flexscript sample to test
```
Object source = Object.create("Source");
source.setLocation(0, 1, 0);
Object processor = Object.create("Processor");
processor.setLocation(3, 1, 0);
Object queue1 = Object.create("Queue");
Object queue2 = Object.create("Queue");
queue1.setLocation(9, 1, 0);
queue2.setLocation(9, -2, 0);

// Assign Round Robin code to Send To Port field
string sendToPortCode = "/**Custom Code*/ \
Object item = param(1); \
Object current = ownerobject(c); \
treenode curlabel = current.labels.assert(\"f_cursendport\", 1); \
\
if (getoutput(current) == 0 && item.rank == 1)   \
	current.f_cursendport = 1; \
\
double returnvalue = curlabel.value; \
curlabel.value += 1; \
if (curlabel.value > current.outObjects.length) \
	current.f_cursendport = 1; \
\
return  returnvalue;";

processor.setProperty("SendToPort", sendToPortCode);
contextdragconnection(source, processor, "A");
contextdragconnection(processor, queue1, "A");
contextdragconnection(processor, queue2, "A");
```