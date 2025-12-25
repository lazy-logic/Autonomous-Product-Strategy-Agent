"""
============================================================
MRD Agent - Progress Display
============================================================
PURPOSE: Provide verbose, animated terminal feedback during
         research without affecting the research logic.
         
Features:
- Live progress updates
- Animated spinners
- Tool usage tracking
- Time elapsed display
============================================================
"""

import time
import threading
from datetime import datetime
from typing import Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text
from rich import box

console = Console()

# Color palette
COLORS = {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
    "dim": "dim white",
}


class ResearchProgress:
    """
    Animated progress display for research tasks.
    Thread-safe and non-blocking.
    """
    
    def __init__(self):
        self.start_time = datetime.now()
        self.current_task = ""
        self.current_tool = ""
        self.tasks_completed = 0
        self.tasks_total = 0
        self.tools_used = set()
        self.messages = []
        self.is_running = False
        self._lock = threading.Lock()
    
    def start(self, total_tasks: int):
        """Start progress tracking."""
        with self._lock:
            self.start_time = datetime.now()
            self.tasks_total = total_tasks
            self.tasks_completed = 0
            self.tools_used = set()
            self.messages = []
            self.is_running = True
    
    def set_task(self, task_name: str, tool_name: str = ""):
        """Update current task being executed."""
        with self._lock:
            self.current_task = task_name
            self.current_tool = tool_name
            if tool_name:
                self.tools_used.add(tool_name)
            self._add_message(f"[{COLORS['info']}]→[/] {task_name}")
    
    def complete_task(self, success: bool = True):
        """Mark current task as complete."""
        with self._lock:
            self.tasks_completed += 1
            status = f"[{COLORS['success']}][OK][/]" if success else f"[{COLORS['error']}][FAIL][/]"
            self._add_message(f"  {status} {self.current_task}")
    
    def add_detail(self, detail: str):
        """Add a detail message (for verbose output)."""
        with self._lock:
            self._add_message(f"    [{COLORS['dim']}]{detail}[/]")
    
    def _add_message(self, message: str):
        """Add message to log (keeps last 10)."""
        self.messages.append(message)
        if len(self.messages) > 10:
            self.messages.pop(0)
    
    def get_elapsed(self) -> str:
        """Get formatted elapsed time."""
        elapsed = datetime.now() - self.start_time
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def stop(self):
        """Stop progress tracking."""
        with self._lock:
            self.is_running = False


# Global progress instance
_progress = ResearchProgress()


def log_research_start(total_tasks: int):
    """Log start of research phase."""
    _progress.start(total_tasks)
    console.print()
    console.print(Panel.fit(
        f"[bold {COLORS['primary']}]Starting Research[/] - {total_tasks} tasks queued",
        border_style=COLORS['primary']
    ))


def log_task_start(task_type: str, target: str, query: str = ""):
    """Log start of a specific research task."""
    task_name = f"{task_type.replace('_', ' ').title()}"
    if target:
        task_name += f" [{target}]"
    
    _progress.set_task(task_name)
    
    # Show abbreviated query
    if query and len(query) > 50:
        query = query[:47] + "..."
    
    console.print(f"  [{COLORS['info']}]●[/] {task_name}")
    if query:
        console.print(f"    [{COLORS['dim']}]Query: {query}[/]")


def log_tool_use(tool_name: str, detail: str = ""):
    """Log when a specific tool is being used."""
    _progress.current_tool = tool_name
    _progress.tools_used.add(tool_name)
    
    console.print(f"    [{COLORS['primary']}]*[/] Using {tool_name}", end="")
    if detail:
        console.print(f" [{COLORS['dim']}]- {detail}[/]")
    else:
        console.print()


def log_data_found(data_type: str, value: str = ""):
    """Log when relevant data is found."""
    msg = f"    [{COLORS['success']}][+][/] Found: {data_type}"
    if value:
        # Truncate long values
        if len(value) > 40:
            value = value[:37] + "..."
        msg += f" = {value}"
    console.print(msg)


