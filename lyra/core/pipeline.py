# -*- coding: utf-8 -*-
"""
Lyra Pipeline - Phase 5A/5B
Orchestrates full execution pipeline
Input -> Intent -> Plan -> Execute -> Output
"""

from typing import Dict, Any, Optional, List
import json
from dataclasses import dataclass
from lyra.reasoning.intent_detector import IntentDetector
from lyra.reasoning.command_schema import Command
from lyra.reasoning.command_suggester import CommandSuggester
from lyra.planning.execution_planner import ExecutionPlanner
from lyra.execution.execution_gateway import ExecutionGateway
from lyra.cli.output_formatter import OutputFormatter
from lyra.core.command_history import CommandHistory, CommandEntry
from lyra.core.execution_history import ExecutionHistory, ExecutionEntry
from lyra.semantic.semantic_engine import SemanticEngine
from lyra.context.context_manager import ConversationContext
from lyra.context.refinement_engine import RefinementEngine
from lyra.context.clarification_service import ClarificationManager
from lyra.memory.session_memory import SessionMemory
from lyra.metrics.metrics_collector import MetricsCollector
from lyra.context.normalization_engine import NormalizationEngine
from lyra.context.conversation_layer import ConversationLayer
from lyra.core.logger import get_logger
import time


@dataclass
class PipelineResult:
    """Result of pipeline execution"""
    success: bool
    output: str
    cancelled: bool = False
    error: Optional[str] = None


