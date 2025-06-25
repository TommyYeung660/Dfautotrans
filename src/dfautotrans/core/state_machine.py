"""Trading state machine for Dead Frontier Auto Trading System."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from loguru import logger

from ..data.models import TradingState, TradingSystemStatus, PlayerResources
from ..config.settings import Settings


class StateTransitionError(Exception):
    """State transition validation error."""
    pass


class StateMachine:
    """Trading system state machine manager."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.current_state = TradingState.IDLE
        self.previous_state: Optional[TradingState] = None
        self.state_history: List[Dict[str, Any]] = []
        self.state_entered_at = datetime.utcnow()
        self.retry_count = 0
        self.max_retries = 3
        
        # State transition rules
        self.valid_transitions = self._build_transition_rules()
        
        # State handlers
        self.state_handlers: Dict[TradingState, Callable] = {}
        
        # Wait management
        self.wait_until: Optional[datetime] = None
        
    def _build_transition_rules(self) -> Dict[TradingState, List[TradingState]]:
        """Build valid state transition rules."""
        # All states can transition to CRITICAL_ERROR as it's an emergency state
        critical_error_allowed = [TradingState.CRITICAL_ERROR]
        
        base_rules = {
            TradingState.IDLE: [
                TradingState.INITIALIZING,
                TradingState.ERROR
            ],
            TradingState.INITIALIZING: [
                TradingState.LOGIN_REQUIRED,
                TradingState.CHECKING_RESOURCES,
                TradingState.ERROR
            ],
            TradingState.LOGIN_REQUIRED: [
                TradingState.LOGGING_IN,
                TradingState.ERROR
            ],
            TradingState.LOGGING_IN: [
                TradingState.CHECKING_RESOURCES,
                TradingState.LOGIN_FAILED,
                TradingState.ERROR
            ],
            TradingState.LOGIN_FAILED: [
                TradingState.LOGIN_REQUIRED,
                TradingState.WAITING_NORMAL
            ],
            TradingState.CHECKING_RESOURCES: [
                TradingState.INSUFFICIENT_FUNDS,
                TradingState.CHECKING_INVENTORY,
                TradingState.MARKET_SCANNING,
                TradingState.ERROR
            ],
            TradingState.INSUFFICIENT_FUNDS: [
                TradingState.WITHDRAWING_FROM_BANK,
                TradingState.WAITING_BLOCKED,
                TradingState.ERROR
            ],
            TradingState.WITHDRAWING_FROM_BANK: [
                TradingState.CHECKING_RESOURCES,
                TradingState.INSUFFICIENT_FUNDS,
                TradingState.ERROR
            ],
            TradingState.CHECKING_INVENTORY: [
                TradingState.DEPOSITING_TO_STORAGE,
                TradingState.SPACE_FULL,
                TradingState.MARKET_SCANNING,
                TradingState.ERROR
            ],
            TradingState.DEPOSITING_TO_STORAGE: [
                TradingState.CHECKING_INVENTORY,
                TradingState.SPACE_FULL,
                TradingState.MARKET_SCANNING,
                TradingState.ERROR
            ],
            TradingState.SPACE_FULL: [
                TradingState.WAITING_BLOCKED,
                TradingState.CHECKING_INVENTORY,
                TradingState.ERROR
            ],
            TradingState.MARKET_SCANNING: [
                TradingState.BUYING,
                TradingState.SELLING,
                TradingState.WAITING_NORMAL,
                TradingState.CHECKING_RESOURCES,
                TradingState.ERROR
            ],
            TradingState.BUYING: [
                TradingState.MARKET_SCANNING,
                TradingState.CHECKING_RESOURCES,
                TradingState.CHECKING_INVENTORY,
                TradingState.ERROR
            ],
            TradingState.SELLING: [
                TradingState.MARKET_SCANNING,
                TradingState.CHECKING_RESOURCES,
                TradingState.SPACE_FULL,
                TradingState.ERROR
            ],
            TradingState.WAITING_NORMAL: [
                TradingState.MARKET_SCANNING,
                TradingState.CHECKING_RESOURCES,
                TradingState.ERROR
            ],
            TradingState.WAITING_BLOCKED: [
                TradingState.CHECKING_RESOURCES,
                TradingState.CHECKING_INVENTORY,
                TradingState.ERROR
            ],
            TradingState.ERROR: [
                TradingState.CHECKING_RESOURCES,
                TradingState.LOGIN_REQUIRED,
                TradingState.CRITICAL_ERROR,
                TradingState.IDLE
            ],
            TradingState.CRITICAL_ERROR: [
                TradingState.IDLE
            ]
        }
        
        # Add CRITICAL_ERROR to all states except CRITICAL_ERROR itself
        for state, allowed_states in base_rules.items():
            if state != TradingState.CRITICAL_ERROR:
                allowed_states.extend(critical_error_allowed)
        
        return base_rules
    
    def register_state_handler(self, state: TradingState, handler: Callable) -> None:
        """Register a handler for a specific state."""
        self.state_handlers[state] = handler
        logger.debug(f"Registered handler for state: {state}")
    
    def can_transition_to(self, target_state: TradingState) -> bool:
        """Check if transition to target state is valid."""
        valid_targets = self.valid_transitions.get(self.current_state, [])
        return target_state in valid_targets
    
    def set_state(self, target_state: TradingState) -> None:
        """Set state directly (synchronous version for compatibility)."""
        # Record state duration
        state_duration = (datetime.utcnow() - self.state_entered_at).total_seconds()
        
        # Log transition
        logger.info(f"State transition: {self.current_state} -> {target_state} (duration: {state_duration:.1f}s)")
        
        # Record state history
        self.state_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'from_state': self.current_state.value,
            'to_state': target_state.value,
            'duration_seconds': state_duration,
            'context': {},
            'retry_count': self.retry_count
        })
        
        # Update state
        self.previous_state = self.current_state
        self.current_state = target_state
        self.state_entered_at = datetime.utcnow()
        
        # Reset retry count on successful transition (except for error states)
        if target_state not in [TradingState.ERROR, TradingState.CRITICAL_ERROR]:
            self.retry_count = 0
        
        # Clear wait condition
        self.wait_until = None

    async def transition_to(self, target_state: TradingState, context: Optional[Dict[str, Any]] = None) -> bool:
        """Transition to a new state with validation."""
        if not self.can_transition_to(target_state):
            error_msg = f"Invalid transition from {self.current_state} to {target_state}"
            logger.error(error_msg)
            raise StateTransitionError(error_msg)
        
        # Record state duration
        state_duration = (datetime.utcnow() - self.state_entered_at).total_seconds()
        
        # Log transition
        logger.info(f"State transition: {self.current_state} -> {target_state} (duration: {state_duration:.1f}s)")
        
        # Record state history
        self.state_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'from_state': self.current_state.value,
            'to_state': target_state.value,
            'duration_seconds': state_duration,
            'context': context or {},
            'retry_count': self.retry_count
        })
        
        # Update state
        self.previous_state = self.current_state
        self.current_state = target_state
        self.state_entered_at = datetime.utcnow()
        
        # Reset retry count on successful transition (except for error states)
        if target_state not in [TradingState.ERROR, TradingState.CRITICAL_ERROR]:
            self.retry_count = 0
        
        # Clear wait condition
        self.wait_until = None
        
        return True
    
    async def handle_error(self, error: Exception, context: Optional[str] = None) -> bool:
        """Handle error and determine appropriate state transition."""
        self.retry_count += 1
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'retry_count': self.retry_count
        }
        
        logger.error(f"Error in state {self.current_state}: {error}", extra=error_context)
        
        # Determine if error is critical
        if self.retry_count > self.max_retries:
            logger.critical(f"Max retries exceeded in state {self.current_state}")
            await self.transition_to(TradingState.CRITICAL_ERROR, error_context)
            return False
        
        # Transition to error state
        await self.transition_to(TradingState.ERROR, error_context)
        return True
    
    def set_wait_condition(self, wait_seconds: int, reason: str = "") -> None:
        """Set a wait condition for the current state."""
        self.wait_until = datetime.utcnow() + timedelta(seconds=wait_seconds)
        logger.info(f"Set wait condition: {wait_seconds}s in state {self.current_state} - {reason}")
    
    def is_waiting(self) -> bool:
        """Check if currently in a wait condition."""
        if self.wait_until is None:
            return False
        return datetime.utcnow() < self.wait_until
    
    def get_wait_remaining(self) -> int:
        """Get remaining wait time in seconds."""
        if self.wait_until is None:
            return 0
        remaining = (self.wait_until - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))
    
    async def execute_state_handler(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Execute the handler for the current state."""
        handler = self.state_handlers.get(self.current_state)
        if handler is None:
            logger.warning(f"No handler registered for state: {self.current_state}")
            return False
        
        try:
            logger.debug(f"Executing handler for state: {self.current_state}")
            result = await handler(context or {})
            return result
        except Exception as e:
            await self.handle_error(e, f"Handler execution for {self.current_state}")
            return False
    
    def get_status(self, player_resources: Optional[PlayerResources] = None) -> TradingSystemStatus:
        """Get current system status."""
        return TradingSystemStatus(
            current_state=self.current_state,
            player_resources=player_resources,
            last_state_change=self.state_entered_at,
            wait_until=self.wait_until,
            retry_count=self.retry_count
        )
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get state transition statistics."""
        if not self.state_history:
            return {}
        
        state_counts = {}
        total_duration = 0
        
        for entry in self.state_history:
            state = entry['from_state']
            duration = entry['duration_seconds']
            
            if state not in state_counts:
                state_counts[state] = {'count': 0, 'total_duration': 0}
            
            state_counts[state]['count'] += 1
            state_counts[state]['total_duration'] += duration
            total_duration += duration
        
        # Calculate averages
        for state, stats in state_counts.items():
            stats['average_duration'] = stats['total_duration'] / stats['count']
        
        return {
            'total_transitions': len(self.state_history),
            'total_duration': total_duration,
            'state_statistics': state_counts,
            'current_state': self.current_state.value,
            'current_state_duration': (datetime.utcnow() - self.state_entered_at).total_seconds()
        }
    
    def export_state_history(self) -> str:
        """Export state history as JSON."""
        return json.dumps({
            'current_state': self.current_state.value,
            'state_entered_at': self.state_entered_at.isoformat(),
            'retry_count': self.retry_count,
            'wait_until': self.wait_until.isoformat() if self.wait_until else None,
            'history': self.state_history,
            'statistics': self.get_state_statistics()
        }, indent=2)
    
    def reset(self) -> None:
        """Reset state machine to initial state."""
        logger.info("Resetting state machine to IDLE")
        self.current_state = TradingState.IDLE
        self.previous_state = None
        self.state_entered_at = datetime.utcnow()
        self.retry_count = 0
        self.wait_until = None
        # Keep history for analysis 