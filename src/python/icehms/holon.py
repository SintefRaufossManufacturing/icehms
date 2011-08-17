"""
This file define the main holon classes
BaseHolon implement the minim methods necessary for communication with other holons
LightHolons adds helper methods to handle message, topics and events
Holon adds a main thread to LightHolon
"""



from threading import Thread, Lock
from copy import copy
from time import sleep, time
import uuid

import Ice 


from icehms import hms
from icehms.logger import Logger




class BaseHolon(hms.Holon):
    """
    Base holon only implementing registration to ice
    and some default methods called by AgentManager
    """
    def __init__(self, name=None, logLevel=3):
        if not name:
            name = self.__class__.__name__ + "_" + str(uuid.uuid1())
        self.name = name
        self.logger = Logger(self, self.name, logLevel)
        self._icemgr = None
        self.registeredToGrid = False
        self._agentMgr = None
        self.proxy = None

    def getName(self, ctx=None): # we may override method from Thread but I guess it is fine
        return self.name

    def setAgentManager(self, mgr): 
        """
        Set agent manager object for a holon. keeping a pointer enable us create other holons 
        also keep a pointer to icemgr
        """
        self._agentMgr = mgr
        self._icemgr = mgr.icemgr
        self.logger.icemgr = self._icemgr

    def cleanup(self):
        """
        Call by agent manager when deregistering
        """

    def start(self, current=None):
        """ 
        Call by Agent manager after registering
        """
        self._log("Starting" )
                
    def stop(self, current=None):
        """ 
        Call by agent manager before deregistering
        """
        self._ilog("stop called ")


    def shutdown(self, ctx=None):
        """
        shutdown a holon, deregister from icegrid and icestorm and call stop() and cleanup on holon instances
        I read somewhere this should notbe available in a MAS, holons should only shutdown themselves
        """
        try:
            self._agentMgr.removeAgent(self)
        except Ice.Exception, why:
            self._ilog(why)

    def getClassName(self, ctx=None):
        return self.__class__.__name__

    def _log(self, msg, level=6):
        """
        Log to enabled log channels
        """
        return self.logger.log(msg, level)

    def _ilog(self, *args, **kwargs):
        """
        format everything to string before logging
        """
        return self.logger.ilog(*args, **kwargs)

    def setLogLevel(self, level):
        """
        maybe should be deprecated, use Agent.logger.setLogLevel
        """
        self.logger.setLogLevel(level)


class LegacyMethods:
    """
    All legacy methods are moved in this class to reduce amount of visble code in Holon
    """
    # pylint: disable-msg=E1101
    def subscribeTopic(self, topicName):
        self._log("Call to deprecated method Holon.subscribeTopic, use Holon._subscribeTopic", 2)
        return self._subscribeTopic(topicName)

    def getPublisher(self, topicName, prxobj, permanentTopic=True):
        self._log("Call to deprecated method Holon.getPublisher, use Holon._getPublisher", 2)
        return self._getPublisher(topicName, prxobj, permanentTopic)

    def unsubscribeTopic(self, name):
        self._log("Call to deprecated method Holon.unsubscribeTopic, use Holon._unsubscribeTopic", 2)
        return self._unsubscribeTopic(name)
  
    def isRunning(self, current=None):
        """
        Return True if thread runnnig
        Since some agents do not need threads, it might return False even if everythig is fine
        """
        return self.isAlive()

    def log(self, *args):
        """
        keep backward compatibility
        """
        self._log("Call to deprecated method self.log, please use self._log")
        return self._log(*args)


    def getProxy(self, name):
        self._log( "Call to deprecated method Holon.getProxy", 2)
        self._log( "Use IceManager.getProxy", 2)
        return self._icemgr.getHolon(name)
 
    def findAllObjectsByType(self, icetype):
        self._log( "Call to deprecated method Holon.findAllObjectsByType", 2)
        self._log( "Use IceManager.findHolons", 2)
        return self._icemgr.findHolons(icetype)
    
    def getProxyBlocking(self, name):
        self._log( "Call to deprecated method Holon.getProxyBlocking", 2)
        self._log( "Use Holon._getProxyBlocking", 2)
        return self._getProxyBlocking(name)


    def getState(self, current=None):
        """ default implementation of a getState
        should be re-imlemented in all clients
        """
        self._log("Call to default state method is deprecated, please fix caller")
        ans = []
        for msg in self.mailbox.copy():
            ans.append(msg.body)
        return ans