class LyraPipeline:
    """
    Full execution pipeline orchestrator
    Phase 5A: Connect all components
    Phase 5B: Add history tracking
    Phase 6: Advanced reasoning & context
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.intent_detector = IntentDetector()
        self.planner = ExecutionPlanner()
        self.gateway = ExecutionGateway()
        self.formatter = OutputFormatter()
        
        # Phase 5B: History tracking & suggestions
        self.command_history = CommandHistory(max_size=20)
        self.execution_history = ExecutionHistory(max_size=10)
        self.suggester = CommandSuggester()
        
        # Phase 6A: Semantic Layer (Optional)
        self.semantic_engine = SemanticEngine()
        self.use_semantic_layer = True  # Feature flag

        # Phase 6B: Conversational Context & Refinement
        self.context = ConversationContext()
        self.refinement_engine = RefinementEngine()
        
        # Phase 6C: Clarification Loop
        self.clarification_manager = ClarificationManager()
        
        # Phase 6F: Session Memory
        self.session_memory = SessionMemory()
        
        # Phase 6G: Metrics
        self.metrics = MetricsCollector()
        
        # Phase 6H: Input Normalization
        self.normalization_engine = NormalizationEngine()

        # Phase 6I: Conversational Intelligence
        self.conversation_layer = ConversationLayer()

        self.logger.info("Lyra pipeline initialized")

    def _handle_metrics(self) -> PipelineResult:
        """Phase 6G: Return internal metrics report"""
        report = self.metrics.get_report()
        return PipelineResult(success=True, output=report)

    def _handle_status(self) -> PipelineResult:
        """Phase 6D: Return system status"""
        context_intent = self.context.get_last_intent()
        conf = context_intent.get("confidence", 0.0) if context_intent else 0.0
        pending = "Yes" if self.clarification_manager.has_pending() else "No"
        
        status_msg = (
            f"Lyra Status:\n"
            f"- Pending Clarification: {pending}\n"
            f"- Last Intent Confidence: {conf:.2f}\n"
            f"- Context Active: {'Yes' if context_intent else 'No'}"
        )
        return PipelineResult(success=True, output=status_msg)

    def _handle_pending(self) -> PipelineResult:
        """Phase 6D: Check pending clarification details"""
        if not self.clarification_manager.has_pending():
            return PipelineResult(success=True, output="No pending clarification.")
            
        mgr = self.clarification_manager
        msg = (
            f"Pending Clarification:\n"
            f"- Attempt: {mgr.attempt_count}/3\n"
            f"- Missing Fields: {', '.join(mgr.missing_fields)}\n"
            f"- Last Question: {mgr.last_question}"
        )
        return PipelineResult(success=True, output=msg)

    def _handle_last_intent(self) -> PipelineResult:
        """Phase 6D: Dump last intent JSON"""
        last = self.context.get_last_intent()
        if not last:
             return PipelineResult(success=True, output="No intent in history.")
        return PipelineResult(success=True, output=json.dumps(last, indent=2))

    def _handle_explain(self) -> PipelineResult:
        """Phase 6D: Explain current state"""
        last = self.context.get_last_intent()
        pending = self.clarification_manager.has_pending()
        
        msg = (
            f"Decision State:\n"
            f"- Clarification Mode: {'Active' if pending else 'Inactive'}\n"
            f"- Last Confidence: {last.get('confidence', 0.0) if last else 0.0}\n"
            f"- Execution Allowed: {'No (Pending)' if pending else 'Yes'}"
        )
        return PipelineResult(success=True, output=msg)
    
    def _execute_command(self, command: Command, auto_confirm: bool = False) -> PipelineResult:
        """
        Execute a single command object.
        Encapsulates Planning -> Confirmation -> Gateway -> History
        """
        try:
            self.logger.info(f"Intent: {command.intent} [{command.decision_source}]")
            
            # 1. Generate execution plan
            plan = self.planner.create_plan_from_command(command)
            
            if not plan:
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not create execution plan"),
                    error="Plan generation failed"
                )
            
            self.logger.info(f"Plan created: {plan.plan_id}, {len(plan.steps)} steps")
            
            # 2. Check if confirmation needed
            confirmed = auto_confirm
            if plan.requires_confirmation and not auto_confirm:
                confirmation_msg = self.formatter.format_confirmation(
                    action=f"{command.intent}: {command.raw_input}",
                    risk=plan.total_risk_score,
                    details=f"{len(plan.steps)} step(s) will be executed"
                )
                print(confirmation_msg)
                
                # Ask for confirmation
                try:
                    response = input(self.formatter.format_confirmation_prompt())
                    confirmed = response.lower() in ['y', 'yes']
                except EOFError:
                    confirmed = False
                
                if not confirmed:
                    return PipelineResult(
                        success=False,
                        output=self.formatter.format_cancellation(),
                        cancelled=True
                    )
            
            # 3. Execute plan
            self.logger.info(f"Executing plan: {plan.plan_id}")
            result = self.gateway.execute_plan(plan, confirmed=confirmed)
            
            # 4. Track execution
            self.execution_history.add(
                plan_id=plan.plan_id,
                success=result.success,
                duration=result.total_duration,
                command=command.raw_input,
                error=result.error
            )
            
            # 5. Format output
            output = self.formatter.format_result(result)
            
            # 6. Update Context
            if result.success:
                self.context.update_last_intent({
                    "intent": command.intent,
                    "parameters": command.entities,
                    "confidence": command.confidence,
                    "requires_clarification": False
                })
                # Phase 6F: Update Session Memory
                self.session_memory.update_from_intent(command)
            else:
                self.context.clear()
            
            return PipelineResult(
                success=result.success,
                output=output,
                error=result.error
            )

        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            return PipelineResult(
                success=False,
                output=self.formatter.format_error_from_exception(e),
                error=str(e)
            )

    def process_command(self, user_input: str, 
                       auto_confirm: bool = False) -> PipelineResult:
        """
        Process user command through full pipeline.
        Supports Multi-Intent Execution (Phase 6E).

        Pipeline order (Phase 6I):
          Raw Input
          → Introspection Interceptors  (Phase 6D)  [always first]
          → Normalization Engine        (Phase 6H)
          → Conversational Layer        (Phase 6I)
          → Session Memory Resolution  (Phase 6F)
          → Clarification Loop         (Phase 6C)
          → Refinement Engine          (Phase 6B)
          → Semantic Layer             (Phase 6A)
          → Regex Fallback
          → Execution Gateway
        """
        try:
            # ── Phase 6D: Introspection Interceptors (ALWAYS FIRST) ──────────
            # These must bypass normalization entirely — they are exact keywords.
            low_input = user_input.lower().strip()
            if low_input == "status":
                return self._handle_status()
            elif low_input == "pending":
                return self._handle_pending()
            elif low_input == "last_intent":
                return self._handle_last_intent()
            elif low_input == "explain":
                return self._handle_explain()
            elif low_input == "metrics":
                return self._handle_metrics()

            # ── Phase 6H: Input Normalization ────────────────────────────────
            norm_result = self.normalization_engine.normalize(user_input)

            if norm_result.dangerous_token_detected:
                # A misspelled destructive keyword was detected — do NOT correct.
                # Return an explicit clarification so the user types it deliberately.
                detected = norm_result.dangerous_token_detected
                self.logger.warning(
                    f"Dangerous token detected near '{detected}': '{user_input}'"
                )
                return PipelineResult(
                    success=False,
                    output=(
                        f"Did you mean '{detected}'? "
                        f"Destructive commands must be typed explicitly."
                    ),
                    error="Dangerous token detected"
                )

            if norm_result.was_modified:
                self.logger.info(
                    f"Input normalised [{norm_result.delta}]: "
                    f"'{user_input}' → '{norm_result.normalized}'"
                )
                # Only count as applied when no dangerous token involved
                self.metrics.increment("normalization_applied")
                user_input = norm_result.normalized

            # ── Phase 6I: Conversational Intelligence Layer ──────────────────
            conv_result = self.conversation_layer.process(user_input)

            if conv_result.clarification_needed:
                # Destructive synonym detected (e.g. "nuke", "wipe") —
                # never steer toward destructive confirmation.
                term = conv_result.dangerous_synonym or "unknown"
                self.logger.warning(
                    f"Destructive synonym '{term}' in: '{user_input}'"
                )
                return PipelineResult(
                    success=False,
                    output=(
                        f"The term '{term}' is destructive. "
                        f"Please use an explicit supported command."
                    ),
                    error="Destructive synonym detected"
                )

            if conv_result.was_modified:
                self.logger.info(
                    f"Conversation layer adjusted input: "
                    f"'{user_input}' → '{conv_result.cleaned}' "
                    f"(tone={conv_result.tone})"
                )
                user_input = conv_result.cleaned

            # Increment metrics per spec:
            # conversation_adjustments only if filler_stripped OR synonym_mapped
            if conv_result.filler_stripped or conv_result.synonym_mapped:
                self.metrics.increment("conversation_adjustments")
            # tone_detected only if tone is not neutral
            if conv_result.tone != "neutral":
                self.metrics.increment("tone_detected")

            # Store confidence modifier for post-semantic application
            _conv_confidence_modifier = conv_result.confidence_modifier

            # ── Phase 6F: Session Memory Resolution ──────────────────────────
            user_input, meta = self.session_memory.resolve_reference(user_input)
            if meta.get("was_modified"):
                self.logger.info(f"Resolved references: {meta}")
                self.metrics.increment("memory_resolutions")

            # Start Metrics Timer (Bypassed by introspection above)
            start_time = time.perf_counter()
            self.metrics.increment("total_commands")

            intents_to_execute = []

            # 0. Check for Pending Clarification (Phase 6C/6D)
            if self.clarification_manager.has_pending():
                self.logger.info("Resolving pending clarification...")
                resolved_intent = self.clarification_manager.resolve_clarification(user_input)
                
                if resolved_intent:
                    cmd = Command(
                        raw_input=user_input,
                        intent=resolved_intent["intent"],
                        entities=resolved_intent["parameters"],
                        confidence=resolved_intent["confidence"]
                    )
                    cmd.decision_source = "clarification"
                    intents_to_execute.append(cmd)
                    self.logger.info(f"Clarification resolved: {cmd.intent}")
                elif self.clarification_manager.has_pending():
                    # Phase 6D: Validation Guard (Invalid input, ask again)
                    return PipelineResult(
                        success=False,
                        output=f"Invalid input. {self.clarification_manager.last_question}",
                        error="Clarification Validation Failed"
                    )
                else:
                    # Phase 6D: Abort (Max attempts exceeded)
                    self.metrics.increment("clarification_failures")
                    return PipelineResult(
                        success=False,
                        output="Too many failed clarification attempts. Aborting.",
                        error="Clarification Aborted"
                    )

            # 1. Refinement Check (Phase 6B)
            # Check if user is refining the previous intent (Only if no command yet)
            if not intents_to_execute:
                refined_intent = self.refinement_engine.refine_intent(user_input, self.context)
                if refined_intent:
                    self.logger.info(f"Refinement detected: {refined_intent['intent']}")
                    self.metrics.increment("refinement_calls")
                    cmd = Command(
                        raw_input=user_input,
                        intent=refined_intent["intent"],
                        entities=refined_intent["parameters"],
                        confidence=refined_intent["confidence"]
                    )
                    cmd.decision_source = "refinement"
                    intents_to_execute.append(cmd)
            
            # 2. Semantic Intent Layer (Phase 6A/6E) - Multi-Intent
            # Only run if not already refined or resolved
            if not intents_to_execute and self.use_semantic_layer:
                try:
                    sem_start = time.perf_counter()
                    semantic_result = self.semantic_engine.parse_semantic_intent(user_input)
                    sem_duration = (time.perf_counter() - sem_start) * 1000
                    self.metrics.record_latency("semantic", sem_duration)
                    self.metrics.increment("semantic_calls")
                    
                    # Check global clarification flag
                    if semantic_result.get("requires_clarification"):
                         # Trigger clarification for the FIRST intent that needs it
                         for intent_data in semantic_result.get("intents", []):
                             if intent_data.get("requires_clarification"):
                                 question = self.clarification_manager.create_clarification(intent_data)
                                 self.logger.info(f"Clarification requested: {question}")
                                 self.metrics.increment("clarification_triggers")
                                 return PipelineResult(
                                     success=False,
                                     output=self.formatter.format_warning(f"{question}"),
                                     error="Requires Clarification"
                                 )
                    
                    # If valid, convert to Commands
                    if semantic_result.get("intents"):
                        for intent_data in semantic_result["intents"]:
                            if intent_data["intent"] != "unknown":
                                cmd = Command(
                                    raw_input=user_input,
                                    intent=intent_data["intent"],
                                    entities=intent_data["parameters"],
                                    # Adjustment 4: apply confidence_modifier AFTER
                                    # semantic parsing, not before.
                                    confidence=intent_data["confidence"] * _conv_confidence_modifier
                                )
                                cmd.decision_source = "semantic"
                                intents_to_execute.append(cmd)
                        
                        if intents_to_execute:
                             self.logger.info(f"Semantic Intents Detected: {[c.intent for c in intents_to_execute]}")

                except Exception as e:
                    self.logger.error(f"Semantic layer failed, falling back: {e}")
                    # Fallthrough to regex detector

            # 3. Fallback: Regex Intent Detector
            if not intents_to_execute:
                self.logger.info(f"Processing command with regex: {user_input}")
                cmd = self.intent_detector.detect_intent(user_input)
                if cmd and cmd.intent != "unknown":
                    cmd.decision_source = "regex"
                    intents_to_execute.append(cmd)
            
            # Verify we have something to do
            if not intents_to_execute:
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not understand command"),
                    error="Unknown intent"
                )
            
            # 4. Execution Loop (Phase 6E)
            final_results = []
            previous_intent_type = None
            
            if len(intents_to_execute) > 1:
                self.metrics.increment("multi_intent_chains")
                
            for cmd in intents_to_execute:
                self.metrics.increment_decision_source(cmd.decision_source)
            
            for i, cmd in enumerate(intents_to_execute):
                # Safety Check: Mixing Write/Delete
                if previous_intent_type:
                    # Generic mix check
                    is_mix = (previous_intent_type == "write_file" and cmd.intent == "delete_file") or \
                             (previous_intent_type == "delete_file" and cmd.intent == "write_file")
                    
                    if is_mix:
                        # Phase 6F: Harden Safety - Block wildcard/ambiguous targets
                        if cmd.intent == "delete_file":
                            path = cmd.entities.get("path") or ""
                            path_lower = path.lower()
                            unsafe_patterns = ["*", "all", "everything"]
                            # Empty path also bad if it implies current dir? Path usually required.
                            
                            if any(p in path_lower for p in unsafe_patterns) or path == "":
                                 return PipelineResult(
                                    success=False,
                                    output="Safety Guard: Blocked ambiguous destructive chain (wildcard detected).",
                                    error="Safety Violation: Cannot delete wildcard/all after write."
                                )
                        
                        return PipelineResult(
                            success=False,
                            output="Safety Guard: Cannot mix write and delete operations in a single chain.",
                            error="Safety Violation"
                        )
                
                # Execute individual command
                step_result = self._execute_command(cmd, auto_confirm)
                
                # Append output, but maybe add a separator if multiple?
                if i > 0:
                    final_results.append("---")
                final_results.append(step_result.output)
                
                # Abort chain on failure/cancel
                if not step_result.success:
                    return PipelineResult(
                        success=False,
                        output="\n".join(final_results), # partial output included
                        error=step_result.error,
                        cancelled=step_result.cancelled
                    )
                    
                previous_intent_type = cmd.intent
            
            # Success
            self.command_history.add(user_input, success=True)
            
            total_duration = (time.perf_counter() - start_time) * 1000
            self.metrics.record_latency("total", total_duration)
            
            return PipelineResult(
                success=True,
                output="\n".join(final_results)
            )
        
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            self.command_history.add(user_input, success=False)
            return PipelineResult(
                success=False,
                output=self.formatter.format_error_from_exception(e),
                error=str(e)
            )
    
    def simulate_command(self, user_input: str) -> PipelineResult:
        """
        Simulate command execution (dry-run)
        
        Args:
            user_input: User command
        
        Returns:
            PipelineResult
        """
        try:
            # Detect intent
            command = self.intent_detector.detect_intent(user_input)
            
            if not command or command.intent == "unknown":
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not understand command"),
                    error="Unknown intent"
                )
            
            # Generate plan
            plan = self.planner.create_plan_from_command(command)
            
            if not plan:
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not create execution plan"),
                    error="Plan generation failed"
                )
            
            # Simulate execution
            result = self.gateway.execute_plan(plan, confirmed=True, simulate=True)
            
            # Format output
            output = self.formatter.format_result(result)
            
            return PipelineResult(
                success=result.success,
                output=output
            )
        
        except Exception as e:
            self.logger.error(f"Simulation error: {e}")
            return PipelineResult(
                success=False,
                output=self.formatter.format_warning(f"Simulation failed: {e}"),
                error=str(e)
            )
    
    def get_history(self, count: Optional[int] = None) -> List[CommandEntry]:
        """
        Get command history for CLI display
        Phase 5B
        
        Args:
            count: Number of commands to return (None = all)
        
        Returns:
            List of command entries
        """
        return self.command_history.get_recent(count)
    
    def get_logs(self, count: Optional[int] = None) -> List[ExecutionEntry]:
        """
        Get execution logs for CLI display
        Phase 5B
        
        Args:
            count: Number of executions to return (None = all)
        
        Returns:
            List of execution entries
        """
        return self.execution_history.get_recent(count)
