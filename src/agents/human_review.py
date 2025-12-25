"""
============================================================
MRD Agent - Human-in-the-Loop Review
============================================================
PURPOSE: Enable human approval at key decision points.

TASK 4 REQUIREMENT:
"Show where the 'Human in the Loop' sits (e.g., approving the 
research plan before the agent writes the strategy)."

APPROVAL POINTS:
1. Research Plan - Before executing research
2. Final MRD - Before outputting final document
============================================================
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from rich import print as rprint
from rich import box
from typing import Optional

from src.models.state import MRDState, ResearchTask


# Initialize rich console for beautiful terminal output
console = Console()


def display_research_plan(state: MRDState) -> None:
    """
    Display the research plan in a formatted table.
    
    This shows what research will be conducted before
    asking for human approval.
    """
    console.print()
    console.print(Panel.fit(
        "[bold blue]Research Plan Review[/bold blue]",
        subtitle="Human-in-the-Loop Checkpoint",
        box=box.ASCII
    ))
    console.print()
    
    # Display prompt
    console.print(f"[bold]Original Prompt:[/bold] {state.prompt}")
    console.print(f"[bold]Domain:[/bold] {state.domain}")
    console.print()
    
    # Display research tasks in a table
    table = Table(title="Planned Research Tasks", box=box.ASCII)
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Type", style="magenta")
    table.add_column("Target", style="green")
    table.add_column("Query", style="white")
    table.add_column("Priority", justify="center")
    
    for i, task in enumerate(state.research_plan, 1):
        priority_style = {
            1: "[bold red]P1[/bold red]",
            2: "[yellow]P2[/yellow]",
            3: "[white]P3[/white]",
            4: "[dim]P4[/dim]",
            5: "[dim]P5[/dim]"
        }.get(task.priority, f"P{task.priority}")
        
        table.add_row(
            str(i),
            task.task_type.value.replace("_", " ").title(),
            task.target_company or "General",
            task.query[:50] + "..." if len(task.query) > 50 else task.query,
            priority_style
        )
    
    console.print(table)
    console.print()
    
    # Display companies being researched
    console.print("[bold]Companies to Research:[/bold]")
    companies_targeted = set(
        t.target_company for t in state.research_plan 
        if t.target_company
    )
    for company in companies_targeted:
        console.print(f"  • {company}")
    console.print()


def request_approval(
    prompt: str,
    default: bool = True,
    allow_skip: bool = False
) -> bool:
    """
    Request approval from human operator.
    
    Args:
        prompt: The question to ask
        default: Default answer if user just presses Enter
        allow_skip: If True, allows skipping with 'skip' input
        
    Returns:
        True if approved, False if rejected
    """
    try:
        return Confirm.ask(prompt, default=default)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Approval skipped by user[/yellow]")
        return False


def display_approval_checkpoint(checkpoint_name: str, details: dict) -> bool:
    """
    Display a checkpoint and request approval.
    
    Args:
        checkpoint_name: Name of the checkpoint
        details: Dictionary of details to display
        
    Returns:
        True if approved, False otherwise
    """
    console.print()
    console.print(Panel.fit(
        f"[bold yellow]CHECKPOINT: {checkpoint_name}[/bold yellow]",
        subtitle="Approval Required",
        box=box.ASCII
    ))
    
    # Display details
    for key, value in details.items():
        if isinstance(value, list):
            console.print(f"[bold]{key}:[/bold]")
            for item in value:
                console.print(f"  • {item}")
        else:
            console.print(f"[bold]{key}:[/bold] {value}")
    
    console.print()
    
    return request_approval(
        "[bold green]Approve and continue?[/bold green]",
        default=True
    )


def display_mrd_preview(state: MRDState) -> bool:
    """
    Display a preview of the MRD before final output.
    
    Args:
        state: Current MRD state with draft
        
    Returns:
        True if approved for output, False to revise
    """
    console.print()
    console.print(Panel.fit(
        "[bold blue]MRD Preview[/bold blue]",
        subtitle="Final Review Checkpoint",
        box=box.ASCII
    ))
    console.print()
    
    if not state.mrd_draft:
        console.print("[red]No MRD draft available[/red]")
        return False
    
    # Display summary
    console.print("[bold]Confidence Score:[/bold]", end=" ")
    score = state.confidence_score
    if score >= 0.8:
        console.print(f"[green]{score:.0%}[/green]")
    elif score >= 0.6:
        console.print(f"[yellow]{score:.0%}[/yellow]")
    else:
        console.print(f"[red]{score:.0%}[/red]")
    
    console.print(f"[bold]Iteration:[/bold] {state.iteration}")
    console.print(f"[bold]Tools Used:[/bold] {', '.join(state.tools_used)}")
    console.print(f"[bold]Total Cost:[/bold] ${state.total_cost:.4f}")
    console.print()
    
    # Display research results summary
    successful = len([r for r in state.research_results if r.success])
    failed = len([r for r in state.research_results if not r.success])
    console.print(f"[bold]Research Results:[/bold] {successful} successful, {failed} failed")
    console.print()
    
    # Display QA feedback if any
    if state.qa_feedback:
        console.print("[bold]QA Feedback:[/bold]")
        for item in state.qa_feedback:
            console.print(f"  • {item}")
        console.print()
    
    return request_approval(
        "[bold green]Approve final MRD output?[/bold green]",
        default=True
    )


def display_status_update(status: str, details: Optional[str] = None) -> None:
    """
    Display a status update during agent execution.
    
    Args:
        status: Status message
        details: Optional additional details
    """
    console.print(f"[dim]->[/dim] {status}")
    if details:
        console.print(f"  [dim]{details}[/dim]")


def display_error(error: str, recoverable: bool = True) -> None:
    """
    Display an error message.
    
    Args:
        error: Error message
        recoverable: Whether the error is recoverable
    """
    if recoverable:
        console.print(f"[yellow]Warning:[/yellow] {error}")
    else:
        console.print(f"[bold red]Error:[/bold red] {error}")


def display_success(message: str) -> None:
    """Display a success message."""
    console.print(f"[bold green]{message}[/bold green]")


def display_final_summary(state: MRDState) -> None:
    """
    Display final summary after MRD generation.
    
    Args:
        state: Final MRD state
    """
    console.print()
    console.print(Panel.fit(
        "[bold green]MRD Generation Complete[/bold green]",
        subtitle="Summary",
        box=box.ASCII
    ))
    console.print()
    
    # Cost breakdown
    table = Table(title="Execution Summary", box=box.ASCII)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Iterations", str(state.iteration))
    table.add_row("Confidence Score", f"{state.confidence_score:.0%}")
    table.add_row("Total Cost", f"${state.total_cost:.4f}")
    table.add_row("Tools Used", str(len(state.tools_used)))
    table.add_row("Research Tasks", str(len(state.research_results)))
    
    console.print(table)
    console.print()
