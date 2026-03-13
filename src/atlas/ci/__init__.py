"""ATLAS CI/CD integration utilities.

This package provides reporters and formatters for integrating ATLAS
security scan results into continuous integration pipelines.

Supported platforms:
    - GitHub Actions / Pull Request comments
"""

from atlas.ci.github_reporter import GitHubPRReporter

__all__ = ["GitHubPRReporter"]
