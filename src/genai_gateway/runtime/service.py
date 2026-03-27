"""Entry point for executing runtime workflows."""

from genai_gateway.observability.request_logger import RequestLogger
from genai_gateway.runtime.agent import AgentExecutionReport, AgentOrchestrator, AgentTaskRequest
from genai_gateway.runtime.context import RuntimeContext
from genai_gateway.runtime.workflows.rag_workflow import RagWorkflow
from genai_gateway.schemas.request_schema import QueryRequest
from genai_gateway.schemas.response_schema import QueryResponse


class RuntimeService:
    """Dispatch incoming requests into the configured workflow."""

    def __init__(self) -> None:
        self.rag_workflow = RagWorkflow()
        self.agent_orchestrator = AgentOrchestrator()
        self.request_logger = RequestLogger()

    def handle_query(self, request: QueryRequest) -> QueryResponse:
        """Execute the default RAG workflow."""
        context = RuntimeContext(
            task=request.task,
            quality_mode=request.quality_mode,
            prompt_version=request.prompt_version,
            retrieval_mode=request.retrieval_mode,
            top_k=request.top_k,
            reranker_type=request.reranker_type,
        )
        return self.rag_workflow.run(request=request, context=context)

    def run_agent_task(self, request: AgentTaskRequest) -> AgentExecutionReport:
        """Execute a controlled multi-step task."""
        report = self.agent_orchestrator.run(request)
        self.request_logger.log_agent_run(request=request, report=report)
        return report
