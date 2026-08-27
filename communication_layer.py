"""
Communication Layer - Inter-agent messaging and coordination system.

This module repurposes autogen-main concepts as a lightweight communication
layer for the 1st Agent framework. It provides:

1. Message passing between agents
2. Topic-based pub/sub system
3. Request/response patterns
4. Broadcast capabilities
5. Agent discovery and registry

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    COMMUNICATION LAYER                         │
├───────────────────────────┬───────────────────────────────────┤
│ MessageBus               │ AgentRegistry                     │
│ - pub/sub                │ - register()                      │
│ - request/response       │ - discover()                      │
│ - broadcast              │ - get_agent()                    │
├───────────────────────────┴───────────────────────────────────┤
│ MessageQueue             │ ProtocolHandlers                 │
│ - async processing       │ - serialize/deserialize           │
│ - prioritization         │ - validation                     │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │ Researcher  │    │ Production  │    │ Specialized │
   │ Agent       │    │ Agent       │    │ Agents      │
   └─────────────┘    └─────────────┘    └─────────────┘
"""

import asyncio
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from collections import defaultdict
import queue

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in the communication system."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    TASK = "task"
    RESULT = "result"


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    agent_id: str
    name: str
    agent_type: str
    domain: str
    capabilities: List[str]
    model_path: Optional[str] = None
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class Message:
    """Base message class for inter-agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: Optional[str] = None
    message_type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    topic: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None
    ttl: Optional[float] = None  # Time to live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "topic": self.topic,
            "content": self.content,
            "metadata": self.metadata,
            "reply_to": self.reply_to,
            "correlation_id": self.correlation_id,
            "ttl": self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Deserialize message from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id"),
            message_type=MessageType(data.get("message_type", "request")),
            priority=MessagePriority(data.get("priority", 1)),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            topic=data.get("topic"),
            content=data.get("content", {}),
            metadata=data.get("metadata", {}),
            reply_to=data.get("reply_to"),
            correlation_id=data.get("correlation_id"),
            ttl=data.get("ttl")
        )
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Deserialize message from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class RequestMessage(Message):
    """Request message with response expectation."""
    expected_response: str = ""
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        self.message_type = MessageType.REQUEST


@dataclass
class ResponseMessage(Message):
    """Response message to a request."""
    request_id: str = ""
    is_success: bool = True
    error: Optional[str] = None
    
    def __post_init__(self):
        self.message_type = MessageType.RESPONSE


class AgentRegistry:
    """Registry for all agents in the system."""
    
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._type_index: Dict[str, List[str]] = defaultdict(list)
        self._domain_index: Dict[str, List[str]] = defaultdict(list)
        self._capability_index: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def register(self, agent_info: AgentInfo) -> AgentInfo:
        """Register an agent with the registry."""
        with self._lock:
            if agent_info.agent_id in self._agents:
                logger.warning(f"Agent {agent_info.agent_id} already registered, updating...")
            
            self._agents[agent_info.agent_id] = agent_info
            self._type_index[agent_info.agent_type].append(agent_info.agent_id)
            self._domain_index[agent_info.domain].append(agent_info.agent_id)
            
            for cap in agent_info.capabilities:
                self._capability_index[cap].append(agent_info.agent_id)
            
            logger.info(f"Registered agent: {agent_info.name} ({agent_info.agent_id})")
            return agent_info
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            agent_info = self._agents.pop(agent_id)
            
            # Remove from indexes
            if agent_info.agent_type in self._type_index:
                self._type_index[agent_info.agent_type].remove(agent_id)
            if agent_info.domain in self._domain_index:
                self._domain_index[agent_info.domain].remove(agent_id)
            
            for cap in agent_info.capabilities:
                if cap in self._capability_index:
                    self._capability_index[cap].remove(agent_id)
            
            logger.info(f"Unregistered agent: {agent_info.name} ({agent_id})")
            return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID."""
        with self._lock:
            return self._agents.get(agent_id)
    
    def get_by_type(self, agent_type: str) -> List[AgentInfo]:
        """Get agents by type."""
        with self._lock:
            return [self._agents[aid] for aid in self._type_index.get(agent_type, []) 
                   if aid in self._agents]
    
    def get_by_domain(self, domain: str) -> List[AgentInfo]:
        """Get agents by domain."""
        with self._lock:
            return [self._agents[aid] for aid in self._domain_index.get(domain, []) 
                   if aid in self._agents]
    
    def get_by_capability(self, capability: str) -> List[AgentInfo]:
        """Get agents with specific capability."""
        with self._lock:
            return [self._agents[aid] for aid in self._capability_index.get(capability, []) 
                   if aid in self._agents]
    
    def discover(self, agent_type: Optional[str] = None, 
                 domain: Optional[str] = None, 
                 capability: Optional[str] = None) -> List[AgentInfo]:
        """Discover agents matching criteria."""
        with self._lock:
            agents = list(self._agents.values())
            
            if agent_type:
                agents = [a for a in agents if a.agent_type == agent_type]
            if domain:
                agents = [a for a in agents if a.domain == domain]
            if capability:
                agents = [a for a in agents if capability in a.capabilities]
            
            return agents
    
    def list_all(self) -> List[AgentInfo]:
        """List all registered agents."""
        with self._lock:
            return list(self._agents.values())
    
    def update_heartbeat(self, agent_id: str) -> bool:
        """Update heartbeat for an agent."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].last_heartbeat = datetime.now().isoformat()
                return True
            return False
    
    def get_active_agents(self) -> List[AgentInfo]:
        """Get all active agents."""
        with self._lock:
            return [a for a in self._agents.values() if a.is_active]
    
    def update_metrics(self, agent_id: str, metrics: Dict[str, float]) -> bool:
        """Update metrics for an agent."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].metrics.update(metrics)
                return True
            return False


