"""Stable human-readable report generation."""
def render_summary(summaries):
    lines = ["group,count,total,mean"]
    for item in summaries:
        lines.append(f"{item.group},{item.count},{item.total:g},{item.mean:g}")
    return "\n".join(lines) + "\n"
