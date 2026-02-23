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
from lyra.semantic.intent_router import EmbeddingIntentRouter
from lyra.llm.escalation_layer import LLMEscalationAdvisor
from lyra.context.emotion.detector import EmotionDetector
from lyra.context.language_mirror import LanguageMirror
from lyra.core.reasoning_depth import ReasoningDepthController, ReasoningLevel
from lyra.memory.context_compressor import ContextCompressor
from lyra.core.integrity_watchdog import IntegrityWatchdog
from lyra.capabilities.capability_registry import CapabilityRegistry
from lyra.policy.policy_engine import PolicyEngine, PolicyViolationException
from lyra.orchestration.task_orchestrator import TaskOrchestrator
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

        # Phase F2: Embedding Intent Router (primary classifier)
        self.embedding_router = EmbeddingIntentRouter()
        self.use_embedding_router = True  # Feature flag

        # Phase F5/X4: Gemini API Escalation Advisor
        self.advisor = LLMEscalationAdvisor()

        # Phase F6: Emotion & Sarcasm Detection (subsystem G)
        self.emotion_detector = EmotionDetector()

        # Phase F10: Integrity Watchdog
        self.watchdog = IntegrityWatchdog()
        
        # Phase X1: Capability & Policy Framework
        self.capability_registry = CapabilityRegistry()
        self.policy_engine = PolicyEngine(self.capability_registry)
        self._register_default_capabilities()
        
        # Phase X2: Autonomous Orchestration
        self.orchestrator = TaskOrchestrator()
        
        self.logger.info("Lyra pipeline initialized")

    def _register_default_capabilities(self):
        """Register the baseline capabilities of Lyra."""
        self.capability_registry.register_capability(
            name="FileSystemCapability",
            allowed_intents=["create_file", "delete_file", "write_file", "read_file", "list_directory", "move_file", "copy_file"],
            max_risk="HIGH"
        )
        self.capability_registry.register_capability(
            name="ConversationCapability",
            allowed_intents=["chat", "clarify", "conversation", "unknown"],
            max_risk="LOW"
        )
        self.capability_registry.register_capability(
            name="SystemCapability",
            allowed_intents=["shutdown", "restart", "upgrade", "get_status", "help", "autonomous_goal"],
            max_risk="CRITICAL"
        )
        self.capability_registry.register_capability(
            name="CodeExecutionCapability",
            allowed_intents=["run_script", "execute_command", "install_package", "run_command"],
            max_risk="HIGH"
        )
        self.capability_registry.register_capability(
            name="AppLauncherCapability",
            allowed_intents=["launch_app", "open_url"],
            max_risk="MEDIUM"
        )

    def _wrap_result(self, result: PipelineResult, emotion: Dict[str, Any], language: str = "en") -> PipelineResult:
        """Apply emotion-based logic and language mirroring to any result."""
        # 1. Soften tone
        result.output = self.conversation_layer.soften_response(result.output, emotion)
        # 2. Mirror language (Phase F7)
        result.output = LanguageMirror.mirror_response(result.output, language)
        
        # 3. Phase F9: Add Response to Interaction History
        if hasattr(self, 'session_memory'):
            self.session_memory.add_interaction(role="assistant", content=result.output)
            
        return result

    def _handle_metrics(self, emotion: Dict[str, Any], language: str = "en") -> PipelineResult:
        """Phase 6G: Return internal metrics report"""
        report = self.metrics.get_report()
        return self._wrap_result(PipelineResult(success=True, output=report), emotion, language)

    def _handle_status(self, emotion: Dict[str, Any], language: str = "en") -> PipelineResult:
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
        return self._wrap_result(PipelineResult(success=True, output=status_msg), emotion, language)

    def _handle_pending(self, emotion: Dict[str, Any], language: str = "en") -> PipelineResult:
        """Phase 6D: Check pending clarification details"""
        if not self.clarification_manager.has_pending():
            return self._wrap_result(PipelineResult(success=True, output="No pending clarification."), emotion, language)
            
        mgr = self.clarification_manager
        msg = (
            f"Pending Clarification:\n"
            f"- Attempt: {mgr.attempt_count}/3\n"
            f"- Missing Fields: {', '.join(mgr.missing_fields)}\n"
            f"- Last Question: {mgr.last_question}"
        )
        return self._wrap_result(PipelineResult(success=True, output=msg), emotion, language)

    def _handle_last_intent(self, emotion: Dict[str, Any], language: str = "en") -> PipelineResult:
        """Phase 6D: Dump last intent JSON"""
        last = self.context.get_last_intent()
        if not last:
             return self._wrap_result(PipelineResult(success=True, output="No intent in history."), emotion, language)
        return self._wrap_result(PipelineResult(success=True, output=json.dumps(last, indent=2)), emotion, language)

    def _handle_explain(self, emotion: Dict[str, Any], language: str = "en") -> PipelineResult:
        """Phase 6D: Explain current state"""
        last = self.context.get_last_intent()
        pending = self.clarification_manager.has_pending()
        
        msg = (
            f"Decision State:\n"
            f"- Clarification Mode: {'Active' if pending else 'Inactive'}\n"
            f"- Last Confidence: {last.get('confidence', 0.0) if last else 0.0}\n"
            f"- Execution Allowed: {'No (Pending)' if pending else 'Yes'}"
        )
        return self._wrap_result(PipelineResult(success=True, output=msg), emotion, language)
    
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
            # ── Phase F10: Watchdog Command Start ──────────────────────────
            self.watchdog.record_command()

            # ── Phase F9: Add Input to Interaction History ──────────────────
            self.session_memory.add_interaction(role="user", content=user_input)

            # ── Phase 6D: Introspection Interceptors (ALWAYS FIRST) ─────────
            low_input = user_input.lower().strip()
            
            # ── Phase F6: Emotion & Sarcasm Detection (MOVE UP for interceptors) ─────
            emotion_result = self.emotion_detector.detect(user_input, context=self.context.get_last_intent())
            self.context.last_emotion = emotion_result

            # ── Phase F7: Language Detection & Mirroring ───────────────────────────
            detected_lang = LanguageMirror.detect_language(user_input)
            self.session_memory.update_language_preference(detected_lang)
            
            language = detected_lang
            if detected_lang == "en" and self.session_memory.preferred_language != "en" and len(user_input.strip()) < 10:
                language = self.session_memory.preferred_language
            
            self.logger.info(f"Language detected: {language}")

            if low_input == "status":
                return self._handle_status(emotion_result, language)
            elif low_input == "pending":
                return self._handle_pending(emotion_result, language)
            elif low_input == "last_intent":
                return self._handle_last_intent(emotion_result, language)
            elif low_input == "explain":
                return self._handle_explain(emotion_result, language)
            elif low_input == "metrics":
                return self._handle_metrics(emotion_result, language)

            # ── Phase 6H: Input Normalization ────────────────────────────────
            norm_result = self.normalization_engine.normalize(user_input)

            if norm_result.dangerous_token_detected:
                # A misspelled destructive keyword was detected — do NOT correct.
                # Return an explicit clarification so the user types it deliberately.
                detected = norm_result.dangerous_token_detected
                self.logger.warning(
                    f"Dangerous token detected near '{detected}': '{user_input}'"
                )
                return self._wrap_result(PipelineResult(
                    success=False,
                    output=(
                        f"Did you mean '{detected}'? "
                        f"Destructive commands must be typed explicitly."
                    ),
                    error="Dangerous token detected"
                ), emotion_result, language)

            if norm_result.was_modified:
                self.logger.info(
                    f"Input normalised [{norm_result.delta}]: "
                    f"'{user_input}' -> '{norm_result.normalized}'"
                )
                # Only count as applied when no dangerous token involved
                self.metrics.increment("normalization_applied")
                user_input = norm_result.normalized
            
            # (Emotion already detected above status checks)
            self.logger.info(f"Emotion detected: {emotion_result['emotion']} (intensity={emotion_result['intensity']:.2f})")
            
            # Behavioral Effect: Force confirmation if sarcastic or high-intensity anger
            force_confirmation = emotion_result.get("requires_confirmation", False)
            
            # ── Phase 6I: Conversational Intelligence Layer ──────────────────
            conv_result = self.conversation_layer.process(user_input)

            if conv_result.clarification_needed:
                # Destructive synonym detected (e.g. "nuke", "wipe") —
                # never steer toward destructive confirmation.
                term = conv_result.dangerous_synonym or "unknown"
                self.logger.warning(
                    f"Destructive synonym '{term}' in: '{user_input}'"
                )
                return self._wrap_result(PipelineResult(
                    success=False,
                    output=(
                        f"The term '{term}' is destructive. "
                        f"Please use an explicit supported command."
                    ),
                    error="Destructive synonym detected"
                ), emotion_result, language)

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
                    return self._wrap_result(PipelineResult(
                        success=False,
                        output=f"Invalid input. {self.clarification_manager.last_question}",
                        error="Clarification Validation Failed"
                    ), emotion_result, language)
                else:
                    # Phase 6D: Abort (Max attempts exceeded)
                    self.metrics.increment("clarification_failures")
                    return self._wrap_result(PipelineResult(
                        success=False,
                        output="Too many failed clarification attempts. Aborting.",
                        error="Clarification Aborted"
                    ), emotion_result, language)

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
            
            # 2a. Phase F2: Embedding Intent Router (PRIMARY classifier)
            # Runs before the semantic rule-based layer.
            if not intents_to_execute and self.use_embedding_router:
                try:
                    emb_start = time.perf_counter()
                    emb_result = self.embedding_router.classify(user_input)
                    emb_duration = (time.perf_counter() - emb_start) * 1000
                    self.metrics.record_latency("embedding", emb_duration)
                    self.metrics.increment("embedding_calls")

                    emb_intent = emb_result.get("intent", "unknown")
                    emb_conf = emb_result.get("confidence", 0.0)

                    if emb_intent != "unknown":
                        # Use embedding result — feed into semantic layer for
                        # parameter extraction, then continue to execution.
                        self.logger.info(
                            f"Embedding router: intent={emb_intent} "
                            f"conf={emb_conf:.3f} "
                            f"escalation={emb_result.get('requires_escalation')}"
                        )

                        # Phase F3: Use extract_parameters for targeted extraction
                        params = self.semantic_engine.extract_parameters(
                            emb_intent, user_input
                        )
                        merged_conf = emb_conf * _conv_confidence_modifier
                        cmd = Command(
                            raw_input=user_input,
                            intent=emb_intent,
                            entities=params,
                            confidence=merged_conf,
                        )
                        cmd.decision_source = "embedding"
                        intents_to_execute.append(cmd)

                        self.logger.info(
                            f"Embedding Intents: "
                            f"{[c.intent for c in intents_to_execute]}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Embedding router failed, falling back: {e}"
                    )
                    # Fallthrough to semantic / regex

            # ── Phase F8: Adaptive Reasoning Depth ────────────────────────────────
            emb_intent = "unknown"
            emb_conf = 0.0
            if 'emb_result' in locals():
                emb_intent = emb_result.get("intent", "unknown")
                emb_conf = emb_result.get("confidence", 0.0)
            
            planning_keywords = ["organize", "clean up", "figure out", "optimize", "arrange"]
            has_planning = any(kw in user_input.lower() for kw in planning_keywords)
            
            # Use conversation history for turn count
            turn_count = len(self.command_history.commands)
            
            reasoning_level = ReasoningDepthController.determine_level(
                intent=emb_intent,
                embedding_confidence=emb_conf,
                ambiguity_score=1.0 - emb_conf,
                conversation_turn_count=turn_count,
                contains_planning_keywords=has_planning,
                user_input=user_input,
                emotion_state=emotion_result.get("emotion", "neutral")
            )
            self.context.last_reasoning_level = reasoning_level
            self.logger.info(f"Reasoning Level: {reasoning_level.value.upper()}")
            
            # Phase F10: Watchdog Reasoning Level
            self.watchdog.record_reasoning_level(reasoning_level.value)

            # -------------------------------------------------------
            # Phase F5/F8: LLM Escalation (Advisor Brain)
            # Triggers if depth >= STANDARD and (low confidence or planning detected)
            # -------------------------------------------------------
            should_escalate = False
            
            if not intents_to_execute:
                should_escalate = True
            elif any(c.intent == "conversation" for c in intents_to_execute):
                should_escalate = True
            elif has_planning:
                should_escalate = True
            elif 'emb_result' in locals() and emb_result.get("requires_escalation"):
                should_escalate = True
                
            if should_escalate and reasoning_level != ReasoningLevel.SHALLOW:
                # ── Phase F9: Contextual Memory Compression ──────────────────
                turn_count = len(self.session_memory.get_interaction_history())
                if ContextCompressor.should_compress(turn_count):
                    self.logger.info(f"Compression triggered ({turn_count} turns)...")
                    # Phase F10: Watchdog Compression
                    self.watchdog.record_compression()
                    compressed_history = ContextCompressor.compress(
                        self.session_memory.get_interaction_history(),
                        model_advisor=self.advisor
                    )
                    self.session_memory.set_interaction_history(compressed_history)

                self.logger.info(f"Escalating to LLM Advisor (Depth: {reasoning_level.value})...")
                # Phase F10: Watchdog Escalation
                self.watchdog.record_escalation()
                # Pass current best guess if any
                first_guess = intents_to_execute[0].__dict__ if intents_to_execute else None
                advisor_report = self.advisor.analyze(
                    user_input, 
                    embedding_result=first_guess,
                    context=self.context.get_last_intent(),
                    language=language,
                    reasoning_level=reasoning_level.value,
                    history=self.session_memory.get_interaction_history(),
                    watchdog=self.watchdog
                )
                
                if advisor_report.get("intent") != "unknown":
                    # Phase F10: Watchdog Loop Detection
                    self.watchdog.detect_escalation_loop(advisor_report["intent"])
                    self.logger.info(f"LLM Advisor recommended: {advisor_report['intent']} (conf: {advisor_report['confidence']})")
                    
                    # LLM only advises intent. We re-run extraction for safety.
                    params = self.semantic_engine.extract_parameters(
                        advisor_report["intent"], user_input
                    )
                    
                    cmd = Command(
                        raw_input=user_input,
                        intent=advisor_report["intent"],
                        entities=params,
                        confidence=advisor_report["confidence"]
                    )
                    # In Phase F5, advisor recommendation replaces others (isolated check)
                    intents_to_execute = [cmd]

                    # ── Phase X2: Autonomous Orchestration Trigger ──────────
                    if reasoning_level == ReasoningLevel.DEEP and advisor_report.get("intent") in ["complex_goal", "autonomous_goal"]:
                        self.logger.info("DEEP reasoning + complex_goal detected. Starting orchestration...")
                        plan = self.orchestrator.generate_plan(user_input, self.advisor, reasoning_level.value)
                        if plan:
                            orch_result = self.orchestrator.execute_plan(plan, self)
                            final_output = f"Autonomous Task Result: {orch_result['status'].upper()}\n"
                            final_output += "\n".join([f"- {s.get('description', s.get('intent'))}: {'✅' if s.get('success') else '❌'}" for s in orch_result['audit_log']])
                            return self._wrap_result(PipelineResult(
                                success=orch_result['status'] == "success",
                                output=final_output
                            ), emotion_result, language)
                        else:
                            self.logger.warning("Orchestration failed to generate plan. Falling back.")
                else:
                    self.logger.info("LLM Advisor confirmed 'unknown' or failed.")

            # 2b. Semantic Intent Layer (Phase 6A/6E) - Multi-Intent
            # Only run if not already resolved by embedding router
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
                                 return self._wrap_result(PipelineResult(
                                     success=False,
                                     output=self.formatter.format_warning(f"{question}"),
                                     error="Requires Clarification"
                                 ), emotion_result, language)
                    
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
                return self._wrap_result(PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not understand command"),
                    error="Unknown intent"
                ), emotion_result, language)

            # -------------------------------------------------------
            # Phase F3: Parameter extraction + Feasibility validation
            # Runs after intent classification, before execution.
            # Only applies to embedding-routed commands (semantic/regex
            # paths have their own validation and entity key formats).
            # -------------------------------------------------------
            for cmd in intents_to_execute:
                if getattr(cmd, 'decision_source', '') != 'embedding':
                    continue

                # Enrich entities via regex extraction if still empty
                if not cmd.entities:
                    cmd.entities = self.semantic_engine.extract_parameters(
                        cmd.intent, user_input
                    )

                # Feasibility check (required params + filesystem etc.)
                feasibility = self.semantic_engine.validate_feasibility(
                    cmd.intent, cmd.entities
                )

                if feasibility.requires_clarification:
                    self.logger.info(
                        f"Feasibility: clarification needed for "
                        f"{cmd.intent}: {feasibility.clarification_question}"
                    )
                    self.metrics.increment("clarification_triggers")
                    return self._wrap_result(PipelineResult(
                        success=False,
                        output=self.formatter.format_warning(
                            feasibility.clarification_question
                            or "More information is needed."
                        ),
                        error="Requires Clarification"
                    ), emotion_result, language)

                if not feasibility.valid:
                    err_msg = "; ".join(feasibility.errors)
                    self.logger.warning(
                        f"Feasibility failed for {cmd.intent}: {err_msg}"
                    )
                    return self._wrap_result(PipelineResult(
                        success=False,
                        output=self.formatter.format_error(
                            f"Cannot execute: {err_msg}"
                        ),
                        error="Feasibility Validation Failed"
                    ), emotion_result, language)
            
            # 4. Execution Loop (Phase 6E)
            final_results = []
            previous_intent_type = None
            
            if len(intents_to_execute) > 1:
                self.metrics.increment("multi_intent_chains")
                
            for cmd in intents_to_execute:
                self.metrics.increment_decision_source(cmd.decision_source)
            
            for i, cmd in enumerate(intents_to_execute):
                # Phase F6: Force confirmation if emotion/sarcasm indicates
                if force_confirmation:
                    cmd.requires_confirmation = True
                    self.logger.info(f"Forcing confirmation for {cmd.intent} due to emotional state.")

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
                                return self._wrap_result(PipelineResult(
                                    success=False,
                                    output="Safety Guard: Blocked ambiguous destructive chain (wildcard detected).",
                                    error="Safety Violation: Cannot delete wildcard/all after write."
                                ), emotion_result, language)
                
                        return self._wrap_result(PipelineResult(
                            success=False,
                            output="Safety Guard: Cannot mix write and delete operations in a single chain.",
                            error="Safety Violation"
                        ), emotion_result, language)
                
                # Phase F4: Execution Validation Gate
                exec_request = self.gateway.validate_execution_request(
                    intent=cmd.intent,
                    params=cmd.entities,
                    metadata={
                        "source": getattr(cmd, "decision_source", "unknown"),
                        "confirmed": auto_confirm,
                        "semantic_valid": True,
                    },
                )

                if not exec_request.allowed:
                    if exec_request.requires_confirmation and not auto_confirm:
                        return self._wrap_result(PipelineResult(
                            success=False,
                            output=self.formatter.format_warning(
                                exec_request.reason
                                or "Confirmation required for this action."
                            ),
                            error="Requires Confirmation",
                        ), emotion_result, language)
                    elif not exec_request.requires_confirmation:
                        # Phase F10: Watchdog Safety Violation
                        self.watchdog.record_safety_violation()
                        return self._wrap_result(PipelineResult(
                            success=False,
                            output=self.formatter.format_error(
                                exec_request.reason
                                or "Execution blocked by safety gate."
                            ),
                            error="Execution Blocked",
                        ), emotion_result, language)

                # ── Phase X1: Policy Engine Validation ─────────────────────────
                try:
                    self.policy_engine.validate(cmd.intent, exec_request.risk_level)
                except PolicyViolationException as pve:
                    self.logger.warning(f"Policy Violation: {pve}")
                    self.watchdog.record_safety_violation()
                    return self._wrap_result(PipelineResult(
                        success=False,
                        output=self.formatter.format_error(str(pve)),
                        error="Policy Violation"
                    ), emotion_result, language)

                # Execute individual command
                step_result = self._execute_command(cmd, auto_confirm)
                
                # Append output, but maybe add a separator if multiple?
                if i > 0:
                    final_results.append("---")
                final_results.append(step_result.output)
                
                # Abort chain on failure/cancel
                if not step_result.success:
                    return self._wrap_result(PipelineResult(
                        success=False,
                        output="\n".join(final_results), # partial output included
                        error=step_result.error,
                        cancelled=step_result.cancelled
                    ), emotion_result, language)
                    
                previous_intent_type = cmd.intent
            
            # Success
            # Phase F10: Watchdog Success
            for cmd in (intents_to_execute or []):
                self.watchdog.record_execution_success(cmd.intent)

            self.command_history.add(user_input, success=True)
            
            total_duration = (time.perf_counter() - start_time) * 1000
            self.metrics.record_latency("total", total_duration)
            
            final_output = "\n".join(final_results)
            return self._wrap_result(PipelineResult(success=True, output=final_output), emotion_result, language)
        except Exception as e:
            # Phase F10: Watchdog Failure
            self.watchdog.record_execution_failure()
            self.logger.error(f"Pipeline error: {e}")
            self.command_history.add(user_input, success=False)
            return self._wrap_result(PipelineResult(
                success=False,
                output=self.formatter.format_error_from_exception(e),
                error=str(e)
            ), emotion_result)
    
    def _process_autonomous_step(self, cmd: Command) -> PipelineResult:
        """
        Internal helper for TaskOrchestrator to run a single step through 
        Safety Gate -> Policy Engine -> Execution -> Watchdog.
        Bypasses intent detection as intent is already planned.
        """
        # 1. Watchdog Command Start
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("deep")
        
        # 2. Safety Gate (Phase F4)
        exec_request = self.gateway.validate_execution_request(
            intent=cmd.intent,
            params=cmd.entities,
            metadata={"source": "orchestrator", "confirmed": True, "semantic_valid": True}
        )
        
        if not exec_request.allowed:
            self.watchdog.record_safety_violation()
            return PipelineResult(success=False, output="Blocked by safety gate", error="Execution Blocked")
            
        # 3. Policy Engine (Phase X1)
        try:
            self.policy_engine.validate(cmd.intent, exec_request.risk_level)
        except PolicyViolationException as pve:
            self.watchdog.record_safety_violation()
            return PipelineResult(success=False, output=str(pve), error="Policy Violation")

        # 4. Execution
        step_result = self._execute_command(cmd, auto_confirm=True)
        
        # 5. Watchdog Success/Failure
        if step_result.success:
            self.watchdog.record_execution_success(cmd.intent)
        else:
            self.watchdog.record_execution_failure()
            
        return step_result

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