class MessageQueue:
    """Priority-based message queue for async processing."""
    
    def __init__(self):
        self._queues: Dict[MessagePriority, queue.PriorityQueue] = {
            MessagePriority.CRITICAL: queue.PriorityQueue(),
            MessagePriority.HIGH: queue.PriorityQueue(),
            MessagePriority.NORMAL: queue.PriorityQueue(),
            MessagePriority.LOW: queue.PriorityQueue()
        }
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
    
    def enqueue(self, message: Message, priority: Optional[MessagePriority] = None):
        """Add a message to the queue."""
        pri = priority or message.priority
        with self._lock:
            # Use negative priority for queue (lower number = higher priority)
            self._queues[pri].put((-pri.value, message))
            self._condition.notify()
    
    def dequeue(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get the next message from the queue."""
        with self._lock:
            if timeout:
                self._condition.wait(timeout)
            
            # Check queues in priority order
            for pri in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                       MessagePriority.NORMAL, MessagePriority.LOW]:
                if not self._queues[pri].empty():
                    _, message = self._queues[pri].get()
                    return message
            return None
    
    def dequeue_by_priority(self, priority: MessagePriority, 
                           timeout: Optional[float] = None) -> Optional[Message]:
        """Get a message from a specific priority queue."""
        with self._lock:
            if timeout:
                self._condition.wait(timeout)
            
            if not self._queues[priority].empty():
                _, message = self._queues[priority].get()
                return message
            return None
    
    def is_empty(self) -> bool:
        """Check if all queues are empty."""
        with self._lock:
            return all(q.empty() for q in self._queues.values())
    
    def size(self) -> int:
        """Get total number of messages in all queues."""
        with self._lock:
            return sum(q.qsize() for q in self._queues.values())
    
    def clear(self):
        """Clear all messages from all queues."""
        with self._lock:
            for q in self._queues.values():
                while not q.empty():
                    q.get()


class PubSubManager:
    """Topic-based publish/subscribe system."""
    
    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, List[Callable]]] = defaultdict(lambda: defaultdict(list))
        self._lock = threading.RLock()
    
    def subscribe(self, agent_id: str, topic: str, 
                  callback: Callable[[Message], Any]) -> str:
        """Subscribe to a topic."""
        subscription_id = str(uuid.uuid4())
        with self._lock:
            self._subscriptions[topic][agent_id].append((subscription_id, callback))
            logger.debug(f"Agent {agent_id} subscribed to topic {topic}")
        return subscription_id
    
    def unsubscribe(self, agent_id: str, topic: str, 
                    subscription_id: Optional[str] = None) -> bool:
        """Unsubscribe from a topic."""
        with self._lock:
            if topic in self._subscriptions and agent_id in self._subscriptions[topic]:
                if subscription_id:
                    # Remove specific subscription
                    self._subscriptions[topic][agent_id] = [
                        (sid, cb) for sid, cb in self._subscriptions[topic][agent_id]
                        if sid != subscription_id
                    ]
                else:
                    # Remove all subscriptions for this agent on this topic
                    del self._subscriptions[topic][agent_id]
                
                # Clean up empty topics
                if not self._subscriptions[topic][agent_id]:
                    del self._subscriptions[topic][agent_id]
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]
                
                return True
        return False
    
    def publish(self, topic: str, message: Message):
        """Publish a message to a topic."""
        message.topic = topic
        message.message_type = MessageType.PUBLISH
        
        with self._lock:
            if topic in self._subscriptions:
                for agent_id, callbacks in self._subscriptions[topic].items():
                    for _, callback in callbacks:
                        try:
                            # Run callback in a separate thread to avoid blocking
                            threading.Thread(
                                target=callback,
                                args=(message,),
                                daemon=True
                            ).start()
                        except Exception as e:
                            logger.error(f"Error delivering message to {agent_id}: {e}")
    
    def get_subscribers(self, topic: str) -> List[str]:
        """Get list of agent IDs subscribed to a topic."""
        with self._lock:
            return list(self._subscriptions.get(topic, {}).keys())
    
    def get_topics(self) -> List[str]:
        """Get all active topics."""
        with self._lock:
            return list(self._subscriptions.keys())


class RequestResponseManager:
    """Manages request/response patterns with timeouts."""
    
    def __init__(self):
        self._pending_requests: Dict[str, Dict] = {}
        self._responses: Dict[str, Message] = {}
        self._lock = threading.RLock()
    
    def send_request(self, request: RequestMessage, 
                     callback: Optional[Callable[[Message], Any]] = None) -> str:
        """Send a request and register a callback for the response."""
        request_id = request.message_id
        with self._lock:
            self._pending_requests[request_id] = {
                "request": request,
                "callback": callback,
                "timestamp": datetime.now(),
                "timeout": request.timeout
            }
        return request_id
    
    def receive_response(self, response: ResponseMessage) -> bool:
        """Receive a response to a pending request."""
        request_id = response.request_id
        with self._lock:
            if request_id in self._pending_requests:
                pending = self._pending_requests[request_id]
                
                # Store response
                self._responses[request_id] = response
                
                # Execute callback if provided
                if pending.get("callback"):
                    try:
                        pending["callback"](response)
                    except Exception as e:
                        logger.error(f"Error in response callback: {e}")
                
                # Clean up
                del self._pending_requests[request_id]
                return True
        return False
    
    def get_response(self, request_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """Wait for and get a response (synchronous)."""
        import time
        start_time = time.time()
        
        while True:
            with self._lock:
                if request_id in self._responses:
                    response = self._responses.pop(request_id)
                    return response
                
                if request_id not in self._pending_requests:
                    return None
                
                if timeout and (time.time() - start_time) > timeout:
                    return None
            
            time.sleep(0.01)
    
    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request."""
        with self._lock:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
                if request_id in self._responses:
                    del self._responses[request_id]
                return True
        return False
    
    def cleanup_expired(self):
        """Clean up expired requests."""
        import time
        current_time = time.time()
        with self._lock:
            expired = []
            for request_id, pending in self._pending_requests.items():
                request_time = pending["timestamp"].timestamp()
                if (current_time - request_time) > pending.get("timeout", 30):
                    expired.append(request_id)
            
            for request_id in expired:
                del self._pending_requests[request_id]
                if request_id in self._responses:
                    del self._responses[request_id]


class CommunicationLayer:
    """
    Main communication layer for the 1st Agent framework.
    
    This is the repurposed autogen-main communication system, designed to be
    lightweight and efficient for local multi-agent coordination.
    
    Usage:
        # Initialize
        comm = CommunicationLayer()
        
        # Register agents
        comm.register_agent(AgentInfo(...))
        
        # Send messages
        comm.send(message)
        
        # Publish to topics
        comm.publish("weather.updates", message)
        
        # Request/response
        response = comm.request(receiver_id, content, timeout=5)
    """
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.queue = MessageQueue()
        self.pubsub = PubSubManager()
        self.request_manager = RequestResponseManager()
        self._message_handlers: Dict[str, Callable] = {}
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        logger.info("Communication layer initialized")
    
    def start(self):
        """Start the communication layer worker thread."""
        with self._lock:
            if self._is_running:
                return
            
            self._is_running = True
            self._worker_thread = threading.Thread(
                target=self._process_messages,
                daemon=True
            )
            self._worker_thread.start()
            logger.info("Communication layer started")
    
    def stop(self):
        """Stop the communication layer."""
        with self._lock:
            self._is_running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5)
            logger.info("Communication layer stopped")
    
    def register_agent(self, agent_info: AgentInfo) -> AgentInfo:
        """Register an agent."""
        return self.registry.register(agent_info)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        return self.registry.unregister(agent_id)
    
    def register_handler(self, agent_id: str, handler: Callable[[Message], Any]):
        """Register a message handler for an agent."""
        with self._lock:
            self._message_handlers[agent_id] = handler
            logger.info(f"Registered message handler for {agent_id}")
    
    def unregister_handler(self, agent_id: str) -> bool:
        """Unregister a message handler."""
        with self._lock:
            if agent_id in self._message_handlers:
                del self._message_handlers[agent_id]
                logger.info(f"Unregistered message handler for {agent_id}")
                return True
        return False
    
    def send(self, message: Message) -> str:
        """Send a message to a specific agent."""
        message_id = message.message_id
        
        # Validate receiver exists
        if message.receiver_id and not self.registry.get_agent(message.receiver_id):
            logger.warning(f"Receiver {message.receiver_id} not found")
            return message_id
        
        # Queue the message
        self.queue.enqueue(message)
        logger.debug(f"Message {message_id} queued for {message.receiver_id or 'any'}")
        return message_id
    
    def publish(self, topic: str, content: Dict[str, Any], 
                sender_id: str = "system") -> str:
        """Publish a message to a topic."""
        message = Message(
            sender_id=sender_id,
            topic=topic,
            content=content,
            message_type=MessageType.PUBLISH
        )
        self.pubsub.publish(topic, message)
        logger.debug(f"Published to topic {topic}")
        return message.message_id
    
    def broadcast(self, content: Dict[str, Any], 
                  sender_id: str = "system",
                  agent_type: Optional[str] = None,
                  domain: Optional[str] = None) -> List[str]:
        """Broadcast a message to multiple agents."""
        agents = self.registry.discover(agent_type=agent_type, domain=domain)
        message_ids = []
        
        for agent in agents:
            message = Message(
                sender_id=sender_id,
                receiver_id=agent.agent_id,
                content=content,
                message_type=MessageType.BROADCAST
            )
            self.send(message)
            message_ids.append(message.message_id)
        
        logger.info(f"Broadcast to {len(agents)} agents")
        return message_ids
    
    def request(self, receiver_id: str, content: Dict[str, Any],
                sender_id: str = "system", timeout: float = 30.0) -> Optional[Message]:
        """Send a request and wait for a response."""
        request = RequestMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            timeout=timeout
        )
        
        request_id = self.request_manager.send_request(request)
        self.send(request)
        
        # Wait for response
        response = self.request_manager.get_response(request_id, timeout=timeout)
        
        if response:
            logger.debug(f"Request {request_id} received response")
        else:
            logger.warning(f"Request {request_id} timed out")
        
        return response
    
    def reply(self, request: Message, content: Dict[str, Any],
              is_success: bool = True, error: Optional[str] = None) -> str:
        """Reply to a request message."""
        response = ResponseMessage(
            sender_id=request.receiver_id or "",
            receiver_id=request.sender_id,
            request_id=request.message_id,
            content=content,
            is_success=is_success,
            error=error,
            correlation_id=request.correlation_id
        )
        self.send(response)
        return response.message_id
    
    def subscribe(self, agent_id: str, topic: str,
                   callback: Callable[[Message], Any]) -> str:
        """Subscribe an agent to a topic."""
        return self.pubsub.subscribe(agent_id, topic, callback)
    
    def unsubscribe(self, agent_id: str, topic: str,
                    subscription_id: Optional[str] = None) -> bool:
        """Unsubscribe an agent from a topic."""
        return self.pubsub.unsubscribe(agent_id, topic, subscription_id)
    
    def discover_agents(self, agent_type: Optional[str] = None,
                        domain: Optional[str] = None,
                        capability: Optional[str] = None) -> List[AgentInfo]:
        """Discover agents matching criteria."""
        return self.registry.discover(agent_type, domain, capability)
    
    def _process_messages(self):
        """Background thread that processes queued messages."""
        logger.info("Message processor started")
        
        while self._is_running:
            try:
                # Get next message
                message = self.queue.dequeue(timeout=0.1)
                
                if message is None:
                    continue
                
                # Handle expired TTL
                if message.ttl and message.timestamp:
                    import time
                    message_time = datetime.fromisoformat(message.timestamp).timestamp()
                    if (time.time() - message_time) > message.ttl:
                        logger.debug(f"Message {message.message_id} expired")
                        continue
                
                # Route message
                self._route_message(message)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
        logger.info("Message processor stopped")
    
    def _route_message(self, message: Message):
        """Route a message to its destination."""
        try:
            # Check for pub/sub messages
            if message.message_type == MessageType.PUBLISH:
                self.pubsub.publish(message.topic or "", message)
                return
            
            # Check for request/response
            if message.message_type == MessageType.RESPONSE:
                self.request_manager.receive_response(message)
                return
            
            # Route to specific agent or broadcast
            if message.receiver_id:
                self._deliver_to_agent(message)
            else:
                # Broadcast to all agents
                for agent_id in self._message_handlers:
                    message_copy = Message(
                        message_id=message.message_id,
                        sender_id=message.sender_id,
                        receiver_id=agent_id,
                        message_type=message.message_type,
                        priority=message.priority,
                        timestamp=message.timestamp,
                        topic=message.topic,
                        content=message.content,
                        metadata=message.metadata,
                        reply_to=message.reply_to,
                        correlation_id=message.correlation_id,
                        ttl=message.ttl
                    )
                    self._deliver_to_agent(message_copy)
                    
        except Exception as e:
            logger.error(f"Error routing message {message.message_id}: {e}")
    
    def _deliver_to_agent(self, message: Message):
        """Deliver a message to a specific agent."""
        if message.receiver_id in self._message_handlers:
            try:
                handler = self._message_handlers[message.receiver_id]
                handler(message)
                logger.debug(f"Delivered message {message.message_id} to {message.receiver_id}")
            except Exception as e:
                logger.error(f"Error delivering message to {message.receiver_id}: {e}")
        else:
            logger.warning(f"No handler for agent {message.receiver_id}")