class LightHolon(BaseHolon, hms.GenericEventInterface, LegacyMethods):
    """Base Class for non active Holons or holons setting up their own threads
    implements helper methods like to handle topics, messages and events 
    """
    def __init__(self, name=None, logLevel=3):
        BaseHolon.__init__(self, name, logLevel)
        self._publishedTopics = {} 
        self._subscribedTopics = {}
        self.mailbox = MessageQueue()


    def _subscribeEvent(self, topicName):
        self._subscribeTopic(topicName, server=self._icemgr.eventMgr)

    def _subscribeTopic(self, topicName, server=None):
        """
        subscribe ourself to a topic using safest ice tramsmition protocol
        The holon needs to inherit the topic proxy and implemented the topic methods
        """
        topic = self._icemgr.subscribeTopic(topicName, self.proxy.ice_twoway(), server=server)
        self._subscribedTopics[topicName] = topic
        return topic

    def _subscribeTopicUDP(self, topicName):
        """
        subscribe ourself to a topic, using UDP
        The holon needs to inherit the topic proxy and implemented the topic methods
        """
        topic = self._icemgr.subscribeTopic(topicName, self.proxy.ice_datagram())
        self._subscribedTopics[topicName] = topic
        return topic


    def _getPublisher(self, topicName, prxobj, permanentTopic=True, server=None):
        """
        get a publisher object for a topic
        create it if it does not exist
        prxobj is the ice interface obj for the desired topic. This is necessary since topics have an interface
        if permanentTopic is False then we destroy it when we leave
        otherwise it stays
        if server is None then default server is used
        """
        pub = self._icemgr.getPublisher(topicName, prxobj, server=server)
        self._publishedTopics[topicName] = (server, permanentTopic)
        return  pub

    def _getEventPublisher(self, topicName):
        """
        Wrapper over getPublisher, for generic event interface
        """
        return self._getPublisher(topicName, hms.GenericEventInterfacePrx, permanentTopic=True, server=self._icemgr.eventMgr)

    def newEvent(self, name, arguments, icebytes):
        """
        Received event from GenericEventInterface
        """
        self._log(2, "Holon registered to topic, but newEvent method not overwritten")


    def _unsubscribeTopic(self, name):
        """
        As the name says. It is necessary to unsubscribe to topics before exiting to avoid exceptions
        and being able to re-subscribe without error next time
        """
        self._subscribedTopics[name].unsubscribe(self.proxy)
        del(self._subscribedTopics[name])

    def cleanup(self):
        """
        Remove stuff from the database
        not catching exceptions since it is not very important
        """
        for topic in self._subscribedTopics.keys():
            self._unsubscribeTopic(topic)

        for k, v in self._publishedTopics.items():
            if not v[1]:
                topic = self._icemgr.getTopic(k, server=v[0], create=False)
                if topic:
                    #topic.destroy()
                    self._ilog("Topic destroying disabled since it can confuse clients")
        self.logger.cleanup()
       

    def getPublishedTopics(self, current):
        """
        Return a list of all topics published by one agent
        """
        return self._publishedTopics.keys()

    def printMsgQueue(self, ctx=None):
        for msg in self.mailbox.copy():
            print "%s" % msg.creationTime + ' receiving ' + msg.body

    
    def putMessage(self, msg, current=None):
        #is going to be called by other process/or threads so must be protected
        self._ilog("Received message: " + msg.body, level=9)
        self.mailbox.append(msg)

class Holon(LightHolon, Thread):
    """
    Holon is the same as LightHolon but starts a thread automatically
    """
    def __init__(self, name=None, logLevel=3):
        Thread.__init__(self)
        LightHolon.__init__(self, name, logLevel)
        self._stop = False
        self._lock = Lock()

    def start(self):
        """
        Re-implement because start exist in LightHolon
        """
        Thread.start(self)

    def stop(self, current=None):
        """
        Attempt to stop processing thread
        """
        self._ilog("stop called ")
        self._stop = True

    def _getProxyBlocking(self, address):
        return self._getHolonBlocking(address)

    def _getHolonBlocking(self, address):
        """
        Attempt to connect a given holon ID
        block until we connect
        return none if interrupted by self._stop
        """
        self._ilog( "Trying to connect  to " + address)
        prx = None    
        while not prx:
            prx = self._icemgr.getProxy(address)
            sleep(0.1)
            if self._stop:
                return None
        self._ilog( "Got connection to ", address)
        return prx

    def run(self):
        """ To be implemented by active holons
        """
        pass





class Agent(hms.Agent, Holon):
    """
    Legacy
    """

    def __init__(self, *args, **kw):
        Holon.__init__(self, *args, **kw)

class Message(hms.Message):
    """
    Wrapper over the Ice Message definition, 
    """
    def __init__(self, *args, **kwargs):
        hms.Message.__init__(self, *args, **kwargs)
        self.createTime = time()

    def __setattr__(self, name, val):
        #format everything to string
        if name == "parameters" and val:
            val = [str(i) for i in val]
        elif name == "arguments" and val:
            #val = {k:str(v) for k,v in val.items()} # does not work with python < 2.6
            d = dict()
            for k, v in val.items():
                if v in ("None", None): 
                    v = ""
                d[k] = str(v)
            val = d
        return hms.Message.__setattr__(self, name, val)



class MessageQueue(object):
    def __init__(self):
        self.lock = Lock()
        self._list = []
        
    def append(self, msg):
        self.lock.acquire()    
        self._list.append(msg)
        self.lock.release()

    def remove(self, msg):
        self.lock.acquire()
        #print "LIST", self._list
        #print msg
        self._list.remove(msg)
        self.lock.release()


    def pop(self):
        self.lock.acquire()
        if len(self._list) > 0:
            msg = self._list.pop(0)
        else: 
            msg = None
        self.lock.release()
        return msg

    def copy(self):
        """ return a copy of the current mailbox
        usefull for, for example, iteration
        """
        self.lock.acquire()
        #copy =  deepcopy(self._list)
        #shallow copy should be enough since as long as we have 
        # a link to the message python gc should not delete it
        # and as long as we do not modify message in our mailbox
        listcopy =  copy(self._list) 
        self.lock.release()
        return listcopy

    def __getitem__(self, x):
        """ to support mailbox[idx]"""
        return self._list.__getitem__(x)
    
    def __repr__(self):
        """ what is printed when printing the maibox  """
        return self._list.__repr__()