def log_task_complete(success: bool = True, result_summary: str = ""):
    """Log completion of a task."""
    _progress.complete_task(success)
    
    if success:
        icon = f"[{COLORS['success']}][OK][/]"
    else:
        icon = f"[{COLORS['error']}][FAIL][/]"
    
    msg = f"  {icon} Task complete"
    if result_summary:
        msg += f" [{COLORS['dim']}]({result_summary})[/]"
    console.print(msg)


def log_warning(message: str):
    """Log a warning message."""
    console.print(f"    [{COLORS['warning']}][!] {message}[/]")


def log_error(message: str):
    """Log an error message."""
    console.print(f"    [{COLORS['error']}][X] {message}[/]")


def log_retry(attempt: int, max_attempts: int, reason: str = ""):
    """Log a retry attempt."""
    msg = f"    [{COLORS['warning']}][R][/] Retry {attempt}/{max_attempts}"
    if reason:
        msg += f" - {reason}"
    console.print(msg)


def log_research_complete(success_count: int, fail_count: int, cost: float):
    """Log completion of research phase."""
    _progress.stop()
    
    elapsed = _progress.get_elapsed()
    tools = ", ".join(sorted(_progress.tools_used)) if _progress.tools_used else "None"
    
    console.print()
    table = Table(box=box.ROUNDED, border_style=COLORS['success'])
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    
    table.add_row("Tasks Completed", f"{success_count}/{success_count + fail_count}")
    table.add_row("Elapsed Time", elapsed)
    table.add_row("Tools Used", tools)
    table.add_row("Total Cost", f"${cost:.4f}")
    
    console.print(Panel(table, title="[bold green]Research Complete[/]", border_style="green"))


def log_synthesis_start():
    """Log start of synthesis phase."""
    console.print()
    console.print(f"[{COLORS['primary']}]━━━ Synthesizing MRD ━━━[/]")


def log_synthesis_step(step: str):
    """Log a synthesis step."""
    console.print(f"  [{COLORS['info']}]>[/] {step}")


def log_qa_start():
    """Log start of QA phase."""
    console.print()
    console.print(f"[{COLORS['primary']}]━━━ Quality Assurance ━━━[/]")


def log_qa_check(check_name: str, passed: bool, detail: str = ""):
    """Log a QA check result."""
    icon = f"[{COLORS['success']}][OK][/]" if passed else f"[{COLORS['warning']}][!][/]"
    msg = f"  {icon} {check_name}"
    if detail:
        msg += f" [{COLORS['dim']}]({detail})[/]"
    console.print(msg)


def log_confidence_score(score: float):
    """Log the confidence score with color coding."""
    if score >= 0.8:
        color = COLORS['success']
        indicator = "[HIGH]"
    elif score >= 0.6:
        color = COLORS['warning']
        indicator = "[MED]"
    else:
        color = COLORS['error']
        indicator = "[LOW]"
    
    console.print(f"\n  [{color}]Confidence Score: {score:.0%}[/] {indicator}")


def log_output_generation(output_path: str, format_type: str):
    """Log output file generation."""
    console.print(f"  [{COLORS['success']}][+][/] {format_type}: {output_path}")


# Spinner context manager for long operations
class Spinner:
    """
    Context manager for showing a spinner during long operations.
    Usage:
        with Spinner("Processing..."):
            do_something_slow()
    """
    
    def __init__(self, message: str):
        self.message = message
        self.progress = None
        self.task = None
    
    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        )
        self.progress.start()
        self.task = self.progress.add_task(self.message, total=None)
        return self
    
    def __exit__(self, *args):
        if self.progress:
            self.progress.stop()
    
    def update(self, message: str):
        """Update spinner message."""
        if self.progress and self.task is not None:
            self.progress.update(self.task, description=message)