# Global communication layer instance
comm_layer = CommunicationLayer()


class AgentCommunicator:
    """
    Mixin class that provides communication capabilities to agents.
    
    Usage:
        class MyAgent(AgentCommunicator):
            def __init__(self, agent_id, comm_layer):
                self.agent_id = agent_id
                self.comm = comm_layer
                self.register()
    """
    
    def __init__(self, agent_id: str, comm_layer: Optional[CommunicationLayer] = None):
        self.agent_id = agent_id
        self.comm = comm_layer or comm_layer
        self._subscriptions: List[Tuple[str, str]] = []  # (topic, subscription_id)
    
    def register(self, agent_info: Optional[AgentInfo] = None):
        """Register this agent with the communication layer."""
        if agent_info:
            self.comm.register_agent(agent_info)
        else:
            # Create default agent info
            info = AgentInfo(
                agent_id=self.agent_id,
                name=self.agent_id,
                agent_type="agent",
                domain="general",
                capabilities=[]
            )
            self.comm.register_agent(info)
        
        # Register message handler
        self.comm.register_handler(self.agent_id, self.handle_message)
    
    def unregister(self):
        """Unregister this agent."""
        self.comm.unregister_agent(self.agent_id)
        self.comm.unregister_handler(self.agent_id)
        
        # Clean up subscriptions
        for topic, sub_id in self._subscriptions:
            self.comm.unsubscribe(self.agent_id, topic, sub_id)
        self._subscriptions = []
    
    def handle_message(self, message: Message):
        """Handle incoming messages. Override in subclasses."""
        logger.info(f"Agent {self.agent_id} received message: {message.message_type}")
    
    def send(self, receiver_id: str, content: Dict[str, Any],
             message_type: MessageType = MessageType.REQUEST) -> str:
        """Send a message to another agent."""
        message = Message(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type
        )
        return self.comm.send(message)
    
    def publish(self, topic: str, content: Dict[str, Any]) -> str:
        """Publish to a topic."""
        return self.comm.publish(topic, content, self.agent_id)
    
    def subscribe(self, topic: str, callback: Callable[[Message], Any]) -> str:
        """Subscribe to a topic."""
        sub_id = self.comm.subscribe(self.agent_id, topic, callback)
        self._subscriptions.append((topic, sub_id))
        return sub_id
    
    def request(self, receiver_id: str, content: Dict[str, Any],
                timeout: float = 30.0) -> Optional[Message]:
        """Send a request and wait for response."""
        return self.comm.request(receiver_id, content, self.agent_id, timeout)
    
    def reply(self, request: Message, content: Dict[str, Any],
              is_success: bool = True, error: Optional[str] = None) -> str:
        """Reply to a request."""
        return self.comm.reply(request, content, is_success, error)
    
    def broadcast(self, content: Dict[str, Any],
                  agent_type: Optional[str] = None,
                  domain: Optional[str] = None) -> List[str]:
        """Broadcast to multiple agents."""
        return self.comm.broadcast(content, self.agent_id, agent_type, domain)
    
    def discover(self, agent_type: Optional[str] = None,
                 domain: Optional[str] = None,
                 capability: Optional[str] = None) -> List[AgentInfo]:
        """Discover other agents."""
        return self.comm.discover_agents(agent_type, domain, capability)


