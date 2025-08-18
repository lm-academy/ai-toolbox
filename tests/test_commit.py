"""Tests for the commit command module."""

import subprocess
import pytest
from click.testing import CliRunner

from ai_toolbox.commands.commit import commit, get_staged_diff


class TestGetStagedDiff:
    """Test cases for the get_staged_diff function."""

    def test_get_staged_diff_success(self, mocker):
        """Test successful retrieval of staged diff."""
        # Arrange
        expected_diff = (
            "diff --git a/file.txt b/file.txt\n+new line\n"
        )
        mock_run = mocker.patch(
            "ai_toolbox.commands.commit.subprocess.run"
        )
        mock_result = mocker.Mock()
        mock_result.stdout = expected_diff
        mock_run.return_value = mock_result

        # Act
        result = get_staged_diff()

        # Assert
        assert result == expected_diff
        mock_run.assert_called_once_with(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_get_staged_diff_empty(self, mocker):
        """Test retrieval when no staged changes exist."""
        # Arrange
        mock_run = mocker.patch(
            "ai_toolbox.commands.commit.subprocess.run"
        )
        mock_result = mocker.Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        # Act
        result = get_staged_diff()

        # Assert
        assert result == ""
        mock_run.assert_called_once_with(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_get_staged_diff_git_error(self, mocker):
        """Test handling of git command errors."""
        # Arrange
        mock_run = mocker.patch(
            "ai_toolbox.commands.commit.subprocess.run"
        )
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "diff", "--staged"],
            stderr="fatal: not a git repository",
        )

        # Act & Assert
        with pytest.raises(
            subprocess.CalledProcessError
        ) as exc_info:
            get_staged_diff()

        # The error message is in the output attribute, not the string representation
        assert "Git command failed:" in exc_info.value.output

    def test_get_staged_diff_git_not_found(self, mocker):
        """Test handling when git is not installed."""
        # Arrange
        mock_run = mocker.patch(
            "ai_toolbox.commands.commit.subprocess.run"
        )
        mock_run.side_effect = FileNotFoundError(
            "git command not found"
        )

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            get_staged_diff()

        assert "Git command not found" in str(exc_info.value)


class TestCommitCommand:
    """Test cases for the commit click command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_commit_with_staged_changes(self, mocker):
        """Test commit command with staged changes."""
        # Arrange
        staged_diff = (
            "diff --git a/file.txt b/file.txt\n+new line\n"
        )
        mock_get_staged_diff = mocker.patch(
            "ai_toolbox.commands.commit.get_staged_diff"
        )
        mock_get_staged_diff.return_value = staged_diff

        # Act
        result = self.runner.invoke(commit)

        # Assert
        assert result.exit_code == 0
        assert (
            "[commit] Retrieved staged changes:" in result.output
        )
        assert staged_diff in result.output
        mock_get_staged_diff.assert_called_once()

    def test_commit_with_no_staged_changes(self, mocker):
        """Test commit command with no staged changes."""
        # Arrange
        mock_get_staged_diff = mocker.patch(
            "ai_toolbox.commands.commit.get_staged_diff"
        )
        mock_get_staged_diff.return_value = ""

        # Act
        result = self.runner.invoke(commit)

        # Assert
        assert result.exit_code == 0
        assert "No staged changes found" in result.output
        assert "Please stage some changes" in result.output
        mock_get_staged_diff.assert_called_once()

    def test_commit_with_whitespace_only_diff(self, mocker):
        """Test commit command with whitespace-only diff."""
        # Arrange
        mock_get_staged_diff = mocker.patch(
            "ai_toolbox.commands.commit.get_staged_diff"
        )
        mock_get_staged_diff.return_value = "   \n\t  \n"

        # Act
        result = self.runner.invoke(commit)

        # Assert
        assert result.exit_code == 0
        assert "No staged changes found" in result.output
        mock_get_staged_diff.assert_called_once()

    def test_commit_git_error(self, mocker):
        """Test commit command when git command fails."""
        # Arrange
        mock_get_staged_diff = mocker.patch(
            "ai_toolbox.commands.commit.get_staged_diff"
        )
        mock_get_staged_diff.side_effect = (
            subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", "diff", "--staged"],
                stderr="fatal: not a git repository",
            )
        )

        # Act
        result = self.runner.invoke(commit)

        # Assert
        assert (
            result.exit_code == 0
        )  # Click command doesn't exit with error code
        assert "Error running git command" in result.output
        mock_get_staged_diff.assert_called_once()

    def test_commit_git_not_found(self, mocker):
        """Test commit command when git is not installed."""
        # Arrange
        mock_get_staged_diff = mocker.patch(
            "ai_toolbox.commands.commit.get_staged_diff"
        )
        mock_get_staged_diff.side_effect = FileNotFoundError(
            "Git command not found. Please ensure git is installed and in your PATH."
        )

        # Act
        result = self.runner.invoke(commit)

        # Assert
        assert (
            result.exit_code == 0
        )  # Click command doesn't exit with error code
        assert "Error: Git command not found" in result.output
        mock_get_staged_diff.assert_called_once()