# Decorator for agent methods that handle specific message types
def message_handler(message_type: Optional[MessageType] = None,
                   topic: Optional[str] = None):
    """Decorator to register a method as a message handler."""
    def decorator(func):
        def wrapper(self, message: Message):
            # Check if this handler should process the message
            if message_type and message.message_type != message_type:
                return
            if topic and message.topic != topic:
                return
            
            # Call the handler
            return func(self, message)
        return wrapper
    return decorator


# Helper function to create agent info from class
def create_agent_info(agent_id: str, name: str, agent_type: str, 
                      domain: str, capabilities: List[str],
                      model_path: Optional[str] = None) -> AgentInfo:
    """Create AgentInfo for an agent."""
    return AgentInfo(
        agent_id=agent_id,
        name=name,
        agent_type=agent_type,
        domain=domain,
        capabilities=capabilities,
        model_path=model_path
    )


if __name__ == "__main__":
    # Demo usage
    logger.info("Starting communication layer demo...")
    
    # Create communication layer
    comm = CommunicationLayer()
    comm.start()
    
    # Create agent info
    researcher_info = create_agent_info(
        agent_id="researcher_001",
        name="Researcher Agent",
        agent_type="researcher",
        domain="R&D",
        capabilities=["data_generation", "evaluation", "analysis"]
    )
    
    production_info = create_agent_info(
        agent_id="production_001",
        name="Production Agent",
        agent_type="production",
        domain="user_queries",
        capabilities=["classification", "routing", "formatting"]
    )
    
    # Register agents
    comm.register_agent(researcher_info)
    comm.register_agent(production_info)
    
    # Create simple message handlers
    def researcher_handler(message: Message):
        print(f"Researcher received: {message.message_type.value} - {message.content}")
    
    def production_handler(message: Message):
        print(f"Production received: {message.message_type.value} - {message.content}")
    
    comm.register_handler("researcher_001", researcher_handler)
    comm.register_handler("production_001", production_handler)
    
    # Send some messages
    comm.send(Message(
        sender_id="system",
        receiver_id="researcher_001",
        content={"task": "generate_data", "domain": "weather"}
    ))
    
    comm.send(Message(
        sender_id="system",
        receiver_id="production_001",
        content={"query": "What's the weather in Lagos?"}
    ))
    
    # Publish to a topic
    comm.publish("system.updates", {"status": "initialized"})
    
    # Discover agents
    agents = comm.discover_agents(domain="R&D")
    print(f"\nDiscovered {len(agents)} R&D agents:")
    for agent in agents:
        print(f"  - {agent.name} ({agent.agent_id})")
    
    # Wait for messages to process
    import time
    time.sleep(1)
    
    comm.stop()
    logger.info("Demo completed")
